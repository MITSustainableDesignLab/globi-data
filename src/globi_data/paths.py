"""Repo layout constants and version resolution.

The one rule that shapes this module: **version directories are frozen, and all
mutable state lives one level up**. `CURRENT.yml` and `versions.yml` sit beside
the `vNNN/` directories, never inside them, so "has a published version been
edited" is a mechanical question about a diff rather than a judgement call.
"""

from __future__ import annotations

import os
import re
from datetime import UTC, datetime
from pathlib import Path

from . import yamlio
from .models import (
    CurrentPointer,
    PublishedEntry,
    PublishedLedger,
    VersionEntry,
    VersionsLedger,
)

INPUTS_DIR = "inputs/partners"
OUTPUT_RUNS_DIR = "outputs/runs"
OUTPUT_BATCHES_DIR = "outputs/batches"
OUTPUT_SURROGATES_DIR = "outputs/surrogates"
PUBLISHED_FILE = "published.yml"

INPUT_MANIFEST_NAME = "input-version.yml"
OUTPUT_MANIFEST_NAME = "output-version.yml"
SURROGATE_MANIFEST_NAME = "surrogate-version.yml"
CURRENT_NAME = "CURRENT.yml"
VERSIONS_NAME = "versions.yml"

VERSION_RE = re.compile(r"^v(\d{3,})$")

# Guardrails that keep the repo browsable and clonable. The whole design rests
# on inputs staying small; a stray geojson or result parquet would break it.
WARN_BYTES = 25 * 1024 * 1024
FAIL_BYTES = 90 * 1024 * 1024


class GlobiDataError(RuntimeError):
    """A user-facing error with an actionable message."""


def utcnow() -> str:
    """Return the current UTC time as an ISO-8601 string with a Z suffix."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def repo_root(start: Path | None = None) -> Path:
    """Locate the globi-data repo root.

    Resolution order: ``GLOBI_DATA_ROOT`` env var, then the nearest ancestor of
    ``start`` containing a ``published.yml``, then the nearest ancestor
    containing a ``.git``.
    """
    env = os.environ.get("GLOBI_DATA_ROOT")
    if env:
        candidate = Path(env).expanduser().resolve()
        if candidate.is_dir():
            return candidate
        raise GlobiDataError(
            f"GLOBI_DATA_ROOT points at {candidate}, which does not exist."
        )

    here = (start or Path.cwd()).resolve()
    for parent in [here, *here.parents]:
        if (parent / PUBLISHED_FILE).exists():
            return parent
    for parent in [here, *here.parents]:
        if (parent / ".git").exists():
            return parent
    raise GlobiDataError(
        "Could not locate the globi-data repo. Run from inside it, or set GLOBI_DATA_ROOT."
    )


def version_number(version: str) -> int:
    """Parse ``v003`` into ``3``."""
    match = VERSION_RE.match(version)
    if not match:
        raise GlobiDataError(
            f"{version!r} is not a valid version label (expected vNNN)."
        )
    return int(match.group(1))


def format_version(number: int) -> str:
    """Format ``3`` as ``v003``."""
    return f"v{number:03d}"


# --------------------------------------------------------------------------- #
# Inputs
# --------------------------------------------------------------------------- #


def partner_dir(root: Path, partner: str) -> Path:
    """Return the directory holding all versions of one partner's inputs."""
    return root / INPUTS_DIR / partner


def input_version_dir(root: Path, partner: str, version: str) -> Path:
    """Return one frozen input version directory."""
    return partner_dir(root, partner) / version


def list_partners(root: Path) -> list[str]:
    """Return every partner that has at least one version directory."""
    base = root / INPUTS_DIR
    if not base.is_dir():
        return []
    return sorted(p.name for p in base.iterdir() if p.is_dir() and list_versions(p))


def list_versions(directory: Path) -> list[str]:
    """Return the sorted ``vNNN`` directory names beneath ``directory``."""
    if not directory.is_dir():
        return []
    versions = [
        p.name for p in directory.iterdir() if p.is_dir() and VERSION_RE.match(p.name)
    ]
    return sorted(versions, key=version_number)


def next_version(directory: Path) -> str:
    """Return the next unused version label in ``directory``."""
    versions = list_versions(directory)
    if not versions:
        return format_version(1)
    return format_version(version_number(versions[-1]) + 1)


# --------------------------------------------------------------------------- #
# Pointers and ledgers
# --------------------------------------------------------------------------- #


def read_current(directory: Path) -> CurrentPointer | None:
    """Read ``CURRENT.yml`` from a partner or run directory."""
    path = directory / CURRENT_NAME
    if not path.exists():
        return None
    return CurrentPointer.model_validate(yamlio.read(path))


def write_current(directory: Path, pointer: CurrentPointer) -> None:
    """Write ``CURRENT.yml``."""
    yamlio.write(
        directory / CURRENT_NAME,
        pointer.dump(),
        header=(
            "Which version is current. Generated - edit by creating a new version\n"
            "with `globi-data inputs new`, not by hand."
        ),
    )


