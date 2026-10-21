"""Creating, finalising, diffing and verifying input versions.

A version is created by *curating* a source directory rather than copying it
wholesale (see :mod:`globi_data.roles`), hashing everything that lands in it,
and freezing the result. Two guards keep the history meaningful:

no-op guard
    Creating a version byte-identical to its parent is refused. Version numbers
    should mean something changed.

impact classification
    A version that only touches non-simulation files is ``metadata-only``, and
    downstream results are not marked stale for it. This is what stops a README
    fix from painting every experiment red.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from . import gitutil, paths, render, yamlio
from .hashing import bundle_sha256, file_sha256, file_size
from .models import (
    NON_SIMULATION_FILENAMES,
    Author,
    ChangeEntry,
    CurrentPointer,
    ExternalFileEntry,
    FileEntry,
    GloBIBlock,
    Impact,
    InputVersionManifest,
    PublishedEntry,
    SourceRef,
    StoredIn,
    Totals,
    VersionEntry,
)
from .paths import GlobiDataError
from .roles import BundlePlan, plan_bundle


@dataclass
class CreateResult:
    """Outcome of creating a version."""

    manifest: InputVersionManifest
    version_dir: Path
    plan: BundlePlan
    created: bool


def _guard_noop(
    partner: str,
    version: str,
    parent_version: str | None,
    parent: InputVersionManifest | None,
    files: list[FileEntry],
    digest: str,
    *,
    allow_noop: bool,
) -> None:
    """Refuse to create a version identical to its parent.

    Version numbers should mean something changed. A bump that alters nothing
    makes the history lie about when inputs moved.

    Raises:
        GlobiDataError: if the bundle matches its parent and ``allow_noop`` is
            not set.
    """
    if allow_noop or parent is None or digest != parent.bundle_sha256:
        return
    # Compare simulation-affecting paths only. The parent's file list also
    # carries README.md, which is written after this guard runs, so including it
    # would make every comparison differ and the guard would never fire.
    new_paths = {e.path for e in files if e.simulation_affecting}
    old_paths = {e.path for e in parent.files if e.simulation_affecting}
    if new_paths != old_paths:
        return
    raise GlobiDataError(
        f"{partner} {version} would be byte-identical to {parent_version} "
        f"(bundle_sha256 {digest[:12]}...). Nothing to version.\n"
        "Use --allow-noop with a --summary if you need a metadata-only bump."
    )


def read_manifest(version_dir: Path) -> InputVersionManifest:
    """Load the ``input-version.yml`` inside a version directory."""
    path = version_dir / paths.INPUT_MANIFEST_NAME
    if not path.exists():
        raise GlobiDataError(f"No {paths.INPUT_MANIFEST_NAME} in {version_dir}.")
    return InputVersionManifest.model_validate(yamlio.read(path))


def manifest_sha(version_dir: Path) -> str:
    """Return the sha256 of a version's manifest file bytes.

    This is the value output manifests pin, and it is deliberately reproducible
    by hand with ``shasum -a 256 input-version.yml``.
    """
    return file_sha256(version_dir / paths.INPUT_MANIFEST_NAME)


def _is_simulation_affecting(rel_path: str) -> bool:
    """Whether a file's contents can change a simulation result."""
    return Path(rel_path).name not in NON_SIMULATION_FILENAMES


def _author(name: str | None, email: str | None, repo: Path) -> Author:
    """Determine the author, falling back to git config."""
    if name or email:
        return Author(name=name, email=email)
    return Author(
        name=gitutil._run(["config", "user.name"], repo),
        email=gitutil._run(["config", "user.email"], repo),
    )


