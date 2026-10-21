"""Repository-wide validation, and the immutability rule.

``run_checks`` is what CI runs as a single command. It deliberately needs no AWS
credentials and no git-lfs, so a pull request from anyone can be validated.

The immutability rule is the load-bearing part: a directory listed in
``published.yml`` must never be modified. Evaluating that against the ledger *as
of the merge base* is what lets a version be edited freely inside the pull
request that introduces it, and freezes it the moment that PR merges.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import gitutil, index, paths, yamlio
from . import inputs as inputs_mod
from . import outputs as outputs_mod
from . import surrogates as surrogates_mod
from .models import PublishedLedger
from .paths import GlobiDataError


@dataclass
class Problem:
    """One validation failure."""

    level: str
    where: str
    message: str


def _check_inputs(root: Path, gis_root: Path | None) -> list[Problem]:
    """Validate every input version: schema, hashes, pointers, ledger."""
    problems: list[Problem] = []
    for partner in paths.list_partners(root):
        pdir = paths.partner_dir(root, partner)
        versions = paths.list_versions(pdir)
        ledger = paths.read_versions(pdir)

        for version in versions:
            try:
                issues = inputs_mod.verify_version(
                    root, partner, version, gis_root=gis_root
                )
            except Exception as exc:
                problems.append(Problem("error", f"{partner}/{version}", str(exc)))
                continue
            problems.extend(
                Problem(issue.level, f"{partner}/{version}/{issue.path}", issue.message)
                for issue in issues
            )
            if ledger.get(version) is None:
                problems.append(
                    Problem(
                        "error",
                        f"{partner}/{version}",
                        "version directory has no entry in versions.yml",
                    )
                )

        for entry in ledger.versions:
            if entry.version not in versions:
                problems.append(
                    Problem(
                        "error",
                        f"{partner}/{entry.version}",
                        "versions.yml lists a version with no directory",
                    )
                )

        actives = [v for v in ledger.versions if v.status == "active"]
        if len(actives) != 1 and versions:
            problems.append(
                Problem(
                    "error",
                    partner,
                    f"versions.yml has {len(actives)} active versions; expected exactly 1",
                )
            )

        pointer = paths.read_current(pdir)
        if pointer is None:
            if versions:
                problems.append(Problem("error", partner, "missing CURRENT.yml"))
        else:
            if pointer.current not in versions:
                problems.append(
                    Problem(
                        "error",
                        partner,
                        f"CURRENT.yml points at {pointer.current}, which does not exist",
                    )
                )
            else:
                actual = inputs_mod.manifest_sha(pdir / pointer.current)
                if actual != pointer.manifest_sha256:
                    problems.append(
                        Problem(
                            "error",
                            partner,
                            "CURRENT.yml manifest_sha256 does not match the manifest on disk",
                        )
                    )
    return problems


def _check_outputs(root: Path) -> list[Problem]:
    """Validate every output version: schema, URI shape, pointers."""
    problems: list[Problem] = []
    for experiment in paths.list_experiments(root):
        edir = paths.experiment_dir(root, experiment)
        versions = paths.list_versions(edir)
        for version in versions:
            where = f"{experiment}/{version}"
            try:
                manifest = outputs_mod.read_output_manifest(edir / version)
            except Exception as exc:
                problems.append(Problem("error", where, str(exc)))
                continue

            if manifest.experiment != experiment:
                problems.append(
                    Problem(
                        "error",
                        where,
                        f"manifest says experiment {manifest.experiment!r} but lives under "
                        f"{experiment!r}",
                    )
                )
            for entry in manifest.result_files:
                try:
                    ref = outputs_mod.parse_s3_uri(entry.s3_uri)
                except GlobiDataError as exc:
                    problems.append(Problem("error", where, str(exc)))
                    continue
                if not ref.experiment:
                    problems.append(
                        Problem(
                            "warning",
                            where,
                            f"{entry.result_key}: URI does not match the expected "
                            "<prefix>/<experiment>/<version>/<timestamp>/final/<key>.pq shape",
                        )
                    )
            if manifest.results != {
                e.result_key: e.s3_uri for e in manifest.result_files
            }:
                problems.append(
                    Problem(
                        "error",
                        where,
                        "the legacy `results` block and `result_files` disagree",
                    )
                )

        pointer = paths.read_current(edir)
        if pointer and pointer.current not in versions:
            problems.append(
                Problem(
                    "error",
                    experiment,
                    f"CURRENT.yml points at {pointer.current}, which does not exist",
                )
            )
    return problems


def _check_surrogates(root: Path) -> list[Problem]:
    """Validate every surrogate version against its transforms and pinned inputs."""
    problems: list[Problem] = []
    for partner in paths.list_surrogates(root):
        for version in paths.list_versions(paths.surrogate_dir(root, partner)):
            where = f"surrogates/{partner}/{version}"
            problems.extend(
                Problem(f.level, where, f.message)
                for f in surrogates_mod.validate_surrogate(root, partner, version)
            )
    return problems


def _check_generated(root: Path, partners_repo: Path | None) -> list[Problem]:
    """Report generated pages that are out of date."""
    changes = index.rebuild(root, write=False, partners_repo=partners_repo)
    return [
        Problem(
            "error",
            str(change.path.relative_to(root)),
            f"generated file is {change.reason}; run `globi-data index --write`",
        )
        for change in changes
    ]


def check_immutability(
    root: Path, *, base: str | None = None, staged: bool = False
) -> list[Problem]:
    """Verify that no published version directory has been modified.

    Args:
        root: Repo root.
        base: A git ref to diff against. The published ledger is read *as of
            that ref*, so versions introduced in the current branch are still
            editable while versions that existed before it are frozen.
        staged: Check the index instead of a ref range (used by the pre-commit
            hook).
    """
    if not gitutil.is_repo(root):
        return []

    if staged:
        changes = gitutil.staged_paths(root)
        ledger = paths.read_published(root)
        baseline = "HEAD"
    else:
        if base is None:
            return []
        merge_base = gitutil.merge_base(root, base, "HEAD") or base
        baseline = merge_base
        changes = gitutil.changed_paths(root, merge_base)
        # Read the ledger as of the merge base, not the working tree: entries
        # added by this branch describe versions this branch is still creating.
        text = gitutil.file_at_ref(root, merge_base, paths.PUBLISHED_FILE)
        parsed = yamlio.loads(text) if text else None
        ledger = PublishedLedger.model_validate(parsed) if parsed else PublishedLedger()

    # A version only becomes immutable once its files are actually in the
    # baseline. `published.yml` gains its entry when the version directory is
    # written, which is before the first commit of that directory — so without
    # this filter the initial commit of a brand-new version would be rejected as
    # tampering with itself. Same reasoning covers a version created inside a
    # pull request: it is not in the merge base, so it stays editable there.
    frozen = {
        directory
        for directory in ledger.paths()
        if gitutil.tree_sha(root, directory, ref=baseline)
    }
    if not frozen:
        return []

    problems: list[Problem] = []
    for state, path in changes:
        owner = next((d for d in frozen if path == d or path.startswith(f"{d}/")), None)
        if owner is None:
            continue
        if state.startswith("A"):
            problems.append(
                Problem(
                    "error",
                    path,
                    f"adds a file to published version {owner}, which is frozen",
                )
            )
        else:
            problems.append(
                Problem(
                    "error",
                    path,
                    f"modifies published version {owner}, which is frozen. "
                    "Create a new version instead: `globi-data inputs new <partner>`",
                )
            )
    return problems


def run_checks(
    root: Path,
    *,
    offline: bool = True,
    gis_root: Path | None = None,
    partners_repo: Path | None = None,
    since: str | None = None,
) -> list[Problem]:
    """Run every validation CI performs, in one pass."""
    problems: list[Problem] = []
    problems.extend(_check_inputs(root, gis_root))
    problems.extend(_check_outputs(root))
    problems.extend(_check_surrogates(root))
    problems.extend(_check_generated(root, partners_repo))
    if since:
        problems.extend(check_immutability(root, base=since))
    if not offline:
        problems.append(
            Problem(
                "warning",
                "s3",
                "online checks are not implemented; use `outputs verify`",
            )
        )
    return problems
