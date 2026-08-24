"""Pydantic schemas for every versioned file in this repo.

Four families of file:

``input-version.yml``
    The manifest inside a frozen input version directory. Records what the
    bundle contains, what changed from its parent, where it came from, and the
    identity of the GIS file that is deliberately stored elsewhere.

``output-version.yml``
    The manifest for one run's results. A literal superset of the payload
    ``globi-partners latest-results --yaml-dir`` already writes, so existing
    consumers keep working, wrapped in a version envelope with full provenance.

``CURRENT.yml`` / ``versions.yml``
    The mutable pointers that live *outside* frozen version directories. This
    separation is what makes immutability a mechanical rule.

``published.yml``
    The append-only ledger of frozen directories, keyed by git tree sha.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Impact = Literal["simulation-affecting", "metadata-only"]
# `draft` is a version that exists but is not yet published: it lives on a
# branch, is still editable, and is not pointed at by CURRENT.yml or listed
# in published.yml. Merging promotes it to `active`.
VersionStatus = Literal["draft", "active", "superseded", "retracted"]
Confidence = Literal["exact", "inferred", "unknown"]
BundleKind = Literal["experiment", "raw"]

# Roles a file can play in a GloBI bundle. The manifest maps these to actual
# filenames because the filenames themselves are not consistent across partners:
# Sao_Paulo and MA use `.yml` where others use `.yaml`, Trondheim has no plain
# `manifest.yml`, and MA has neither `artifacts.yml` nor `manifest.yml`.
ROLES = (
    "experiment_manifest",
    "file_config",
    "gis_preprocessor_config",
    "overheating_config",
    "hourly_data_config",
    "db_file",
    "semantic_fields_file",
    "component_map_file",
    "epwzip_file",
    "epwzip_file_local",
    "ftmy_zip",
    "gis_file",
    "weather_lookup",
    "context",
)

# Files whose contents cannot change a simulation result. Excluded from
# bundle_sha256 so a README fix does not invalidate every downstream run.
NON_SIMULATION_FILENAMES = frozenset({"README.md", "input-version.yml"})


class _Base(BaseModel):
    """Base model that lets `bytes` be a YAML key without shadowing the builtin."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    def dump(self) -> dict[str, Any]:
        """Render to a plain dict using YAML key names, dropping unset optionals."""
        return self.model_dump(by_alias=True, exclude_none=False, mode="json")


class Author(_Base):
    """Who created a version."""

    name: str | None = None
    email: str | None = None


class SourceRef(_Base):
    """The repo and commit a bundle was assembled from."""

    repo: str
    remote: str | None = None
    commit: str | None = None
    dirty: bool | None = None
    path: str | None = None


class ChangeEntry(_Base):
    """One line of the human-readable changelog for a version."""

    path: str
    change: Literal["added", "modified", "removed"]
    note: str | None = None


class FileEntry(_Base):
    """A file stored in git inside this version directory."""

    path: str
    role: str | None = None
    size_bytes: int = Field(..., alias="bytes")
    sha256: str
    simulation_affecting: bool = True
    changed_from_parent: bool = False


class StoredIn(_Base):
    """Where an external file actually lives."""

    repo: str
    remote: str | None = None
    commit: str | None = None
    path: str
    storage: Literal["git-lfs", "git", "filesystem"] = "git-lfs"


class ExternalFileEntry(_Base):
    """A file deliberately NOT stored here, recorded for lineage only.

    This is how GIS files stay out of the repo without breaking traceability:
    the sha256 and byte size pin exactly which geometry produced a run, while
    the bytes remain under git-lfs in globi-partners-data.
    """

    path: str
    role: str
    size_bytes: int = Field(..., alias="bytes")
    sha256: str | None = None
    stored_in: StoredIn
    resolver: str
    reason: str


class RemoteFileEntry(_Base):
    """An input pushed to S3 instead of git, because it is too large."""

    path: str
    role: str | None = None
    s3_uri: str
    size_bytes: int | None = Field(default=None, alias="bytes")
    sha256: str | None = None


