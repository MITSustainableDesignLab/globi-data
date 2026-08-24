"""Deciding which results are still trustworthy.

An output version pins the input version that produced it. When the partner's
current input moves ahead of that pin, the results may be out of date — but only
if something that can actually change a simulation changed. That is what the
``impact`` field on each input version is for, and it is what keeps this check
useful instead of noisy: a README fix must not mark twenty-eight experiments as
needing a re-run.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import gitutil, paths
from . import inputs as inputs_mod
from . import outputs as outputs_mod
from .hashing import bundle_sha256, file_sha256
from .models import InputVersionManifest

# Ordered worst-first, so a summary can report the most serious state present.
SEVERITY = (
    "tampered",
    "broken-pin",
    "stale",
    "code-drift",
    "unpinned",
    "inferred",
    "metadata-drift",
    "ok",
)


@dataclass
class StatusRow:
    """One experiment's verdict."""

    experiment: str
    partner: str
    state: str
    pinned_version: str | None
    current_version: str | None
    detail: str = ""

    @property
    def is_problem(self) -> bool:
        """Whether this row represents something that needs attention."""
        return self.state in {"stale", "broken-pin", "tampered"}


def _tamper_reason(
    version_dir: Path,
    manifest: InputVersionManifest,
    cache: dict[Path, str | None] | None = None,
) -> str | None:
    """Return why a pinned version looks altered, or None if it is intact.

    Checks the bytes on disk rather than the hashes recorded in the manifest —
    an edit that changes a file but not its manifest entry is exactly the case
    worth catching.

    Args:
        version_dir: The frozen input version to inspect.
        manifest: That version's manifest.
        cache: Optional memo, since one version is typically pinned by several
            experiments and re-hashing it once per experiment is wasteful. Owned
            by the caller so it can never outlive a sweep and go stale.
    """
    if cache is not None and version_dir in cache:
        return cache[version_dir]

    reason: str | None = None
    entries: list[tuple[str, str]] = []
    for entry in manifest.files:
        if not entry.simulation_affecting:
            continue
        path = version_dir / entry.path
        if not path.exists():
            reason = f"{entry.path} is missing from the pinned input version."
            break
        actual = file_sha256(path)
        if actual != entry.sha256:
            reason = f"{entry.path} was modified after this version was published."
            break
        entries.append((entry.path, actual))

    if reason is None:
        entries += [(e.path, e.sha256) for e in manifest.external_files if e.sha256]
        if bundle_sha256(entries) != manifest.bundle_sha256:
            reason = "The pinned input version's contents no longer match its manifest."

    if cache is not None:
        cache[version_dir] = reason
    return reason


def _intervening_impacts(
    root: Path, partner: str, pinned: str, current: str
) -> list[str]:
    """Return the impact of every version strictly after ``pinned``, up to ``current``."""
    pdir = paths.partner_dir(root, partner)
    ledger = paths.read_versions(pdir)
    low = paths.version_number(pinned)
    high = paths.version_number(current)
    impacts: list[str] = []
    for entry in ledger.versions:
        number = paths.version_number(entry.version)
        if low < number <= high and entry.impact:
            impacts.append(entry.impact)
    return impacts


def evaluate_experiment(
    root: Path,
    experiment: str,
    *,
    partners_repo: Path | None = None,
    tamper_cache: dict[Path, str | None] | None = None,
) -> StatusRow:
    """Classify one experiment's current output version."""
    edir = paths.experiment_dir(root, experiment)
    version = paths.resolve_version(edir, "current")
    manifest = outputs_mod.read_output_manifest(edir / version)
    pin = manifest.provenance.input
    partner = manifest.partner

    pdir = paths.partner_dir(root, partner)
    available = paths.list_versions(pdir)
    current = None
    if available:
        pointer = paths.read_current(pdir)
        current = pointer.current if pointer else available[-1]

    if not pin.version:
        return StatusRow(
            experiment,
            partner,
            "unpinned",
            None,
            current,
            "No input version recorded; cannot judge.",
        )

    if pin.version not in available:
        return StatusRow(
            experiment,
            partner,
            "broken-pin",
            pin.version,
            current,
            f"Input version {pin.version} no longer exists.",
        )

    pinned_dir = pdir / pin.version

    # Has the pinned bundle itself been altered since it was recorded?
    try:
        pinned_manifest = inputs_mod.read_manifest(pinned_dir)
    except paths.GlobiDataError as exc:
        return StatusRow(
            experiment, partner, "broken-pin", pin.version, current, str(exc)
        )

    tampering = _tamper_reason(pinned_dir, pinned_manifest, tamper_cache)
    if tampering:
        return StatusRow(
            experiment, partner, "tampered", pin.version, current, tampering
        )

    if pin.manifest_sha256:
        actual = inputs_mod.manifest_sha(pinned_dir)
        if actual != pin.manifest_sha256:
            return StatusRow(
                experiment,
                partner,
                "tampered",
                pin.version,
                current,
                "The pinned input manifest changed after these results were recorded.",
            )

    if current and pin.version != current:
        impacts = _intervening_impacts(root, partner, pin.version, current)
        if "simulation-affecting" in impacts:
            n = impacts.count("simulation-affecting")
            return StatusRow(
                experiment,
                partner,
                "stale",
                pin.version,
                current,
                f"{n} later input version(s) changed simulation inputs. Re-run.",
            )
        return StatusRow(
            experiment,
            partner,
            "metadata-drift",
            pin.version,
            current,
            "Later input versions only changed documentation. No re-run needed.",
        )

    # Input is current. Check whether the simulation code has moved on.
    if partners_repo:
        recorded = (manifest.provenance.code.globi or {}).get("commit")
        actual = gitutil.submodule_commit(partners_repo, "packages/globi")
        if recorded and actual and recorded != actual:
            return StatusRow(
                experiment,
                partner,
                "code-drift",
                pin.version,
                current,
                f"Simulation code moved from {recorded[:8]} to {actual[:8]}.",
            )

    if pin.confidence == "inferred":
        return StatusRow(
            experiment,
            partner,
            "inferred",
            pin.version,
            current,
            "Input version was assumed during backfill, not recorded at run time.",
        )

    return StatusRow(experiment, partner, "ok", pin.version, current, "")


def evaluate_all(
    root: Path,
    *,
    partner: str | None = None,
    experiment: str | None = None,
    partners_repo: Path | None = None,
) -> list[StatusRow]:
    """Classify every recorded experiment, optionally filtered."""
    names = [experiment] if experiment else paths.list_experiments(root)
    # One cache per sweep: several experiments pin the same input version, and
    # re-hashing it for each of them would be pure waste.
    tamper_cache: dict[Path, str | None] = {}
    rows: list[StatusRow] = []
    for name in names:
        if partner and not name.startswith(f"{partner}/") and name != partner:
            continue
        try:
            rows.append(
                evaluate_experiment(
                    root,
                    name,
                    partners_repo=partners_repo,
                    tamper_cache=tamper_cache,
                )
            )
        except paths.GlobiDataError as exc:
            head = name.split("/")[0]
            rows.append(StatusRow(name, head, "broken-pin", None, None, str(exc)))
    rows.sort(key=lambda row: (SEVERITY.index(row.state), row.experiment))
    return rows
