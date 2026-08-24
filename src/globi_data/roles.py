"""Curating a source partner directory into a versioned bundle.

The source directories in globi-partners-data accumulated backups, build
intermediates and one-off exports alongside the real inputs. Copying them
wholesale would bloat every version and blur what actually drives a simulation,
so this module plans an explicit copy set and reports everything it leaves
behind. Nothing is dropped silently: skipped files are recorded in the version
manifest's ``not_carried_over`` list and shown in the version README.

Roles rather than filenames are the organising idea, because the filenames are
genuinely inconsistent:

- Sao_Paulo and MA use ``component-map.yml`` / ``semantic-fields.yml`` where the
  others use ``.yaml``
- Trondheim has no plain ``manifest.yml``, only ``manifest_LowEfficiency.yml``
  and ``manifest_HighEfficiency.yml``
- MA has neither ``artifacts.yml`` nor ``manifest.yml``
- Singapore's GIS file is ``buildings-singapore.geojson``
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from pathlib import Path

from . import yamlio
from .paths import FAIL_BYTES, WARN_BYTES, GlobiDataError

# Config files that are always part of a bundle when present.
CONFIG_NAMES = (
    "artifacts.yml",
    "artifacts.yaml",
    "gis-preprocessor.yml",
    "gis-preprocessor.yaml",
    "overheating-config.yml",
    "overheating-config.yaml",
    "hourly-data-config.yml",
    "hourly-data-config.yaml",
    "weather-lookup.yml",
    "weather-lookup.yaml",
)

# Prefix families where partner-specific variants are meaningful inputs and are
# carried alongside the canonical file (e.g. Manchester's `-manchester-dsr`
# component map and semantic fields, which drive its DSR scenario).
VARIANT_PREFIXES = ("component-map", "semantic-fields")

# Directories copied wholesale (minus the excluded patterns below).
TREE_DIRS = ("weather", "weather_ftmy", "runs")

# Backups, build intermediates and derived exports. Each entry pairs a glob with
# the reason shown to the user, so a skip is never mysterious.
EXCLUDE_PATTERNS: tuple[tuple[str, str], ...] = (
    ("*.epw.txt", "FTMY build intermediate; the real .epw is under weather_ftmy/"),
    ("components-lib-old.db", "superseded backup of components-lib.db"),
    ("components-lib-og.db", "superseded backup of components-lib.db"),
    ("*-old.db", "superseded backup"),
    ("*-og.db", "superseded backup"),
    ("*.DS_Store", "macOS metadata"),
    ("*.tmp", "temporary file"),
    ("*.log", "log file"),
    ("*.bak", "backup file"),
    (".ipynb_checkpoints/*", "notebook checkpoint"),
)

# Extensions that are never stored in git here. GIS geometry is recorded as an
# external file (hash + location) instead; result parquets belong in S3.
EXTERNAL_EXTENSIONS = (".geojson", ".gpkg", ".shp")

# Per-partner additions that the generic rules cannot infer.
PARTNER_EXTRAS: dict[str, tuple[str, ...]] = {
    "MA": ("context-small.parquet", "tl_2024_25_tract.zip"),
}


@dataclass
class PlannedFile:
    """A file selected for inclusion in a bundle."""

    rel_path: str
    source: Path
    role: str | None = None


@dataclass
class PlannedExternal:
    """A file recorded for lineage but deliberately not stored."""

    rel_path: str
    source: Path
    role: str
    reason: str


@dataclass
class BundlePlan:
    """The full decision about what a new version will contain."""

    partner: str
    source: Path
    bundle_kind: str = "experiment"
    roles: dict[str, str | None] = field(default_factory=dict)
    scenarios: dict[str, str] = field(default_factory=dict)
    include: list[PlannedFile] = field(default_factory=list)
    external: list[PlannedExternal] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    notes: str | None = None


def _is_remote(ref: object) -> bool:
    """Whether a reference points at a remote location rather than a local file.

    Mirrors the same helper in globi-partners-data so the two repos agree on what
    counts as remote.
    """
    return isinstance(ref, str) and ref.startswith(("http://", "https://", "s3://"))


def _excluded(rel_path: str) -> str | None:
    """Return the reason a path is excluded, or None if it is not."""
    name = Path(rel_path).name
    for pattern, reason in EXCLUDE_PATTERNS:
        if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(rel_path, pattern):
            return reason
    return None


def _load_artifacts(source: Path) -> tuple[dict[str, object], str | None]:
    """Load a partner's artifacts.yml, returning its data and filename."""
    for name in ("artifacts.yml", "artifacts.yaml"):
        path = source / name
        if path.exists():
            data = yamlio.read(path) or {}
            if not isinstance(data, dict):
                raise GlobiDataError(f"{path} did not parse as a mapping.")
            return data, name
    return {}, None