def _diff_against_parent(
    files: list[FileEntry],
    externals: list[ExternalFileEntry],
    parent: InputVersionManifest | None,
) -> tuple[list[ChangeEntry], Impact]:
    """Compute the changelog and impact classification relative to a parent."""
    if parent is None:
        return [], "simulation-affecting"

    # Compare simulation-affecting content only. README.md is written after this
    # runs, so including it would report a spurious "removed README.md" on every
    # version — and a regenerated README is not a change worth reporting anyway.
    old = {e.path: e.sha256 for e in parent.files if e.simulation_affecting}
    old.update({
        entry.path: entry.sha256 for entry in parent.external_files if entry.sha256
    })
    new = {e.path: e.sha256 for e in files if e.simulation_affecting}
    new.update({entry.path: entry.sha256 for entry in externals if entry.sha256})

    sim = {entry.path for entry in files if entry.simulation_affecting}
    sim.update(entry.path for entry in externals)
    old_sim = {entry.path for entry in parent.files if entry.simulation_affecting}
    old_sim.update(entry.path for entry in parent.external_files)

    changes: list[ChangeEntry] = []
    impact: Impact = "metadata-only"

    for path in sorted(set(new) | set(old)):
        if path not in old:
            changes.append(ChangeEntry(path=path, change="added"))
            if path in sim:
                impact = "simulation-affecting"
        elif path not in new:
            changes.append(ChangeEntry(path=path, change="removed"))
            if path in old_sim:
                impact = "simulation-affecting"
        elif old[path] != new[path]:
            changes.append(ChangeEntry(path=path, change="modified"))
            if path in sim:
                impact = "simulation-affecting"

    return changes, impact


def _build_entries(
    plan: BundlePlan,
    version_dir: Path,
    *,
    hash_external: bool,
) -> tuple[list[FileEntry], list[ExternalFileEntry]]:
    """Hash everything in the staged version directory."""
    files: list[FileEntry] = []
    for planned in plan.include:
        dest = version_dir / planned.rel_path
        files.append(
            FileEntry(
                path=planned.rel_path,
                role=planned.role,
                bytes=file_size(dest),
                sha256=file_sha256(dest),
                simulation_affecting=_is_simulation_affecting(planned.rel_path),
            )
        )

    source_repo = gitutil.repo_root(plan.source)
    externals: list[ExternalFileEntry] = []
    for item in plan.external:
        rel_to_repo = (
            str(item.source.resolve().relative_to(source_repo))
            if source_repo and source_repo in item.source.resolve().parents
            else str(item.source)
        )
        externals.append(
            ExternalFileEntry(
                path=item.rel_path,
                role=item.role,
                bytes=file_size(item.source),
                sha256=file_sha256(item.source) if hash_external else None,
                stored_in=StoredIn(
                    repo=source_repo.name if source_repo else "unknown",
                    remote=gitutil.remote_url(source_repo) if source_repo else None,
                    commit=gitutil.head_commit(source_repo) if source_repo else None,
                    path=rel_to_repo,
                    storage="git-lfs",
                ),
                resolver=f"$GLOBI_GIS_ROOT/{plan.partner}/{item.rel_path}",
                reason=item.reason,
            )
        )
    return files, externals


