"""Recording, fetching and validating surrogate models.

A surrogate is a regressor trained on sampled GloBI simulations: semantic
fields, weather and geometry go in; EUI and end-use energy come out. The model
files stay in S3, pinned by sha256. What is versioned here is the manifest and
the transforms file (globi's ``transforms.yml`` or epengine's ``space.yml``) —
the exact feature list, category values, scalers and target names — because
that contract is what a user needs to call the model, and because it can be
checked against the input bundle it claims to match.

The check that matters most: every category the model was trained on must be
an allowed option in the pinned ``semantic-fields`` file. If the two drift,
globi's index encoder turns the unknown value into ``-1`` and the model still
returns a number.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse

from . import inputs as inputs_mod
from . import outputs as outputs_mod
from . import paths, yamlio
from .hashing import file_sha256
from .models import (
    Author,
    CurrentPointer,
    FeatureSource,
    InputVersionManifest,
    StorageProvenance,
    SurrogateFeature,
    SurrogateModelFile,
    SurrogateModelPart,
    SurrogateProvenance,
    SurrogateTarget,
    SurrogateVersionManifest,
    TrainingProvenance,
    TransformsRef,
    VersionEntry,
)
from .paths import GlobiDataError


@dataclass
class Finding:
    """One problem with a surrogate version. ``level`` is error or warning."""

    level: str
    message: str


def read_surrogate_manifest(version_dir: Path) -> SurrogateVersionManifest:
    """Load the ``surrogate-version.yml`` inside a surrogate version directory."""
    path = version_dir / paths.SURROGATE_MANIFEST_NAME
    if not path.is_file():
        raise GlobiDataError(f"{path} is missing")
    return SurrogateVersionManifest.model_validate(yamlio.read(path))


def _semantic_options(
    root: Path, manifest: InputVersionManifest
) -> dict[str, list[Any]] | None:
    """Return ``{field: options}`` from the pinned bundle's semantic fields file."""
    rel = manifest.role_path("semantic_fields_file")
    if not rel:
        return None
    path = paths.input_version_dir(root, manifest.partner, manifest.version) / rel
    if not path.is_file():
        return None
    data = yamlio.read(path) or {}
    return {
        f["Name"].strip(): list(f.get("Options") or [])
        for f in data.get("Fields") or []
        if "Name" in f
    }


def _check_uri(uri: str | None, what: str, out: list[Finding]) -> None:
    if uri is not None and urlparse(uri).scheme != "s3":
        out.append(Finding("error", f"{what} is not an s3:// URI: {uri}"))


def _contract(
    s: SurrogateVersionManifest, transforms: dict[str, Any]
) -> tuple[list[str], set[str], dict[str, list[Any]], list[str]]:
    """Return ``(features, continuous, cat_map, targets)`` for either transforms format.

    epengine's ``space.yml`` describes inputs only; its targets are the model
    files, one per target.
    """
    if s.transforms.format == "epengine-space":
        feats = transforms.get("features") or []
        return (
            [f["name"] for f in feats],
            {f["name"] for f in feats if "values" not in f},
            {f["name"]: list(f["values"]) for f in feats if "values" in f},
            [p.target for p in s.model.files],
        )
    x = transforms.get("x") or {}
    y = transforms.get("y") or {}
    return (
        list(x.get("features") or []),
        set(x.get("continuous_features") or []),
        x.get("cat_map") or {},
        list(y.get("targets") or []),
    )


def _check_contract(
    s: SurrogateVersionManifest, transforms: dict[str, Any], out: list[Finding]
) -> None:
    """The manifest's feature/target annotations must describe the transforms exactly."""
    t_features, continuous, cat_map, t_targets = _contract(s, transforms)

    declared = [f.name for f in s.features]
    if sorted(declared) != sorted(t_features):
        missing = sorted(set(t_features) - set(declared))
        extra = sorted(set(declared) - set(t_features))
        out.append(
            Finding(
                "error",
                f"features disagree with {s.transforms.path} "
                f"(not annotated: {missing or 'none'}; not in model: {extra or 'none'})",
            )
        )
    no_default: list[str] = []
    for f in s.features:
        if f.name not in t_features:
            continue
        in_cat = f.name in cat_map
        if f.kind == "categorical" and not in_cat:
            out.append(
                Finding("error", f"{f.name}: declared categorical, has no cat_map")
            )
        if f.kind == "continuous" and f.name not in continuous:
            out.append(
                Finding(
                    "error", f"{f.name}: declared continuous, not scaled as continuous"
                )
            )
        if f.source == "semantic" and not f.semantic_field:
            out.append(
                Finding("error", f"{f.name}: semantic feature names no semantic_field")
            )
        if f.source != "semantic" and f.default is None:
            no_default.append(f.name)
    if no_default:
        out.append(
            Finding(
                "warning",
                f"{len(no_default)} non-semantic feature(s) have no default "
                f"(e.g. {no_default[0]}), so the model cannot be driven from "
                "semantic fields alone",
            )
        )

    names = [t.name for t in s.targets]
    if sorted(names) != sorted(t_targets):
        out.append(Finding("error", f"targets disagree with {s.transforms.path}"))
    for key in s.metrics.per_target:
        if key not in names:
            out.append(Finding("error", f"metrics given for unknown target {key!r}"))

    weather = [f for f in s.features if f.source == "weather"]
    if weather and s.weather_options:
        values = sorted(str(w.value) for w in s.weather_options)
        trained = sorted(str(v) for v in cat_map.get(weather[0].name, []))
        if values != trained:
            out.append(
                Finding(
                    "error",
                    "weather_options disagree with the weather feature's cat_map",
                )
            )


