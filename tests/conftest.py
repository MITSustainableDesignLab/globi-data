"""Shared fixtures: a miniature globi-partners-data and an empty globi-data."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from globi_data import paths


def _git(repo: Path, *args: str) -> None:
    """Run a git command in ``repo``, failing loudly."""
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def _init_repo(path: Path) -> None:
    """Create a git repo with an identity, so provenance capture has something to read."""
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init", "-q", "-b", "main")
    _git(path, "config", "user.name", "Test User")
    _git(path, "config", "user.email", "test@example.com")


@pytest.fixture
def data_root(tmp_path: Path) -> Path:
    """An initialised, empty globi-data repo."""
    root = tmp_path / "globi-data"
    _init_repo(root)
    (root / paths.PUBLISHED_FILE).write_text("schema_version: 1\nentries: []\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "initial commit")
    return root


def _write_partner(base: Path, name: str, *, ext: str = "yaml") -> Path:
    """Write a minimal but realistic partner bundle.

    ``ext`` switches between the ``.yaml`` and ``.yml`` spellings that real
    partners disagree on, so tests can cover both.
    """
    partner = base / name
    (partner / "weather").mkdir(parents=True)
    (partner / "weather_ftmy").mkdir(parents=True)

    (partner / "artifacts.yml").write_text(
        f"""gis_file: data/partners/{name}/buildings.geojson
db_file: data/partners/{name}/components-lib.db
semantic_fields_file: data/partners/{name}/semantic-fields.{ext}
epwzip_file: "https://climate.onebuilding.org/x/{name}.zip"
component_map_file: data/partners/{name}/component-map.{ext}
"""
    )
    (partner / "manifest.yml").write_text(
        f"name: {name}\nscenario: Baseline\nfile_config: data/partners/{name}/artifacts.yml\n"
    )
    (partner / "gis-preprocessor.yml").write_text("cart_crs: EPSG:3857\n")
    (partner / f"semantic-fields.{ext}").write_text("Name: test\nFields: []\n")
    (partner / f"component-map.{ext}").write_text("Envelope: {}\n")
    (partner / "components-lib.db").write_bytes(b"SQLite format 3\x00" + b"\x01" * 512)
    (partner / "buildings.geojson").write_text(
        '{"type":"FeatureCollection","features":[]}'
    )
    (partner / "weather" / f"{name}_TMYx.epw").write_text("LOCATION,test\n")
    (partner / "weather" / f"{name}_TMYx.zip").write_bytes(b"PK\x03\x04zip")
    (partner / "weather_ftmy" / f"{name}_ftmy_2050.zip").write_bytes(b"PK\x03\x04ftmy")

    # Noise that curation must leave behind.
    (partner / "components-lib-old.db").write_bytes(b"stale backup")
    (partner / f"{name}_ftmy_2050.epw.txt").write_text("intermediate\n")
    return partner


@pytest.fixture
def partners_repo(tmp_path: Path) -> Path:
    """A miniature globi-partners-data with three partners and a registry."""
    repo = tmp_path / "globi-partners-data"
    base = repo / "data" / "partners"
    base.mkdir(parents=True)
    _init_repo(repo)

    _write_partner(base, "Lisbon", ext="yaml")
    _write_partner(base, "Sao_Paulo", ext="yml")

    # Trondheim: no plain manifest.yml, only scenario variants.
    trondheim = _write_partner(base, "Trondheim", ext="yaml")
    (trondheim / "manifest.yml").unlink()
    (trondheim / "manifest_LowEfficiency.yml").write_text(
        "name: Trondheim\nscenario: LowEfficiency\n"
    )
    (trondheim / "manifest_HighEfficiency.yml").write_text(
        "name: Trondheim\nscenario: HighEfficiency\n"
    )

    (repo / "data" / "experiments.yaml").write_text(
        """data_root: data/partners
partners:
  Lisbon:
    scenarios: {baseline: Baseline, alternative: Retrofit}
  Sao_Paulo:
    name: Sao_Paulo_Bela_Vista
    scenarios: {baseline: noAC, alternative: withAC}
  Trondheim:
    scenarios: {baseline: LowEfficiency, alternative: HighEfficiency}
"""
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "add partner data")
    return repo


@pytest.fixture
def seeded(data_root: Path, partners_repo: Path) -> tuple[Path, Path]:
    """A globi-data repo with v001 seeded for every partner."""
    from globi_data import inputs, registry

    scenarios = registry.load_partner_scenarios(
        partners_repo / "data" / "experiments.yaml"
    )
    for name in ("Lisbon", "Sao_Paulo", "Trondheim"):
        inputs.create_version(
            data_root,
            name,
            partners_repo / "data" / "partners" / name,
            summary=f"Initial import of {name}.",
            scenarios=scenarios.get(name),
        )
    return data_root, partners_repo
