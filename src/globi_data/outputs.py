"""Recording, verifying and downloading run outputs.

Result parquets stay in S3 — there are roughly 11 GB of them — so what is
versioned here is the *pointer plus provenance*: which S3 objects hold the
results, and exactly which inputs and code produced them.

The manifest's first four fields reproduce the payload that
``globi-partners latest-results --yaml-dir`` already writes, so anything
consuming that format keeps working unchanged.
"""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from . import gitutil, paths, render, yamlio
from . import inputs as inputs_mod
from .hashing import file_sha256
from .models import (
    Author,
    CodeProvenance,
    CurrentPointer,
    GisPin,
    InputPin,
    OutputVersionManifest,
    Provenance,
    PublishedEntry,
    ResultFileEntry,
    RunProvenance,
    StorageProvenance,
    Totals,
    VersionEntry,
)
from .paths import GlobiDataError


@dataclass(frozen=True)
class S3Ref:
    """The parts of an S3 result URI that matter for provenance."""

    bucket: str
    key: str
    prefix: str | None
    experiment: str | None
    version: str | None
    run_timestamp: str | None


def parse_s3_uri(uri: str) -> S3Ref:
    """Pull bucket, prefix, experiment, version and timestamp out of a result URI.

    Result URIs look like::

        s3://ml-for-bem/globi-partners/Ahmedabad/tmy/BAU/v1.0.0/2026-06-08_12-27-10/final/EnergyAndPeak.pq

    The prefix is read from the URI rather than the environment on purpose: the
    checked-in URIs use ``globi-partners`` while ``.env`` currently says
    ``globi``, and reconstructing a URI from the environment would look in the
    wrong place.
    """
    parsed = urlparse(uri)
    if parsed.scheme != "s3" or not parsed.netloc:
        raise GlobiDataError(f"{uri!r} is not an s3:// URI.")
    bucket = parsed.netloc
    key = parsed.path.lstrip("/")
    parts = key.split("/")

    prefix = experiment = version = timestamp = None
    if "final" in parts:
        idx = parts.index("final")
        if idx >= 3:
            timestamp = parts[idx - 1]
            version = parts[idx - 2]
            prefix = parts[0]
            experiment = "/".join(parts[1 : idx - 2])
    return S3Ref(bucket, key, prefix, experiment, version, timestamp)


def split_experiment(experiment: str) -> tuple[str, str | None, str | None]:
    """Split a run name into ``(partner, weather, scenario)``.

    Handles both the three-part partner form (``Ahmedabad/tmy/BAU``) and the
    four-part MA tract form (``MA/000101/tmy/baseline``).
    """
    parts = experiment.split("/")
    if len(parts) == 1:
        return parts[0], None, None
    if len(parts) == 2:
        return parts[0], None, parts[1]
    return parts[0], parts[-2], parts[-1]


def read_output_manifest(version_dir: Path) -> OutputVersionManifest:
    """Load the ``output-version.yml`` inside an output version directory."""
    path = version_dir / paths.OUTPUT_MANIFEST_NAME
    if not path.exists():
        raise GlobiDataError(f"No {paths.OUTPUT_MANIFEST_NAME} in {version_dir}.")
    return OutputVersionManifest.model_validate(yamlio.read(path))


def _capture_code_provenance(partners_repo: Path | None) -> CodeProvenance:
    """Snapshot the code that produced a run."""
    if partners_repo is None or not partners_repo.exists():
        return CodeProvenance(python=".".join(map(str, sys.version_info[:3])))

    gpd = gitutil.capture(partners_repo, "globi-partners-data")
    globi_commit = gitutil.submodule_commit(partners_repo, "packages/globi")
    globi_dir = partners_repo / "packages" / "globi"
    globi_info: dict[str, object] | None = None
    if globi_commit or globi_dir.exists():
        globi_info = {
            "commit": globi_commit,
            "describe": gitutil.describe(globi_dir) if globi_dir.exists() else None,
        }

    scythe_version = None
    try:
        from importlib.metadata import version as _pkg_version

        scythe_version = _pkg_version("scythe-engine")
    except Exception:
        scythe_version = None

    return CodeProvenance(
        globi_partners_data={
            "commit": gpd.commit,
            "dirty": gpd.dirty,
            "remote": gpd.remote,
        },
        globi=globi_info,
        scythe_engine=scythe_version,
        python=".".join(map(str, sys.version_info[:3])),
    )