def _check_against_inputs(
    root: Path,
    s: SurrogateVersionManifest,
    transforms: dict[str, Any],
    out: list[Finding],
) -> None:
    """Categories and weather files must exist in the pinned input bundle."""
    pin = s.provenance.input
    if pin.partner != s.partner:
        out.append(
            Finding("error", f"pins inputs of {pin.partner!r}, not {s.partner!r}")
        )
    if not pin.version:
        out.append(Finding("warning", "does not pin an input version"))
        return
    vdir = paths.input_version_dir(root, pin.partner, pin.version)
    if not vdir.is_dir():
        out.append(
            Finding("error", f"pinned input {pin.partner}/{pin.version} does not exist")
        )
        return
    if pin.manifest_sha256 and inputs_mod.manifest_sha(vdir) != pin.manifest_sha256:
        out.append(
            Finding(
                "error", f"pinned input {pin.partner}/{pin.version} has been modified"
            )
        )
    manifest = inputs_mod.read_manifest(vdir)

    options = _semantic_options(root, manifest)
    cat_map = _contract(s, transforms)[2]
    for f in s.features:
        if f.source != "semantic" or not f.semantic_field:
            continue
        if options is None:
            out.append(
                Finding("warning", "pinned input has no readable semantic fields file")
            )
            break
        if f.semantic_field not in options:
            out.append(
                Finding(
                    "error", f"{f.name}: {f.semantic_field!r} is not a semantic field"
                )
            )
            continue
        allowed = options[f.semantic_field]
        trained = cat_map.get(f.name, [])
        unknown = [v for v in trained if v not in allowed]
        if unknown:
            out.append(
                Finding(
                    "error", f"{f.name}: trained on values not in Options: {unknown}"
                )
            )
        unseen = [v for v in allowed if v not in trained]
        if unseen and f.name in cat_map:
            out.append(
                Finding(
                    "warning",
                    f"{f.name}: Options the model never saw (encoded as -1): {unseen}",
                )
            )

    stored = {e.path for e in manifest.files}
    for w in s.weather_options:
        if w.input_file not in stored:
            out.append(
                Finding(
                    "error",
                    f"weather option {w.label!r}: {w.input_file} is not in "
                    f"{pin.partner}/{pin.version}",
                )
            )


def validate_surrogate(root: Path, partner: str, version: str) -> list[Finding]:
    """Check one surrogate version against its transforms and its pinned inputs."""
    vdir = paths.surrogate_dir(root, partner) / version
    out: list[Finding] = []
    try:
        s = read_surrogate_manifest(vdir)
    except Exception as exc:
        return [Finding("error", str(exc))]

    if s.partner != partner or s.surrogate_version != version:
        out.append(
            Finding(
                "error",
                f"manifest says {s.partner}/{s.surrogate_version} but lives under "
                f"{partner}/{version}",
            )
        )
    if s.example:
        out.append(
            Finding(
                "warning", "illustrative example; URIs and metrics are placeholders"
            )
        )
        if s.status == "active":
            out.append(Finding("error", "an example cannot be active"))
    else:
        for part in model_parts(s):
            if part.sha256 is None:
                out.append(
                    Finding("warning", f"model file {part.target} has no sha256")
                )

    for part in model_parts(s):
        _check_uri(part.s3_uri, f"model file {part.target}", out)
    _check_uri(s.transforms.s3_uri, "transforms.s3_uri", out)

    tpath = vdir / s.transforms.path
    if not tpath.is_file():
        out.append(Finding("error", f"{s.transforms.path} is missing"))
        return out
    if file_sha256(tpath) != s.transforms.sha256:
        out.append(Finding("error", f"{s.transforms.path} does not match its sha256"))
    transforms = yamlio.read(tpath) or {}

    _check_contract(s, transforms, out)
    _check_against_inputs(root, s, transforms, out)
    return out