def _pick_manifest(source: Path) -> list[str]:
    """Choose which ``manifest*.yml`` files to carry.

    A plain ``manifest.yml`` wins outright when present, which drops redundant
    scenario copies like Nairobi's ``manifest_noAC.yml``. When there is no plain
    manifest — Trondheim's case — every variant is carried, because one of them
    is the only manifest that exists.
    """
    for name in ("manifest.yml", "manifest.yaml"):
        if (source / name).exists():
            return [name]
    variants = sorted(p.name for p in source.glob("manifest*.y*ml") if p.is_file())
    return variants


def _resolve_role_file(source: Path, ref: object, role: str) -> str | None:
    """Resolve an artifacts.yml reference to a filename inside the source dir.

    The stored paths are repo-root-relative and therefore meaningless once the
    bundle moves, so only the basename is trusted. This is the same rebasing the
    consumer-side resolver performs.
    """
    if ref is None or _is_remote(ref):
        return None
    name = Path(str(ref)).name
    if (source / name).exists():
        return name
    # Some references point into a subdirectory, e.g. Singapore's local epwzip
    # under weather/.
    matches = sorted(source.rglob(name))
    if matches:
        return str(matches[0].relative_to(source))
    raise GlobiDataError(
        f"{role} refers to {ref!r} but no file named {name!r} exists under {source}."
    )


class _Selection:
    """Accumulates the chosen files, keeping the first role assigned to each."""

    def __init__(self, source: Path) -> None:
        self.source = source
        self.chosen: dict[str, PlannedFile] = {}

    def add(self, rel: str, role: str | None = None) -> None:
        """Select ``rel`` if it exists, recording its role the first time one is given."""
        path = self.source / rel
        if not path.is_file():
            return
        existing = self.chosen.get(rel)
        if existing is None:
            self.chosen[rel] = PlannedFile(rel_path=rel, source=path, role=role)
        elif role and not existing.role:
            existing.role = role

    def __contains__(self, rel: str) -> bool:
        return rel in self.chosen


# Conventional filenames for each role, used when there is no artifacts.yml to
# read them from. MA is the case that matters: it has a components DB, semantic
# fields and a component map, but no artifacts.yml, so without this its roles
# would all be null and the consumer-side resolver would have nothing to work
# with.
ROLE_FALLBACKS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("db_file", ("components-lib.db", "components.db")),
    ("semantic_fields_file", ("semantic-fields.yaml", "semantic-fields.yml")),
    ("component_map_file", ("component-map.yaml", "component-map.yml")),
)


def _plan_manifest_and_artifacts(
    plan: BundlePlan,
    source: Path,
    artifacts_name: str | None,
    picked: _Selection,
) -> None:
    """Select the experiment manifest and artifacts.yml."""
    manifests = _pick_manifest(source)
    if manifests:
        plan.roles["experiment_manifest"] = manifests[0]
        for name in manifests:
            picked.add(name, "experiment_manifest" if name == manifests[0] else None)
        if len(manifests) > 1:
            # No plain manifest.yml exists (Trondheim's case), so the choice
            # among the scenario variants is arbitrary. Say so, and make clear
            # the registry — not this file — decides which scenario runs.
            others = ", ".join(manifests[1:])
            plan.warnings.append(
                f"No plain manifest.yml; carrying {', '.join(manifests)} and naming "
                f"{manifests[0]} as the experiment manifest. The scenario actually run "
                f"is set by experiments.yaml, not by this file. Also carried: {others}."
            )

    if artifacts_name:
        plan.roles["file_config"] = artifacts_name
        picked.add(artifacts_name, "file_config")


def _plan_fallback_roles(plan: BundlePlan, source: Path, picked: _Selection) -> None:
    """Fill roles by conventional filename for bundles with no artifacts.yml."""
    for role, candidates in ROLE_FALLBACKS:
        if plan.roles.get(role):
            continue
        for name in candidates:
            if (source / name).is_file():
                plan.roles[role] = name
                picked.add(name, role)
                break