def _input_pin(
    root: Path,
    partner: str,
    requested: str | None,
    confidence: str,
) -> InputPin:
    """Resolve which input version a run was built from."""
    pdir = paths.partner_dir(root, partner)
    if not paths.list_versions(pdir):
        return InputPin(partner=partner, confidence="unknown")

    version = paths.resolve_version(pdir, requested or "current")
    version_dir = pdir / version
    manifest = inputs_mod.read_manifest(version_dir)
    gis = next((e for e in manifest.external_files if e.role == "gis_file"), None)
    return InputPin(
        partner=partner,
        version=version,
        manifest_path=str((version_dir / paths.INPUT_MANIFEST_NAME).relative_to(root)),
        manifest_sha256=inputs_mod.manifest_sha(version_dir),
        bundle_sha256=manifest.bundle_sha256,
        confidence=confidence,  # type: ignore[arg-type]
        gis_file=GisPin(
            sha256=gis.sha256 if gis else None,
            bytes=gis.size_bytes if gis else None,
        ),
    )


def record_experiment(
    root: Path,
    experiment: str,
    results: dict[str, str],
    *,
    summary: str,
    input_version: str | None = None,
    confidence: str = "inferred",
    partners_repo: Path | None = None,
    scenario_kinds: dict[tuple[str, str], str] | None = None,
    partner_aliases: dict[str, str] | None = None,
    sizes: dict[str, tuple[int | None, str | None, str | None]] | None = None,
    allow_noop: bool = False,
    author: Author | None = None,
) -> OutputVersionManifest | None:
    """Record a new output version for one experiment.

    Returns:
        The written manifest, or ``None`` if the no-op guard suppressed it.
    """
    if not results:
        raise GlobiDataError(f"No result URIs supplied for {experiment}.")

    refs = {key: parse_s3_uri(uri) for key, uri in results.items()}
    first = next(iter(refs.values()))
    run_partner, weather, scenario = split_experiment(experiment)
    # The run may be named differently from the directory holding its inputs.
    partner = (partner_aliases or {}).get(run_partner, run_partner)

    edir = paths.experiment_dir(root, experiment)
    versions = paths.list_versions(edir)
    parent_version = versions[-1] if versions else None
    parent = read_output_manifest(edir / parent_version) if parent_version else None

    pin = _input_pin(root, partner, input_version, confidence)

    if parent is not None and not allow_noop:
        same_run = (
            parent.version == (first.version or "unknown")
            and parent.run_timestamp == (first.run_timestamp or "unknown")
            and parent.results == results
        )
        if same_run and parent.provenance.input.version == pin.version:
            return None

    version = paths.next_version(edir)
    version_dir = edir / version

    result_files: list[ResultFileEntry] = []
    for key in sorted(results):
        size, etag, modified = (sizes or {}).get(key, (None, None, None))
        result_files.append(
            ResultFileEntry(
                result_key=key,
                s3_uri=results[key],
                bytes=size,
                sha256=None,
                sha256_source="none",
                etag=etag,
                last_modified=modified,
            )
        )

    run_prefix = None
    if first.prefix and first.experiment and first.version and first.run_timestamp:
        run_prefix = (
            f"s3://{first.bucket}/{first.prefix}/{first.experiment}/"
            f"{first.version}/{first.run_timestamp}"
        )

    manifest = OutputVersionManifest(
        experiment=experiment,
        version=first.version or "unknown",
        run_timestamp=first.run_timestamp or "unknown",
        results=dict(sorted(results.items())),
        output_version=version,
        parent_version=parent_version,
        created_at=paths.utcnow(),
        created_by=author or Author(),
        summary=summary,
        partner=partner,
        weather=weather,
        scenario_kind=(scenario_kinds or {}).get((run_partner, scenario or "")),
        scenario_value=scenario,
        provenance=Provenance(
            input=pin,
            code=_capture_code_provenance(partners_repo),
            storage=StorageProvenance(
                bucket=first.bucket,
                bucket_prefix=first.prefix,
                run_prefix=run_prefix,
            ),
            run=RunProvenance(
                scythe_version=first.version,
                run_timestamp=first.run_timestamp,
            ),
        ),
        result_files=result_files,
        totals=Totals(
            file_count=len(result_files),
            bytes=sum(entry.size_bytes or 0 for entry in result_files),
        ),
    )

    yamlio.write(version_dir / paths.OUTPUT_MANIFEST_NAME, manifest.dump())
    (version_dir / "README.md").write_text(
        _output_version_readme(manifest), encoding="utf-8"
    )
    _publish_output(root, experiment, manifest, version_dir)
    return manifest


