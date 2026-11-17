"""Public processed-result layout (bucket, prefix, product keys)."""

from __future__ import annotations

from pathlib import Path

from . import yamlio
from .paths import GlobiDataError, repo_root

PUBLIC_STORAGE_FILE = "public_storage.yml"
RAW_BUCKET_PREFIX = "globi-partners"


def read_public_storage(root: Path | None = None) -> dict:
    """Load ``public_storage.yml`` from the repo root."""
    root = root or repo_root()
    path = root / PUBLIC_STORAGE_FILE
    data = yamlio.read(path) if path.exists() else {}
    if not data:
        return {
            "bucket": "ml-for-bem",
            "inputs_prefix": "globi-inputs",
            "outputs_prefix": "globi-public",
            "products": [
                {
                    "result_key": "energy_and_peak",
                    "filename": "energy_and_peak.parquet",
                },
                {
                    "result_key": "overheating",
                    "filename": "overheating.parquet",
                },
                {
                    "result_key": "emissions_by_building",
                    "filename": "emissions_by_building.parquet",
                },
            ],
        }
    return data


def outputs_prefix(cfg: dict) -> str:
    """S3 prefix for processed result objects (``globi-public``)."""
    return cfg.get("outputs_prefix") or cfg.get("bucket_prefix") or "globi-public"


def inputs_prefix(cfg: dict) -> str:
    """S3 prefix for published input bundles (``globi-inputs``)."""
    return cfg.get("inputs_prefix") or "globi-inputs"


def public_input_uri(
    root: Path, iso: str, partner: str, input_version: str, rel_path: str
) -> str:
    """Build the canonical public S3 URI for one file under an input bundle."""
    cfg = read_public_storage(root)
    bucket = cfg.get("bucket") or "ml-for-bem"
    prefix = inputs_prefix(cfg)
    rel = rel_path.lstrip("/")
    return f"s3://{bucket}/{prefix}/{iso}/{partner}/{input_version}/{rel}"


def public_uri(
    root: Path, experiment: str, output_version: str, result_key: str
) -> str:
    """Build the canonical public S3 URI for one result key."""
    cfg = read_public_storage(root)
    products = {p["result_key"]: p["filename"] for p in cfg.get("products") or []}
    filename = products.get(result_key)
    if not filename:
        raise GlobiDataError(f"unknown public result key {result_key!r}")
    bucket = cfg.get("bucket") or "ml-for-bem"
    prefix = outputs_prefix(cfg)
    return f"s3://{bucket}/{prefix}/{experiment}/{output_version}/{filename}"


def public_result_keys(root: Path | None = None) -> tuple[str, ...]:
    """Return the result keys exposed for download."""
    cfg = read_public_storage(root or repo_root())
    return tuple(p["result_key"] for p in cfg.get("products") or [])


def is_raw_scythe_uri(uri: str) -> bool:
    """True if the URI points at private scythe ``final/*.pq`` objects."""
    return "/globi-partners/" in uri and "/final/" in uri