def create_version(
    root: Path,
    partner: str,
    source: Path,
    *,
    summary: str,
    impact: str = "auto",
    extra_includes: tuple[str, ...] = (),
    scenarios: dict[str, str] | None = None,
    allow_noop: bool = False,
    hash_external: bool = True,
    dry_run: bool = False,
    author_name: str | None = None,
    author_email: str | None = None,
) -> CreateResult:
    """Create the next input version for ``partner`` from ``source``.

    Raises:
        GlobiDataError: if the result would be byte-identical to the parent and
            ``allow_noop`` is not set.
    """
    plan = plan_bundle(partner, source, extra_includes=extra_includes)
    if scenarios:
        # Recorded so the bundle says which scenarios it compares without needing
        # globi-partners-data's experiments.yaml alongside it.
        plan.scenarios = dict(scenarios)
    if not plan.include:
        raise GlobiDataError(
            f"Nothing to version: no bundle files found under {source}."
        )

    pdir = paths.partner_dir(root, partner)
    versions = paths.list_versions(pdir)
    parent_version = versions[-1] if versions else None
    parent = read_manifest(pdir / parent_version) if parent_version else None
    version = paths.next_version(pdir)
    version_dir = pdir / version

    if version_dir.exists():
        raise GlobiDataError(f"{version_dir} already exists.")

    staging = version_dir if not dry_run else Path(str(version_dir) + ".dryrun")
    if staging.exists():
        shutil.rmtree(staging)

    try:
        for planned in plan.include:
            dest = staging / planned.rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(planned.source, dest)

        files, externals = _build_entries(plan, staging, hash_external=hash_external)
        changes, derived_impact = _diff_against_parent(files, externals, parent)

        entries = [(e.path, e.sha256) for e in files if e.simulation_affecting]
        entries += [(e.path, e.sha256) for e in externals if e.sha256]
        digest = bundle_sha256(entries)

        _guard_noop(
            partner,
            version,
            parent_version,
            parent,
            files,
            digest,
            allow_noop=allow_noop,
        )

        final_impact: Impact
        if impact == "auto":
            final_impact = (
                derived_impact if parent is not None else "simulation-affecting"
            )
            if allow_noop and digest == (parent.bundle_sha256 if parent else None):
                final_impact = "metadata-only"
        else:
            final_impact = impact  # type: ignore[assignment]

        source_repo = gitutil.repo_root(source)
        manifest = InputVersionManifest(
            partner=partner,
            version=version,
            parent_version=parent_version,
            created_at=paths.utcnow(),
            created_by=_author(author_name, author_email, root),
            summary=summary,
            impact=final_impact,
            changes=changes,
            not_carried_over=[f"{rel} - {reason}" for rel, reason in plan.skipped],
            source=SourceRef(
                repo=source_repo.name if source_repo else "unknown",
                remote=gitutil.remote_url(source_repo) if source_repo else None,
                commit=gitutil.head_commit(source_repo) if source_repo else None,
                dirty=gitutil.is_dirty(source_repo) if source_repo else None,
                path=(
                    str(source.resolve().relative_to(source_repo))
                    if source_repo and source_repo in source.resolve().parents
                    else str(source)
                ),
            ),
            globi=GloBIBlock(
                bundle_kind=plan.bundle_kind,  # type: ignore[arg-type]
                scenarios=plan.scenarios,
                roles=plan.roles,
                notes=plan.notes,
            ),
            files=files,
            external_files=externals,
            remote_files=[],
            totals=Totals(
                file_count=len(files),
                bytes=sum(e.size_bytes for e in files),
            ),
            bundle_sha256=digest,
        )

        yamlio.write(staging / paths.INPUT_MANIFEST_NAME, manifest.dump())
        (staging / "README.md").write_text(
            render.input_version_readme(manifest, plan), encoding="utf-8"
        )

        # README.md is written after hashing, so record it now that it exists.
        _append_readme_entry(manifest, staging)
        yamlio.write(staging / paths.INPUT_MANIFEST_NAME, manifest.dump())

        if dry_run:
            shutil.rmtree(staging)
            return CreateResult(
                manifest=manifest, version_dir=version_dir, plan=plan, created=False
            )

        _publish(root, partner, manifest, version_dir)
        return CreateResult(
            manifest=manifest, version_dir=version_dir, plan=plan, created=True
        )

    except Exception:
        # Never leave a half-written version directory behind: a partial vNNN
        # would look published to anyone browsing the tree.
        if staging.exists():
            shutil.rmtree(staging)
        raise


def _append_readme_entry(manifest: InputVersionManifest, version_dir: Path) -> None:
    """Record README.md in the file list without disturbing ``bundle_sha256``.

    README.md is not simulation-affecting, so it is excluded from the bundle
    hash by construction and can be added after that hash is computed.
    """
    readme = version_dir / "README.md"
    if not readme.exists():
        return
    manifest.files.append(
        FileEntry(
            path="README.md",
            bytes=file_size(readme),
            sha256=file_sha256(readme),
            simulation_affecting=False,
        )
    )
    manifest.files.sort(key=lambda entry: entry.path)
    manifest.totals = Totals(
        file_count=len(manifest.files),
        bytes=sum(entry.size_bytes for entry in manifest.files),
    )