def _output_version_readme(manifest: OutputVersionManifest) -> str:
    """Render the README inside an output version directory."""
    m = manifest
    lines = [
        f"# {m.experiment} — results {m.output_version}",
        "",
        m.summary.strip() or "Recorded simulation results.",
        "",
        f"- **Simulation run:** `{m.version}` at `{m.run_timestamp}`",
        f"- **Built from inputs:** "
        f"[`{m.provenance.input.version or 'unknown'}`]"
        f"(../../../../../inputs/partners/{m.partner}/{m.provenance.input.version or ''}/)"
        f" ({m.provenance.input.confidence})",
        f"- **Recorded:** {m.created_at}",
        "",
        "The result files live in S3, not in this repository. Download them with:",
        "",
        "```",
        f"globi-data outputs download {m.experiment} --dest ./results",
        "```",
        "",
        "## Result files",
        "",
    ]
    rows = [
        [f"`{entry.result_key}`", render._bytes(entry.size_bytes), f"`{entry.s3_uri}`"]
        for entry in m.result_files
    ]
    lines.append(render._table(["Result", "Size", "Location"], rows))

    if m.provenance.input.confidence == "inferred":
        lines += [
            "> ⚠️ The input version above was inferred when these results were backfilled,",
            "> not recorded at the time the simulation ran. Treat it as an assumption.",
            "",
        ]
    return "\n".join(lines)


def _publish_output(
    root: Path, experiment: str, manifest: OutputVersionManifest, version_dir: Path
) -> None:
    """Update pointers and ledgers after an output version is written."""
    edir = paths.experiment_dir(root, experiment)

    ledger = paths.read_versions(edir)
    ledger.experiment = experiment
    for entry in ledger.versions:
        if entry.status == "active":
            entry.status = "superseded"
    ledger.versions.append(
        VersionEntry(
            version=manifest.output_version,
            status="active",
            created_at=manifest.created_at,
            summary=manifest.summary,
        )
    )
    ledger.versions.sort(key=lambda entry: paths.version_number(entry.version))
    paths.write_versions(edir, ledger)

    paths.write_current(
        edir,
        CurrentPointer(
            experiment=experiment,
            current=manifest.output_version,
            manifest=f"{manifest.output_version}/{paths.OUTPUT_MANIFEST_NAME}",
            manifest_sha256=file_sha256(version_dir / paths.OUTPUT_MANIFEST_NAME),
            updated_at=manifest.created_at,
        ),
    )

    published = paths.read_published(root)
    rel = str(version_dir.relative_to(root))
    if rel not in published.paths():
        published.entries.append(
            PublishedEntry(path=rel, published_at=manifest.created_at)
        )
        published.entries.sort(key=lambda entry: entry.path)
        paths.write_published(root, published)


def load_latest_results_csv(path: Path) -> dict[str, dict[str, str]]:
    """Read ``latest-results.csv`` into ``{experiment: {result_key: s3_uri}}``."""
    if not path.exists():
        raise GlobiDataError(f"{path} does not exist.")
    grouped: dict[str, dict[str, str]] = {}
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            experiment = (row.get("experiment") or "").strip()
            key = (row.get("result_key") or "").strip()
            uri = (row.get("s3_uri") or "").strip()
            if experiment and key and uri:
                grouped.setdefault(experiment, {})[key] = uri
    return grouped


def _s3_client():
    """Return a boto3 S3 client, with a clear message if boto3 is missing."""
    try:
        import boto3
    except ImportError as exc:  # pragma: no cover - depends on install extras
        raise GlobiDataError(
            "This command needs the S3 extra. Install it with: uv sync --extra s3"
        ) from exc
    return boto3.client("s3")


def head_objects(
    uris: dict[str, str],
) -> dict[str, tuple[int | None, str | None, str | None]]:
    """HEAD each result object, returning ``{key: (bytes, etag, last_modified)}``.

    Cheap compared with hashing: one metadata request per object instead of
    streaming gigabytes.
    """
    client = _s3_client()
    out: dict[str, tuple[int | None, str | None, str | None]] = {}
    for key, uri in uris.items():
        ref = parse_s3_uri(uri)
        try:
            head = client.head_object(Bucket=ref.bucket, Key=ref.key)
        except Exception:
            out[key] = (None, None, None)
            continue
        modified = head.get("LastModified")
        out[key] = (
            head.get("ContentLength"),
            (head.get("ETag") or "").strip('"') or None,
            modified.isoformat() if modified else None,
        )
    return out


def download_results(
    manifest: OutputVersionManifest, dest: Path, *, keys: tuple[str, ...] = ()
) -> list[Path]:
    """Download an experiment's result parquets to ``dest``.

    Mirrors the layout ``scripts/download_latest_results.py`` uses in
    globi-partners-data: ``<dest>/<experiment>/<result_key>.pq``.
    """
    client = _s3_client()
    out_dir = dest / manifest.experiment
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for entry in manifest.result_files:
        if keys and entry.result_key not in keys:
            continue
        ref = parse_s3_uri(entry.s3_uri)
        target = out_dir / f"{entry.result_key}{Path(ref.key).suffix or '.pq'}"
        client.download_file(ref.bucket, ref.key, str(target))
        written.append(target)
    return written