# --------------------------------------------------------------------------- #
# Fetching and recording
# --------------------------------------------------------------------------- #

DEFAULT_CACHE = Path("~/.cache/globi-data/surrogates")
# Placeholder unit written by `record`; `promote` refuses until it is replaced.
UNCONFIRMED = "unconfirmed"
_SOURCES: dict[str, FeatureSource] = {
    "semantic": "semantic",
    "weather": "weather",
    "geometry": "geometry",
    "extra_spaces": "extra_space",
}


def model_parts(s: SurrogateVersionManifest) -> list[SurrogateModelPart]:
    """Return the model's files, treating a single-file model as one part."""
    if s.model.files:
        return s.model.files
    return [
        SurrogateModelPart(
            target="model",
            s3_uri=s.model.s3_uri or "",
            bytes=s.model.size_bytes,
            sha256=s.model.sha256,
        )
    ]


def _local_name(part: SurrogateModelPart) -> str:
    return PurePosixPath(outputs_mod.parse_s3_uri(part.s3_uri).key).name


def _download_parts(parts: list[SurrogateModelPart], out: Path) -> None:
    """Download each part into ``out``, skipping files whose sha256 already matches.

    A file that no longer matches its recorded hash after download means the S3
    object was replaced; that is an error, never a silent model swap.
    """
    out.mkdir(parents=True, exist_ok=True)
    client = None
    for part in parts:
        target = out / _local_name(part)
        if target.is_file() and (
            part.sha256 is None or file_sha256(target) == part.sha256
        ):
            continue
        client = client or outputs_mod._s3_client()
        ref = outputs_mod.parse_s3_uri(part.s3_uri)
        tmp = target.with_name(target.name + ".part")
        client.download_file(ref.bucket, ref.key, str(tmp))
        if part.sha256 and file_sha256(tmp) != part.sha256:
            tmp.unlink()
            raise GlobiDataError(
                f"{part.s3_uri} no longer matches its recorded sha256: the S3 "
                "object was replaced. Record a new surrogate version for it."
            )
        tmp.replace(target)


def fetch_surrogate(
    root: Path, partner: str, version: str = "current", dest: Path | None = None
) -> Path:
    """Download a surrogate's model files and transforms; return the local directory.

    Files land in ``<dest>/<partner>/<version>/`` (default
    ``~/.cache/globi-data/surrogates``). A second call only re-hashes.
    """
    sdir = paths.surrogate_dir(root, partner)
    version = paths.resolve_version(sdir, version)
    s = read_surrogate_manifest(sdir / version)
    out = (dest or DEFAULT_CACHE).expanduser() / partner / version
    _download_parts(model_parts(s), out)
    shutil.copy2(sdir / version / s.transforms.path, out / s.transforms.path)
    return out


def _feature_from_space(spec: dict[str, Any]) -> SurrogateFeature:
    """Annotate one ``space.yml`` feature from its ``feature.<source>.<name>`` path."""
    name = spec["name"]
    parts = name.split(".", 2)
    source = _SOURCES.get(parts[1]) if len(parts) == 3 else None
    if parts[0] != "feature" or source is None:
        raise GlobiDataError(f"Cannot tell where feature {name!r} comes from.")
    return SurrogateFeature(
        name=name,
        source=source,
        kind="categorical" if "values" in spec else "continuous",
        semantic_field=parts[2] if source == "semantic" else None,
    )