def _publish(
    root: Path, partner: str, manifest: InputVersionManifest, version_dir: Path
) -> None:
    """Update the pointers and ledgers after a version directory is written."""
    pdir = paths.partner_dir(root, partner)

    ledger = paths.read_versions(pdir)
    ledger.partner = partner
    for entry in ledger.versions:
        if entry.status == "active":
            entry.status = "superseded"
    ledger.versions.append(
        VersionEntry(
            version=manifest.version,
            status="active",
            created_at=manifest.created_at,
            impact=manifest.impact,
            summary=manifest.summary,
        )
    )
    ledger.versions.sort(key=lambda entry: paths.version_number(entry.version))
    paths.write_versions(pdir, ledger)

    paths.write_current(
        pdir,
        CurrentPointer(
            partner=partner,
            current=manifest.version,
            manifest=f"{manifest.version}/{paths.INPUT_MANIFEST_NAME}",
            manifest_sha256=manifest_sha(version_dir),
            bundle_sha256=manifest.bundle_sha256,
            updated_at=manifest.created_at,
        ),
    )

    published = paths.read_published(root)
    rel = str(version_dir.relative_to(root))
    if rel not in published.paths():
        published.entries.append(
            PublishedEntry(
                path=rel,
                tree_sha=None,
                bundle_sha256=manifest.bundle_sha256,
                published_at=manifest.created_at,
                published_commit=None,
            )
        )
        published.entries.sort(key=lambda entry: entry.path)
        paths.write_published(root, published)

    (pdir / "README.md").write_text(
        render.partner_readme(partner, ledger, manifest), encoding="utf-8"
    )