def _plan_artifact_roles(
    plan: BundlePlan,
    source: Path,
    artifacts: dict[str, object],
    picked: _Selection,
) -> None:
    """Resolve the file roles declared by artifacts.yml.

    The stored paths are repo-root-relative and meaningless once the bundle
    moves, so only the basename is trusted.
    """
    for role in ("db_file", "semantic_fields_file", "component_map_file"):
        resolved = _resolve_role_file(source, artifacts.get(role), role)
        plan.roles[role] = resolved
        if resolved:
            picked.add(resolved, role)

    # epwzip_file is the one artifacts.yml field that already tolerates a URI.
    # Remote values are kept verbatim; Singapore's local zip is carried and
    # exposed as `epwzip_file_local` so the consumer can rebase it.
    epwzip = artifacts.get("epwzip_file")
    if _is_remote(epwzip):
        plan.roles["epwzip_file"] = str(epwzip)
    elif epwzip:
        local = _resolve_role_file(source, epwzip, "epwzip_file")
        plan.roles["epwzip_file"] = None
        plan.roles["epwzip_file_local"] = local
        if local:
            picked.add(local, "epwzip_file_local")


def _plan_gis(
    plan: BundlePlan,
    source: Path,
    artifacts: dict[str, object],
    external_names: set[str],
) -> None:
    """Record the GIS geometry as an external file rather than selecting it.

    The bytes stay in globi-partners-data under git-lfs; only the fingerprint
    and location are stored here, which is what keeps results traceable without
    putting a gigabyte of geometry in this repo.
    """
    gis_ref = artifacts.get("gis_file")
    if gis_ref and not _is_remote(gis_ref):
        gis_name: str | None = Path(str(gis_ref)).name
    else:
        candidates = sorted(p.name for p in source.glob("*.geojson"))
        gis_name = candidates[0] if candidates else None

    if not gis_name:
        return

    plan.roles["gis_file"] = f"external:{gis_name}"
    gis_path = source / gis_name
    if not gis_path.is_file():
        plan.warnings.append(
            f"artifacts.yml names {gis_name} but it is not present in {source}; "
            "recorded as external with no hash."
        )
        return

    plan.external.append(
        PlannedExternal(
            rel_path=gis_name,
            source=gis_path,
            role="gis_file",
            reason=(
                f"{gis_path.stat().st_size / 1e6:.0f} MB of geometry - kept under "
                "git-lfs in globi-partners-data where it already lives."
            ),
        )
    )
    external_names.add(gis_name)


_CONFIG_ROLES: dict[str, str] = {
    "gis-preprocessor.yml": "gis_preprocessor_config",
    "gis-preprocessor.yaml": "gis_preprocessor_config",
    "overheating-config.yml": "overheating_config",
    "overheating-config.yaml": "overheating_config",
    "hourly-data-config.yml": "hourly_data_config",
    "hourly-data-config.yaml": "hourly_data_config",
    "weather-lookup.yml": "weather_lookup",
    "weather-lookup.yaml": "weather_lookup",
}


def _plan_configs(plan: BundlePlan, source: Path, picked: _Selection) -> None:
    """Select the generic config files and any partner-specific variants."""
    for name in CONFIG_NAMES:
        if not (source / name).is_file():
            continue
        role = _CONFIG_ROLES.get(name)
        picked.add(name, role)
        if role and role not in plan.roles:
            plan.roles[role] = name

    # Variant configs such as Manchester's `-manchester-dsr` component map and
    # semantic fields, which drive its DSR scenario.
    for prefix in VARIANT_PREFIXES:
        for path in sorted(source.glob(f"{prefix}*.y*ml")):
            picked.add(path.name)


def _plan_trees(plan: BundlePlan, source: Path, picked: _Selection) -> None:
    """Select whole subtrees (weather, weather_ftmy, runs), minus exclusions."""
    for tree in TREE_DIRS:
        tree_path = source / tree
        if not tree_path.is_dir():
            continue
        for path in sorted(tree_path.rglob("*")):
            if not path.is_file():
                continue
            rel = str(path.relative_to(source))
            reason = _excluded(rel)
            if reason:
                plan.skipped.append((rel, reason))
            else:
                picked.add(rel)