def record_surrogate(
    root: Path,
    partner: str,
    prefix: str,
    *,
    summary: str,
    author: Author | None = None,
    dest: Path | None = None,
) -> SurrogateVersionManifest:
    """Record an epengine LightGBM surrogate (``*.lgb`` + ``space.yml``) as a draft.

    Copies ``space.yml`` in, downloads every model file once to hash it (that
    download doubles as the first fetch), and annotates features from their
    names. Target units are written as ``unconfirmed``: set them, then
    ``promote``.
    """
    ref = outputs_mod.parse_s3_uri(prefix.rstrip("/") + "/")
    client = outputs_mod._s3_client()
    pages = client.get_paginator("list_objects_v2").paginate(
        Bucket=ref.bucket, Prefix=ref.key
    )
    keys = [o["Key"] for page in pages for o in page.get("Contents", [])]
    lgb_keys = sorted(k for k in keys if k.endswith(".lgb"))
    space_key = next((k for k in keys if PurePosixPath(k).name == "space.yml"), None)
    if not lgb_keys or space_key is None:
        raise GlobiDataError(
            f"{prefix} needs *.lgb files and a space.yml; is it an epengine models/ prefix?"
        )

    sdir = paths.surrogate_dir(root, partner)
    previous = paths.list_versions(sdir)
    version = paths.next_version(sdir)
    vdir = sdir / version
    vdir.mkdir(parents=True)
    client.download_file(ref.bucket, space_key, str(vdir / "space.yml"))

    parts = [
        SurrogateModelPart(
            target=PurePosixPath(k).stem, s3_uri=f"s3://{ref.bucket}/{k}"
        )
        for k in lgb_keys
    ]
    cache = (dest or DEFAULT_CACHE).expanduser() / partner / version
    shutil.rmtree(cache, ignore_errors=True)  # never hash a stale earlier attempt
    _download_parts(parts, cache)
    for part in parts:
        local = cache / _local_name(part)
        part.size_bytes = local.stat().st_size
        part.sha256 = file_sha256(local)

    space = yamlio.read(vdir / "space.yml") or {}
    run_prefix = f"s3://{ref.bucket}/{ref.key}".rstrip("/")
    bucket_prefix, _, experiment_id = ref.key.rstrip("/").partition("/")
    manifest = SurrogateVersionManifest(
        partner=partner,
        surrogate_version=version,
        parent_version=previous[-1] if previous else None,
        status="draft",
        created_at=paths.utcnow(),
        created_by=author or Author(),
        summary=summary,
        model=SurrogateModelFile(backend="lgb", format="lightgbm-text", files=parts),
        transforms=TransformsRef(
            path="space.yml",
            format="epengine-space",
            sha256=file_sha256(vdir / "space.yml"),
            s3_uri=f"s3://{ref.bucket}/{space_key}",
        ),
        features=[_feature_from_space(f) for f in space.get("features") or []],
        targets=[SurrogateTarget(name=p.target, unit=UNCONFIRMED) for p in parts],
        provenance=SurrogateProvenance(
            input=outputs_mod._input_pin(root, partner, None, "inferred"),
            storage=StorageProvenance(
                bucket=ref.bucket, bucket_prefix=bucket_prefix, run_prefix=run_prefix
            ),
            training=TrainingProvenance(experiment_id=experiment_id),
        ),
    )
    _write_manifest(vdir, manifest)

    ledger = paths.read_versions(sdir)
    ledger.partner = partner
    ledger.versions.append(
        VersionEntry(
            version=version,
            status="draft",
            created_at=manifest.created_at,
            impact="simulation-affecting",
            summary=summary,
        )
    )
    paths.write_versions(sdir, ledger)
    return manifest


def _write_manifest(vdir: Path, manifest: SurrogateVersionManifest) -> None:
    yamlio.write(
        vdir / paths.SURROGATE_MANIFEST_NAME,
        manifest.dump(),
        header="Schema: docs/SCHEMA.md#surrogate-versionyml",
    )


def promote_surrogate(
    root: Path, partner: str, version: str
) -> SurrogateVersionManifest:
    """Publish a draft surrogate: make it current and freeze it."""
    sdir = paths.surrogate_dir(root, partner)
    entry = paths.read_versions(sdir).get(version)
    if entry is None:
        raise GlobiDataError(f"{partner} {version} has no entry in versions.yml.")
    if entry.status != "draft":
        raise GlobiDataError(
            f"{partner} {version} is {entry.status}, not a draft. Only drafts are promoted."
        )
    vdir = sdir / version
    s = read_surrogate_manifest(vdir)
    unconfirmed = [t.name for t in s.targets if t.unit == UNCONFIRMED]
    if unconfirmed:
        raise GlobiDataError(
            f"Set the unit of {', '.join(unconfirmed)} in "
            f"{vdir / paths.SURROGATE_MANIFEST_NAME} before promoting."
        )
    errors = [
        f.message
        for f in validate_surrogate(root, partner, version)
        if f.level == "error"
    ]
    if errors:
        raise GlobiDataError(f"{partner} {version} has errors: " + "; ".join(errors))

    s.status = "active"
    _write_manifest(vdir, s)
    paths.publish_version(
        root,
        sdir,
        VersionEntry(
            version=version,
            status="active",
            created_at=s.created_at,
            impact=entry.impact,
            summary=s.summary,
        ),
        CurrentPointer(
            partner=partner,
            current=version,
            manifest=f"{version}/{paths.SURROGATE_MANIFEST_NAME}",
            manifest_sha256=file_sha256(vdir / paths.SURROGATE_MANIFEST_NAME),
            updated_at=paths.utcnow(),
        ),
    )
    return s
