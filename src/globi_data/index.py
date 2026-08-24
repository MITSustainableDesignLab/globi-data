"""Regenerating the browsable index pages.

Everything here is derived from the manifests, so it can always be rebuilt.
``--check`` mode compares what *would* be written against what is on disk and
reports drift, which is how CI keeps generated pages honest without letting
them cause merge conflicts on every pull request.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import inputs as inputs_mod
from . import outputs as outputs_mod
from . import paths, render, status, yamlio

# Every generated page stamps when it was produced. That stamp changes on every
# run, so comparing raw text would report drift forever and CI would never pass.
# Both sides are compared with the stamp removed, and a file whose only
# difference is the stamp is left alone — which also stops the nightly rebuild
# from committing a no-op change every night.
_VOLATILE = re.compile(r"^(generated_at:.*|_Generated .*\._)$", re.MULTILINE)


@dataclass
class Change:
    """A file the index pass would rewrite."""

    path: Path
    reason: str


def _substantive(text: str) -> str:
    """Strip volatile timestamps so two renderings compare on content alone."""
    return _VOLATILE.sub("", text)


def _write_if_changed(
    path: Path, content: str, changes: list[Change], *, write: bool
) -> None:
    """Record (and optionally apply) a difference between disk and generated content."""
    existing = path.read_text(encoding="utf-8") if path.exists() else None
    if existing is not None and _substantive(existing) == _substantive(content):
        return
    changes.append(Change(path, "missing" if existing is None else "out of date"))
    if write:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def rebuild(
    root: Path, *, write: bool = True, partners_repo: Path | None = None
) -> list[Change]:
    """Regenerate every index, README and status page. Returns what changed."""
    changes: list[Change] = []
    generated_at = paths.utcnow()

    # --- inputs -------------------------------------------------------------
    input_rows: list[dict[str, Any]] = []
    index_entries: list[dict[str, Any]] = []
    for partner in paths.list_partners(root):
        pdir = paths.partner_dir(root, partner)
        versions = paths.list_versions(pdir)
        current = paths.resolve_version(pdir, "current")
        manifest = inputs_mod.read_manifest(pdir / current)
        ledger = paths.read_versions(pdir)

        _write_if_changed(
            pdir / "README.md",
            render.partner_readme(partner, ledger, manifest),
            changes,
            write=write,
        )

        input_rows.append({
            "partner": partner,
            "current": current,
            "versions": len(versions),
            "updated": manifest.created_at,
            "bytes": manifest.totals.size_bytes,
            "kind": manifest.globi.bundle_kind,
        })
        index_entries.append({
            "partner": partner,
            "current": current,
            "versions": [
                {
                    "version": entry.version,
                    "status": entry.status,
                    "impact": entry.impact,
                    "created_at": entry.created_at,
                }
                for entry in ledger.versions
            ],
            "bundle_sha256": manifest.bundle_sha256,
            "bundle_kind": manifest.globi.bundle_kind,
        })

    _write_if_changed(
        root / "inputs" / "README.md",
        render.inputs_index_readme(input_rows),
        changes,
        write=write,
    )
    _write_if_changed(
        root / "inputs" / "index.yml",
        yamlio.dumps({
            "schema_version": 1,
            "generated_at": generated_at,
            "partners": index_entries,
        }),
        changes,
        write=write,
    )

    # --- outputs ------------------------------------------------------------
    output_rows: list[dict[str, Any]] = []
    output_entries: list[dict[str, Any]] = []
    for experiment in paths.list_experiments(root):
        edir = paths.experiment_dir(root, experiment)
        current = paths.resolve_version(edir, "current")
        manifest = outputs_mod.read_output_manifest(edir / current)
        output_rows.append({
            "experiment": experiment,
            "current": current,
            "scythe_version": manifest.version,
            "run_timestamp": manifest.run_timestamp,
            "result_count": len(manifest.result_files),
            "input_version": manifest.provenance.input.version or "?",
        })
        output_entries.append({
            "experiment": experiment,
            "current": current,
            "scythe_version": manifest.version,
            "run_timestamp": manifest.run_timestamp,
            "input_version": manifest.provenance.input.version,
            "input_confidence": manifest.provenance.input.confidence,
        })

    if output_rows:
        _write_if_changed(
            root / "outputs" / "README.md",
            render.outputs_index_readme(output_rows),
            changes,
            write=write,
        )
        _write_if_changed(
            root / "outputs" / "index.yml",
            yamlio.dumps({
                "schema_version": 1,
                "generated_at": generated_at,
                "experiments": output_entries,
            }),
            changes,
            write=write,
        )

        rows = status.evaluate_all(root, partners_repo=partners_repo)
        _write_if_changed(
            root / "outputs" / "STATUS.md",
            render.status_markdown(rows, generated_at),
            changes,
            write=write,
        )

    return changes