class GloBIBlock(_Base):
    """How the simulation code enters this bundle."""

    bundle_kind: BundleKind = "experiment"
    scenarios: dict[str, str] = Field(default_factory=dict)
    roles: dict[str, str | None] = Field(default_factory=dict)
    notes: str | None = None


class Totals(_Base):
    """Aggregate size of a version."""

    file_count: int
    size_bytes: int = Field(..., alias="bytes")


class InputVersionManifest(_Base):
    """`input-version.yml` — the manifest of a frozen input bundle."""

    schema_version: int = 1
    kind: Literal["input-version"] = "input-version"
    partner: str
    version: str
    parent_version: str | None = None
    created_at: str
    created_by: Author = Field(default_factory=Author)

    summary: str
    impact: Impact
    changes: list[ChangeEntry] = Field(default_factory=list)
    not_carried_over: list[str] = Field(default_factory=list)

    source: SourceRef
    globi: GloBIBlock = Field(default_factory=GloBIBlock)

    files: list[FileEntry] = Field(default_factory=list)
    external_files: list[ExternalFileEntry] = Field(default_factory=list)
    remote_files: list[RemoteFileEntry] = Field(default_factory=list)

    totals: Totals
    bundle_sha256: str

    def role_path(self, role: str) -> str | None:
        """Return the bundle-relative filename for a role, if it has one."""
        return self.globi.roles.get(role)

    def simulation_affecting_entries(self) -> list[tuple[str, str]]:
        """Return the ``(path, sha256)`` pairs that define ``bundle_sha256``."""
        pairs: list[tuple[str, str]] = [
            (entry.path, entry.sha256)
            for entry in self.files
            if entry.simulation_affecting
        ]
        pairs.extend(
            (entry.path, entry.sha256) for entry in self.external_files if entry.sha256
        )
        return pairs


class CurrentPointer(_Base):
    """`CURRENT.yml` — which version is current, plus its hashes for verification."""

    schema_version: int = 1
    partner: str | None = None
    experiment: str | None = None
    current: str
    manifest: str
    manifest_sha256: str
    bundle_sha256: str | None = None
    updated_at: str


class VersionEntry(_Base):
    """One row of the mutable per-partner version ledger."""

    version: str
    status: VersionStatus = "active"
    created_at: str
    impact: Impact | None = None
    summary: str = ""
    retracted_reason: str | None = None


class VersionsLedger(_Base):
    """`versions.yml` — the mutable status of every version of one partner or run.

    Lives outside the frozen version directories, which is what allows a bad
    version to be retracted without editing an immutable directory.
    """

    schema_version: int = 1
    partner: str | None = None
    experiment: str | None = None
    versions: list[VersionEntry] = Field(default_factory=list)

    def get(self, version: str) -> VersionEntry | None:
        """Return the ledger entry for a version, if present."""
        return next((v for v in self.versions if v.version == version), None)

    def active(self) -> VersionEntry | None:
        """Return the single active entry, if there is exactly one."""
        actives = [v for v in self.versions if v.status == "active"]
        return actives[0] if len(actives) == 1 else None


class PublishedEntry(_Base):
    """One frozen directory in the immutability ledger."""

    path: str
    tree_sha: str | None = None
    bundle_sha256: str | None = None
    published_at: str
    published_commit: str | None = None


class PublishedLedger(_Base):
    """`published.yml` — append-only record of directories that must never change."""

    schema_version: int = 1
    entries: list[PublishedEntry] = Field(default_factory=list)

    def paths(self) -> set[str]:
        """Return the set of frozen directory paths."""
        return {entry.path for entry in self.entries}


# --------------------------------------------------------------------------- #
# Outputs
# --------------------------------------------------------------------------- #


class GisPin(_Base):
    """The identity of the GIS file used by a run."""

    sha256: str | None = None
    size_bytes: int | None = Field(default=None, alias="bytes")