def read_versions(directory: Path) -> VersionsLedger:
    """Read ``versions.yml``, returning an empty ledger if absent."""
    path = directory / VERSIONS_NAME
    if not path.exists():
        return VersionsLedger()
    return VersionsLedger.model_validate(yamlio.read(path))


def write_versions(directory: Path, ledger: VersionsLedger) -> None:
    """Write ``versions.yml``."""
    yamlio.write(
        directory / VERSIONS_NAME,
        ledger.dump(),
        header=(
            "Mutable status of every version. This file lives OUTSIDE the frozen\n"
            "version directories so a version can be retracted without editing it."
        ),
    )


def read_published(root: Path) -> PublishedLedger:
    """Read the append-only immutability ledger."""
    path = root / PUBLISHED_FILE
    if not path.exists():
        return PublishedLedger()
    data = yamlio.read(path)
    if not data:
        return PublishedLedger()
    return PublishedLedger.model_validate(data)


def write_published(root: Path, ledger: PublishedLedger) -> None:
    """Write the immutability ledger."""
    yamlio.write(
        root / PUBLISHED_FILE,
        ledger.dump(),
        header=(
            "Append-only ledger of frozen version directories.\n"
            "Anything listed here must never be modified in place - publish a new\n"
            "version instead. Enforced by .githooks/pre-commit and CI."
        ),
    )


def publish_version(
    root: Path, directory: Path, entry: VersionEntry, pointer: CurrentPointer
) -> None:
    """Make ``entry`` the single active version, point CURRENT at it, freeze it.

    Shared by output and surrogate versions. Any earlier entry for the same
    version (a draft) is replaced; whatever was active becomes superseded.
    """
    ledger = read_versions(directory)
    ledger.partner = pointer.partner or ledger.partner
    ledger.experiment = pointer.experiment or ledger.experiment
    ledger.versions = [v for v in ledger.versions if v.version != entry.version]
    for other in ledger.versions:
        if other.status == "active":
            other.status = "superseded"
    ledger.versions.append(entry)
    ledger.versions.sort(key=lambda e: version_number(e.version))
    write_versions(directory, ledger)

    write_current(directory, pointer)

    published = read_published(root)
    rel = str((directory / entry.version).relative_to(root))
    if rel not in published.paths():
        published.entries.append(
            PublishedEntry(path=rel, published_at=entry.created_at)
        )
        published.entries.sort(key=lambda e: e.path)
        write_published(root, published)


def resolve_version(directory: Path, requested: str = "current") -> str:
    """Resolve a version request against a partner or run directory.

    Order: an explicit ``vNNN`` label, then ``CURRENT.yml``, then the highest
    version present (with the caller expected to warn), then an error listing
    what is available.
    """
    available = list_versions(directory)
    if not available:
        raise GlobiDataError(f"No versions exist under {directory}.")

    if requested and requested != "current":
        if requested not in available:
            raise GlobiDataError(
                f"Version {requested} not found under {directory}. "
                f"Available: {', '.join(available)}"
            )
        return requested

    pointer = read_current(directory)
    if pointer:
        if pointer.current not in available:
            raise GlobiDataError(
                f"{directory / CURRENT_NAME} points at {pointer.current}, "
                f"which does not exist. Available: {', '.join(available)}"
            )
        return pointer.current

    return available[-1]


# --------------------------------------------------------------------------- #
# Outputs
# --------------------------------------------------------------------------- #


def experiment_dir(root: Path, experiment: str) -> Path:
    """Return the directory holding all versions of one experiment's outputs.

    ``experiment`` is the scythe run name, e.g. ``Ahmedabad/tmy/BAU``; the
    directory layout mirrors it exactly.
    """
    return root / OUTPUT_RUNS_DIR / experiment


def batch_dir(root: Path, batch: str) -> Path:
    """Return the directory holding all versions of one batch's outputs."""
    return root / OUTPUT_BATCHES_DIR / batch


def list_experiments(root: Path) -> list[str]:
    """Return every experiment that has at least one output version."""
    base = root / OUTPUT_RUNS_DIR
    if not base.is_dir():
        return []
    found: list[str] = []
    for path in base.rglob(CURRENT_NAME):
        found.append(str(path.parent.relative_to(base)))
    return sorted(found)


def list_batches(root: Path) -> list[str]:
    """Return every batch that has at least one output version."""
    base = root / OUTPUT_BATCHES_DIR
    if not base.is_dir():
        return []
    return sorted(p.name for p in base.iterdir() if p.is_dir() and list_versions(p))


def surrogate_dir(root: Path, partner: str) -> Path:
    """Return the directory holding all versions of one partner's surrogate."""
    return root / OUTPUT_SURROGATES_DIR / partner


def list_surrogates(root: Path) -> list[str]:
    """Return every partner that has at least one surrogate version."""
    base = root / OUTPUT_SURROGATES_DIR
    if not base.is_dir():
        return []
    return sorted(p.name for p in base.iterdir() if p.is_dir() and list_versions(p))