def _plan_raw(plan: BundlePlan, source: Path, picked: _Selection) -> None:
    """Carry loose files for partners that have no artifacts.yml.

    Korea and similar raw drops are not wired into experiments.yaml, so the
    role-driven rules select nothing. Preserving their files verbatim is better
    than versioning an empty bundle.
    """
    for path in sorted(source.glob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() in EXTERNAL_EXTENSIONS:
            continue
        if _excluded(path.name):
            continue
        picked.add(path.name)
    plan.notes = (
        "Raw drop: this partner has no artifacts.yml or manifest.yml and is not "
        "wired into experiments.yaml. Files are carried as-is for preservation."
    )


def _skip_reason(path: Path, rel: str, carried_manifest: str | None) -> str:
    """Explain why a file was not selected. Never returns an empty reason.

    The reason ends up in the manifest and the version README, so it has to be
    specific enough that someone can tell whether the omission was a mistake.
    """
    reason = _excluded(rel)
    if reason:
        return reason
    name = path.name
    if carried_manifest and fnmatch.fnmatch(name, "manifest*.y*ml"):
        return f"redundant scenario manifest; {carried_manifest} is the one carried"
    if path.suffix.lower() == ".xlsx":
        return "source spreadsheet; the simulation reads the .db built from it"
    if path.suffix.lower() in EXTERNAL_EXTENSIONS:
        return "GIS geometry is not stored in this repo"
    if path.suffix.lower() in (".parquet", ".pq"):
        return "result/context parquet not part of this bundle"
    return "not a recognised bundle file"


def _plan_skipped(
    plan: BundlePlan, source: Path, picked: _Selection, external_names: set[str]
) -> None:
    """Record every source file that was not selected, with a reason.

    Nothing is dropped silently: these end up in the manifest's
    ``not_carried_over`` list and in the version README.
    """
    already = {rel for rel, _ in plan.skipped}
    carried_manifest = plan.roles.get("experiment_manifest")
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        rel = str(path.relative_to(source))
        if rel in picked or rel in external_names or rel in already:
            continue
        plan.skipped.append((rel, _skip_reason(path, rel, carried_manifest)))


def _check_sizes(plan: BundlePlan, picked: _Selection) -> None:
    """Enforce the size guardrails that keep this repo clonable.

    Raises:
        GlobiDataError: if a selected file exceeds the hard limit.
    """
    for planned in picked.chosen.values():
        size = planned.source.stat().st_size
        if size > FAIL_BYTES:
            raise GlobiDataError(
                f"{planned.rel_path} is {size / 1e6:.0f} MB, over the "
                f"{FAIL_BYTES / 1e6:.0f} MB limit for a git-stored input. Push it to S3 "
                "and record it under `remote_files` instead."
            )
        if size > WARN_BYTES:
            plan.warnings.append(
                f"{planned.rel_path} is {size / 1e6:.0f} MB - large for a git-stored input."
            )


def plan_bundle(
    partner: str,
    source: Path,
    *,
    extra_includes: tuple[str, ...] = (),
) -> BundlePlan:
    """Decide what a new version of ``partner`` should contain.

    Args:
        partner: Partner name, used to look up per-partner extras.
        source: The directory to assemble from.
        extra_includes: Glob patterns that force inclusion of otherwise-skipped
            files.

    Returns:
        A fully populated plan. Nothing is copied; that is the caller's job.
    """
    if not source.is_dir():
        raise GlobiDataError(f"Source directory {source} does not exist.")

    plan = BundlePlan(partner=partner, source=source)
    artifacts, artifacts_name = _load_artifacts(source)
    plan.bundle_kind = "experiment" if artifacts_name else "raw"

    picked = _Selection(source)
    external_names: set[str] = set()

    _plan_manifest_and_artifacts(plan, source, artifacts_name, picked)
    _plan_artifact_roles(plan, source, artifacts, picked)
    _plan_gis(plan, source, artifacts, external_names)
    _plan_configs(plan, source, picked)
    _plan_trees(plan, source, picked)

    for name in PARTNER_EXTRAS.get(partner, ()):
        role = "context" if "context" in name else None
        picked.add(name, role)
        if role and (source / name).is_file():
            plan.roles.setdefault("context", name)

    if plan.bundle_kind == "raw":
        _plan_raw(plan, source, picked)
        _plan_fallback_roles(plan, source, picked)

    for pattern in extra_includes:
        for path in sorted(source.rglob(pattern)):
            if path.is_file():
                picked.add(str(path.relative_to(source)))

    _plan_skipped(plan, source, picked, external_names)
    _check_sizes(plan, picked)

    plan.include = sorted(picked.chosen.values(), key=lambda item: item.rel_path)
    plan.skipped.sort()
    return plan