class InputPin(_Base):
    """Which input bundle produced a set of results.

    ``confidence`` matters: ``inferred`` means the pin was reconstructed during
    backfill and is an assumption, not an observation. It must never silently
    graduate to ``exact``.
    """

    partner: str
    version: str | None = None
    manifest_path: str | None = None
    manifest_sha256: str | None = None
    bundle_sha256: str | None = None
    confidence: Confidence = "unknown"
    gis_file: GisPin = Field(default_factory=GisPin)
    uploaded_artifacts: dict[str, str | None] = Field(default_factory=dict)


class CodeProvenance(_Base):
    """The code that produced a set of results."""

    globi_partners_data: dict[str, Any] | None = None
    globi: dict[str, Any] | None = None
    scythe_engine: str | None = None
    python: str | None = None


class StorageProvenance(_Base):
    """Where results live.

    ``bucket_prefix`` is always parsed from the observed URI, never read from
    the environment — the two have drifted (`globi-partners` in checked-in URIs
    versus `globi` in `.env`) and reconstructing a URI from env looks in the
    wrong place.
    """

    bucket: str | None = None
    bucket_prefix: str | None = None
    run_prefix: str | None = None


class RunProvenance(_Base):
    """Identity of the scythe run itself."""

    scythe_version: str | None = None
    run_timestamp: str | None = None
    hatchet_workflow_run_id: str | None = None
    submitted_at: str | None = None
    n_specs: int | None = None


class Provenance(_Base):
    """Everything needed to answer "what produced these numbers"."""

    input: InputPin
    code: CodeProvenance = Field(default_factory=CodeProvenance)
    storage: StorageProvenance = Field(default_factory=StorageProvenance)
    run: RunProvenance = Field(default_factory=RunProvenance)
    settings: dict[str, Any] = Field(default_factory=dict)


class ResultFileEntry(_Base):
    """One result parquet in S3."""

    result_key: str
    s3_uri: str
    size_bytes: int | None = Field(default=None, alias="bytes")
    sha256: str | None = None
    sha256_source: Literal["computed", "none"] = "none"
    etag: str | None = None
    last_modified: str | None = None


class OutputVersionManifest(_Base):
    """`output-version.yml` — one run's results plus full provenance.

    The first four fields reproduce, byte for byte, the payload written by
    ``_write_latest_results_yaml`` in globi-partners-data, so anything already
    parsing that format keeps working. ``version`` therefore means the *scythe*
    run version; the globi-data version is ``output_version``.
    """

    schema_version: int = 1
    kind: Literal["output-version"] = "output-version"

    # --- legacy-compatible block ---
    experiment: str
    version: str
    run_timestamp: str
    results: dict[str, str] = Field(default_factory=dict)

    # --- version envelope ---
    output_version: str
    parent_version: str | None = None
    status: VersionStatus = "active"
    created_at: str
    created_by: Author = Field(default_factory=Author)
    summary: str = ""

    partner: str
    weather: str | None = None
    scenario_kind: str | None = None
    scenario_value: str | None = None

    provenance: Provenance
    result_files: list[ResultFileEntry] = Field(default_factory=list)
    totals: Totals


class ResultIndex(_Base):
    """Pointer to the CSV holding a batch's result URIs."""

    path: str
    columns: list[str]
    rows: int
    sha256: str


class AllocationInfo(_Base):
    """Shape of a batch allocation."""

    manifest: str | None = None
    n_tracts: int | None = None
    specs_per_tract: int | None = None


class OutputBatchManifest(_Base):
    """`output-version.yml` for a batch of runs too numerous to store one-per-directory.

    MA allocates ~355 specs per (tract, weather, scenario) across ~1600 census
    tracts. One directory per run would create tens of thousands of folders and
    make the repo unbrowsable, so a batch gets a single manifest plus a
    ``results.csv`` index.
    """

    schema_version: int = 1
    kind: Literal["output-batch"] = "output-batch"

    batch: str
    output_version: str
    parent_version: str | None = None
    status: VersionStatus = "active"
    created_at: str
    created_by: Author = Field(default_factory=Author)
    summary: str = ""

    partner: str
    provenance: Provenance
    result_index: ResultIndex
    allocation: AllocationInfo = Field(default_factory=AllocationInfo)
    totals: Totals