def finalize_version(root: Path, partner: str, version: str) -> InputVersionManifest:
    """Recompute every hash for an unpublished version and rewrite its manifest.

    This is what the CI bot runs after someone edits a draft version through
    GitHub's web UI, where hashes cannot be computed client-side.
    """
    pdir = paths.partner_dir(root, partner)
    version_dir = pdir / version
    if not version_dir.is_dir():
        raise GlobiDataError(f"{version_dir} does not exist.")

    manifest = read_manifest(version_dir)
    parent = (
        read_manifest(pdir / manifest.parent_version)
        if manifest.parent_version
        else None
    )

    files: list[FileEntry] = []
    previous = {entry.path: entry for entry in manifest.files}
    for path in sorted(version_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = str(path.relative_to(version_dir))
        if rel == paths.INPUT_MANIFEST_NAME:
            continue
        prior = previous.get(rel)
        files.append(
            FileEntry(
                path=rel,
                role=prior.role if prior else None,
                bytes=file_size(path),
                sha256=file_sha256(path),
                simulation_affecting=_is_simulation_affecting(rel),
            )
        )

    changes, derived_impact = _diff_against_parent(
        files, manifest.external_files, parent
    )
    entries = [(e.path, e.sha256) for e in files if e.simulation_affecting]
    entries += [(e.path, e.sha256) for e in manifest.external_files if e.sha256]
    digest = bundle_sha256(entries)

    if parent is not None and digest == parent.bundle_sha256:
        raise GlobiDataError(
            f"{partner} {version} is byte-identical to {manifest.parent_version}. "
            "Either make a change or close the pull request."
        )

    manifest.files = files
    manifest.changes = changes
    manifest.impact = derived_impact
    manifest.bundle_sha256 = digest
    manifest.totals = Totals(
        file_count=len(files), bytes=sum(entry.size_bytes for entry in files)
    )
    yamlio.write(version_dir / paths.INPUT_MANIFEST_NAME, manifest.dump())
    return manifest


@dataclass
class FileDiff:
    """One file's difference between two versions."""

    path: str
    change: str
    old_bytes: int | None = None
    new_bytes: int | None = None
    old_sha: str | None = None
    new_sha: str | None = None


def diff_versions(root: Path, partner: str, a: str, b: str) -> list[FileDiff]:
    """Compare two input versions file by file."""
    pdir = paths.partner_dir(root, partner)
    left = read_manifest(pdir / a)
    right = read_manifest(pdir / b)

    old = {entry.path: entry for entry in [*left.files, *left.external_files]}
    new = {entry.path: entry for entry in [*right.files, *right.external_files]}

    diffs: list[FileDiff] = []
    for path in sorted(set(old) | set(new)):
        before = old.get(path)
        after = new.get(path)
        if before is None and after is not None:
            diffs.append(
                FileDiff(path, "added", None, after.size_bytes, None, after.sha256)
            )
        elif after is None and before is not None:
            diffs.append(
                FileDiff(path, "removed", before.size_bytes, None, before.sha256, None)
            )
        elif before and after and before.sha256 != after.sha256:
            diffs.append(
                FileDiff(
                    path,
                    "modified",
                    before.size_bytes,
                    after.size_bytes,
                    before.sha256,
                    after.sha256,
                )
            )
    return diffs


@dataclass
class VerifyIssue:
    """A problem found while verifying a version."""

    level: str
    path: str
    message: str


def verify_version(
    root: Path,
    partner: str,
    version: str,
    *,
    gis_root: Path | None = None,
    hash_gis: bool = False,
) -> list[VerifyIssue]:
    """Re-hash a version's files and check them against its manifest."""
    pdir = paths.partner_dir(root, partner)
    version_dir = pdir / version
    manifest = read_manifest(version_dir)
    issues: list[VerifyIssue] = []

    recorded = {entry.path: entry for entry in manifest.files}
    on_disk = {
        str(path.relative_to(version_dir))
        for path in version_dir.rglob("*")
        if path.is_file() and path.name != paths.INPUT_MANIFEST_NAME
    }

    for path in sorted(set(recorded) | on_disk):
        entry = recorded.get(path)
        full = version_dir / path
        if entry is None:
            issues.append(
                VerifyIssue("error", path, "present on disk but not in the manifest")
            )
            continue
        if not full.exists():
            issues.append(
                VerifyIssue("error", path, "in the manifest but missing on disk")
            )
            continue
        actual = file_sha256(full)
        if actual != entry.sha256:
            issues.append(
                VerifyIssue(
                    "error",
                    path,
                    f"sha256 mismatch: manifest {entry.sha256[:12]}..., disk {actual[:12]}...",
                )
            )
        elif full.stat().st_size != entry.size_bytes:
            issues.append(VerifyIssue("error", path, "size mismatch"))

    entries = [(e.path, e.sha256) for e in manifest.files if e.simulation_affecting]
    entries += [(e.path, e.sha256) for e in manifest.external_files if e.sha256]
    digest = bundle_sha256(entries)
    if digest != manifest.bundle_sha256:
        issues.append(
            VerifyIssue(
                "error",
                paths.INPUT_MANIFEST_NAME,
                f"bundle_sha256 mismatch: recorded {manifest.bundle_sha256[:12]}..., "
                f"recomputed {digest[:12]}...",
            )
        )

    for external in manifest.external_files:
        issues.extend(_verify_external(external, partner, gis_root, hash_gis))

    return issues


def _verify_external(
    external: ExternalFileEntry,
    partner: str,
    gis_root: Path | None,
    hash_gis: bool,
) -> list[VerifyIssue]:
    """Check that an external (not-stored) file is reachable and intact."""
    if gis_root is None:
        return []
    candidate = gis_root / partner / external.path
    if not candidate.exists():
        return [
            VerifyIssue(
                "warning",
                external.path,
                f"external file not found at {candidate}",
            )
        ]
    size = candidate.stat().st_size
    if size != external.size_bytes:
        # A fresh clone of globi-partners-data leaves a ~133-byte pointer here.
        hint = " - run `git lfs pull`" if size < 1024 else ""
        return [
            VerifyIssue(
                "error",
                external.path,
                f"expected {external.size_bytes} bytes, found {size}{hint}",
            )
        ]
    if hash_gis and external.sha256:
        actual = file_sha256(candidate)
        if actual != external.sha256:
            return [
                VerifyIssue(
                    "error",
                    external.path,
                    f"sha256 mismatch: manifest {external.sha256[:12]}..., "
                    f"disk {actual[:12]}...",
                )
            ]
    return []


def retract_version(root: Path, partner: str, version: str, reason: str) -> None:
    """Mark a published version as retracted.

    Only ``versions.yml`` is touched. The frozen version directory is never
    edited, which is what keeps the immutability rule mechanical.
    """
    pdir = paths.partner_dir(root, partner)
    ledger = paths.read_versions(pdir)
    entry = ledger.get(version)
    if entry is None:
        raise GlobiDataError(f"{partner} has no version {version}.")
    entry.status = "retracted"
    entry.retracted_reason = reason
    paths.write_versions(pdir, ledger)


def draft_version(
    root: Path,
    partner: str,
    *,
    summary: str,
    author: Author | None = None,
) -> InputVersionManifest:
    """Start the next version as an editable copy of the current one.

    This is what the browser-based flow uses: it produces a complete version
    directory on a branch that someone can then edit through GitHub's web UI —
    upload a replacement components DB, delete a weather file — without needing
    anything installed. Hashes are recomputed by ``finalize_version`` in CI on
    every push, and the version is promoted to ``active`` only when the pull
    request merges.

    The copy is verbatim, including the ``external_files`` records, so the GIS
    fingerprints survive even though those files are not present here.
    """
    pdir = paths.partner_dir(root, partner)
    versions = paths.list_versions(pdir)
    if not versions:
        raise GlobiDataError(
            f"{partner} has no versions yet; create v001 with `globi-data inputs new`."
        )

    parent_version = versions[-1]
    parent = read_manifest(pdir / parent_version)
    version = paths.next_version(pdir)
    version_dir = pdir / version

    shutil.copytree(pdir / parent_version, version_dir)

    manifest = parent.model_copy(deep=True)
    manifest.version = version
    manifest.parent_version = parent_version
    manifest.created_at = paths.utcnow()
    manifest.created_by = author or _author(None, None, root)
    manifest.summary = summary
    manifest.impact = "metadata-only"
    manifest.changes = []
    yamlio.write(version_dir / paths.INPUT_MANIFEST_NAME, manifest.dump())
    (version_dir / "README.md").write_text(
        render.input_version_readme(manifest), encoding="utf-8"
    )

    ledger = paths.read_versions(pdir)
    ledger.partner = partner
    ledger.versions.append(
        VersionEntry(
            version=version,
            status="draft",
            created_at=manifest.created_at,
            impact=manifest.impact,
            summary=summary,
        )
    )
    ledger.versions.sort(key=lambda entry: paths.version_number(entry.version))
    paths.write_versions(pdir, ledger)
    return manifest


def promote_version(root: Path, partner: str, version: str) -> InputVersionManifest:
    """Publish a draft version: make it current and freeze it.

    Run when the pull request that introduced the draft merges. Until this
    point the directory is editable; afterwards it is a permanent record.
    """
    pdir = paths.partner_dir(root, partner)
    version_dir = pdir / version
    if not version_dir.is_dir():
        raise GlobiDataError(f"{version_dir} does not exist.")

    ledger = paths.read_versions(pdir)
    entry = ledger.get(version)
    if entry is None:
        raise GlobiDataError(f"{partner} {version} has no entry in versions.yml.")
    if entry.status != "draft":
        raise GlobiDataError(
            f"{partner} {version} is {entry.status}, not a draft. Only drafts are promoted."
        )

    manifest = finalize_version(root, partner, version)
    # Drop the draft entry so _publish can re-add it as the single active one,
    # superseding whatever was current before.
    ledger.versions = [v for v in ledger.versions if v.version != version]
    paths.write_versions(pdir, ledger)
    _publish(root, partner, manifest, version_dir)
    return manifest
