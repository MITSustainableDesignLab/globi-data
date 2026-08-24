"""Tests for the guarantees the versioning system is supposed to provide."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from globi_data import check, index, inputs, outputs, paths, roles, status
from globi_data.hashing import bundle_sha256
from globi_data.paths import GlobiDataError

RESULT_KEYS = ("EnergyAndPeak", "BasicOverheating")


def _results(experiment: str, version: str = "v1.0.0", ts: str = "2026-06-08_12-27-10"):
    """Build a realistic result-URI mapping for an experiment."""
    return {
        key: f"s3://ml-for-bem/globi-partners/{experiment}/{version}/{ts}/final/{key}.pq"
        for key in RESULT_KEYS
    }


# --------------------------------------------------------------------------- #
# Curation
# --------------------------------------------------------------------------- #


def test_curation_keeps_inputs_and_drops_noise(seeded):
    """Backups and build intermediates are excluded, with a stated reason."""
    root, _ = seeded
    manifest = inputs.read_manifest(paths.input_version_dir(root, "Lisbon", "v001"))
    stored = {entry.path for entry in manifest.files}

    assert "components-lib.db" in stored
    assert "weather/Lisbon_TMYx.epw" in stored
    assert "weather_ftmy/Lisbon_ftmy_2050.zip" in stored

    assert "components-lib-old.db" not in stored
    assert "Lisbon_ftmy_2050.epw.txt" not in stored
    assert "buildings.geojson" not in stored

    skipped = "\n".join(manifest.not_carried_over)
    assert "components-lib-old.db" in skipped
    assert "superseded backup" in skipped


def test_gis_recorded_as_external_not_stored(seeded):
    """GIS geometry stays out of the repo but keeps its fingerprint."""
    root, partners_repo = seeded
    version_dir = paths.input_version_dir(root, "Lisbon", "v001")
    manifest = inputs.read_manifest(version_dir)

    assert not (version_dir / "buildings.geojson").exists()

    gis = next(e for e in manifest.external_files if e.role == "gis_file")
    source = partners_repo / "data" / "partners" / "Lisbon" / "buildings.geojson"
    assert gis.size_bytes == source.stat().st_size
    assert gis.sha256 is not None
    assert gis.stored_in.path == "data/partners/Lisbon/buildings.geojson"
    assert manifest.role_path("gis_file") == "external:buildings.geojson"


@pytest.mark.parametrize(
    ("partner", "expected_ext"),
    [("Lisbon", "yaml"), ("Sao_Paulo", "yml")],
)
def test_roles_resolve_across_filename_spellings(seeded, partner, expected_ext):
    """Partners disagree on .yaml vs .yml; roles resolve either way."""
    root, _ = seeded
    manifest = inputs.read_manifest(paths.input_version_dir(root, partner, "v001"))
    assert (
        manifest.role_path("semantic_fields_file") == f"semantic-fields.{expected_ext}"
    )
    assert manifest.role_path("component_map_file") == f"component-map.{expected_ext}"
    assert manifest.role_path("db_file") == "components-lib.db"


def test_partner_without_plain_manifest_carries_every_variant(seeded):
    """Trondheim has no manifest.yml; both scenario variants are kept."""
    root, _ = seeded
    manifest = inputs.read_manifest(paths.input_version_dir(root, "Trondheim", "v001"))
    stored = {entry.path for entry in manifest.files}
    assert "manifest_LowEfficiency.yml" in stored
    assert "manifest_HighEfficiency.yml" in stored
    assert manifest.role_path("experiment_manifest") in {
        "manifest_LowEfficiency.yml",
        "manifest_HighEfficiency.yml",
    }


def test_scenarios_recorded_from_registry(seeded):
    """The bundle records which scenarios it compares."""
    root, _ = seeded
    manifest = inputs.read_manifest(paths.input_version_dir(root, "Lisbon", "v001"))
    assert manifest.globi.scenarios == {
        "baseline": "Baseline",
        "alternative": "Retrofit",
    }


def test_oversized_input_is_refused(data_root, partners_repo, monkeypatch):
    """A file too large for git is rejected rather than silently committed."""
    monkeypatch.setattr(roles, "FAIL_BYTES", 100)
    monkeypatch.setattr(roles, "WARN_BYTES", 50)
    with pytest.raises(GlobiDataError, match="over the"):
        inputs.create_version(
            data_root,
            "Lisbon",
            partners_repo / "data" / "partners" / "Lisbon",
            summary="too big",
        )


# --------------------------------------------------------------------------- #
# The no-op guard
# --------------------------------------------------------------------------- #


def test_identical_version_is_refused(seeded):
    """A version that changes nothing is not a version."""
    root, partners_repo = seeded
    with pytest.raises(GlobiDataError, match="byte-identical"):
        inputs.create_version(
            root,
            "Lisbon",
            partners_repo / "data" / "partners" / "Lisbon",
            summary="no change",
        )


def test_identical_version_allowed_with_explicit_override(seeded):
    """--allow-noop exists for deliberate metadata-only bumps."""
    root, partners_repo = seeded
    result = inputs.create_version(
        root,
        "Lisbon",
        partners_repo / "data" / "partners" / "Lisbon",
        summary="metadata only",
        allow_noop=True,
    )
    assert result.manifest.version == "v002"
    assert result.manifest.impact == "metadata-only"


def test_failed_creation_leaves_no_partial_directory(seeded):
    """A refused version must not leave a half-written folder behind."""
    root, partners_repo = seeded
    with pytest.raises(GlobiDataError):
        inputs.create_version(
            root,
            "Lisbon",
            partners_repo / "data" / "partners" / "Lisbon",
            summary="no change",
        )
    assert not paths.input_version_dir(root, "Lisbon", "v002").exists()
    assert paths.list_versions(paths.partner_dir(root, "Lisbon")) == ["v001"]


# --------------------------------------------------------------------------- #
# Impact classification and staleness
# --------------------------------------------------------------------------- #


def _bump(root: Path, partners_repo: Path, partner: str, mutate) -> str:
    """Apply ``mutate`` to the source directory and cut a new version."""
    source = partners_repo / "data" / "partners" / partner
    mutate(source)
    result = inputs.create_version(root, partner, source, summary="changed")
    return result.manifest.version


def test_changing_a_component_db_is_simulation_affecting(seeded):
    """A different components library can change results."""
    root, partners_repo = seeded
    version = _bump(
        root,
        partners_repo,
        "Lisbon",
        lambda src: (src / "components-lib.db").write_bytes(b"SQLite format 3\x00new"),
    )
    manifest = inputs.read_manifest(paths.input_version_dir(root, "Lisbon", version))
    assert manifest.impact == "simulation-affecting"
    assert any(c.path == "components-lib.db" for c in manifest.changes)


def test_stale_when_a_simulation_affecting_version_lands(seeded):
    """Results built on an older input are flagged for a re-run."""
    root, partners_repo = seeded
    outputs.record_experiment(
        root,
        "Lisbon/tmy/Baseline",
        _results("Lisbon/tmy/Baseline"),
        summary="initial",
        confidence="exact",
    )
    assert status.evaluate_experiment(root, "Lisbon/tmy/Baseline").state == "ok"

    _bump(
        root,
        partners_repo,
        "Lisbon",
        lambda src: (src / "components-lib.db").write_bytes(b"SQLite format 3\x00new"),
    )

    row = status.evaluate_experiment(root, "Lisbon/tmy/Baseline")
    assert row.state == "stale"
    assert row.pinned_version == "v001"
    assert row.current_version == "v002"


def test_metadata_only_version_does_not_make_results_stale(seeded):
    """A documentation bump must not mark every experiment for a re-run.

    This is the distinction that keeps the status page worth reading.
    """
    root, partners_repo = seeded
    outputs.record_experiment(
        root,
        "Lisbon/tmy/Baseline",
        _results("Lisbon/tmy/Baseline"),
        summary="initial",
        confidence="exact",
    )
    inputs.create_version(
        root,
        "Lisbon",
        partners_repo / "data" / "partners" / "Lisbon",
        summary="clarify the README",
        allow_noop=True,
    )

    row = status.evaluate_experiment(root, "Lisbon/tmy/Baseline")
    assert row.state == "metadata-drift"
    assert "No re-run needed" in row.detail


def test_backfilled_pins_are_reported_as_assumptions(seeded):
    """An inferred pin never masquerades as an observed one."""
    root, _ = seeded
    outputs.record_experiment(
        root,
        "Lisbon/tmy/Baseline",
        _results("Lisbon/tmy/Baseline"),
        summary="backfilled",
        confidence="inferred",
    )
    assert status.evaluate_experiment(root, "Lisbon/tmy/Baseline").state == "inferred"


def test_tampering_with_a_pinned_version_is_detected(seeded):
    """Editing a published version after results pinned it is caught."""
    root, _ = seeded
    outputs.record_experiment(
        root,
        "Lisbon/tmy/Baseline",
        _results("Lisbon/tmy/Baseline"),
        summary="initial",
        confidence="exact",
    )
    victim = paths.input_version_dir(root, "Lisbon", "v001") / "components-lib.db"
    victim.write_bytes(b"tampered")

    assert status.evaluate_experiment(root, "Lisbon/tmy/Baseline").state == "tampered"


def test_broken_pin_when_the_version_disappears(seeded):
    """A pin to a version that no longer exists is an error, not silence."""
    root, _ = seeded
    outputs.record_experiment(
        root,
        "Lisbon/tmy/Baseline",
        _results("Lisbon/tmy/Baseline"),
        summary="initial",
        confidence="exact",
    )
    shutil.rmtree(paths.input_version_dir(root, "Lisbon", "v001"))
    assert status.evaluate_experiment(root, "Lisbon/tmy/Baseline").state == "broken-pin"


# --------------------------------------------------------------------------- #
# Outputs
# --------------------------------------------------------------------------- #


def test_output_manifest_keeps_the_legacy_payload(seeded):
    """The first four fields stay byte-compatible with latest-results.yml."""
    root, _ = seeded
    results = _results("Lisbon/tmy/Baseline")
    manifest = outputs.record_experiment(
        root, "Lisbon/tmy/Baseline", results, summary="x", confidence="exact"
    )
    assert manifest is not None
    assert manifest.experiment == "Lisbon/tmy/Baseline"
    assert manifest.version == "v1.0.0"
    assert manifest.run_timestamp == "2026-06-08_12-27-10"
    assert manifest.results == results


def test_bucket_prefix_is_read_from_the_uri(seeded):
    """The prefix must never be reconstructed from the environment.

    Checked-in URIs use `globi-partners` while `.env` says `globi`; trusting the
    environment would look in the wrong place.
    """
    root, _ = seeded
    manifest = outputs.record_experiment(
        root,
        "Lisbon/tmy/Baseline",
        _results("Lisbon/tmy/Baseline"),
        summary="x",
        confidence="exact",
    )
    assert manifest is not None
    assert manifest.provenance.storage.bucket == "ml-for-bem"
    assert manifest.provenance.storage.bucket_prefix == "globi-partners"


def test_partner_alias_resolves_to_the_input_bundle(seeded):
    """Sao_Paulo runs as Sao_Paulo_Bela_Vista but pins the Sao_Paulo bundle."""
    root, partners_repo = seeded
    from globi_data import registry

    aliases = registry.load_partner_aliases(partners_repo / "data" / "experiments.yaml")
    manifest = outputs.record_experiment(
        root,
        "Sao_Paulo_Bela_Vista/tmy/noAC",
        _results("Sao_Paulo_Bela_Vista/tmy/noAC"),
        summary="x",
        confidence="exact",
        partner_aliases=aliases,
        scenario_kinds=registry.load_scenario_kinds(
            partners_repo / "data" / "experiments.yaml"
        ),
    )
    assert manifest is not None
    assert manifest.partner == "Sao_Paulo"
    assert manifest.provenance.input.partner == "Sao_Paulo"
    assert manifest.provenance.input.version == "v001"
    assert manifest.scenario_kind == "baseline"


def test_recording_the_same_run_twice_is_a_no_op(seeded):
    """Re-recording unchanged results must not invent a version."""
    root, _ = seeded
    results = _results("Lisbon/tmy/Baseline")
    first = outputs.record_experiment(
        root, "Lisbon/tmy/Baseline", results, summary="x", confidence="exact"
    )
    second = outputs.record_experiment(
        root, "Lisbon/tmy/Baseline", results, summary="x", confidence="exact"
    )
    assert first is not None
    assert second is None


def test_new_run_creates_a_new_output_version(seeded):
    """A genuinely different run is recorded alongside, not over, the old one."""
    root, _ = seeded
    outputs.record_experiment(
        root,
        "Lisbon/tmy/Baseline",
        _results("Lisbon/tmy/Baseline"),
        summary="first",
        confidence="exact",
    )
    manifest = outputs.record_experiment(
        root,
        "Lisbon/tmy/Baseline",
        _results("Lisbon/tmy/Baseline", ts="2026-07-01_09-00-00"),
        summary="rerun",
        confidence="exact",
    )
    assert manifest is not None
    assert manifest.output_version == "v002"
    assert manifest.parent_version == "v001"
    edir = paths.experiment_dir(root, "Lisbon/tmy/Baseline")
    assert paths.list_versions(edir) == ["v001", "v002"]
    # The old version is still readable exactly as it was.
    old = outputs.read_output_manifest(edir / "v001")
    assert old.run_timestamp == "2026-06-08_12-27-10"


def test_parse_s3_uri_rejects_non_s3():
    """A malformed URI is an error, not a silent pass-through."""
    with pytest.raises(GlobiDataError, match="not an s3"):
        outputs.parse_s3_uri("https://example.com/thing.pq")


# --------------------------------------------------------------------------- #
# Verification and integrity
# --------------------------------------------------------------------------- #


def test_verify_detects_a_modified_file(seeded):
    """Re-hashing catches content that no longer matches the manifest."""
    root, _ = seeded
    (paths.input_version_dir(root, "Lisbon", "v001") / "components-lib.db").write_bytes(
        b"changed"
    )
    issues = inputs.verify_version(root, "Lisbon", "v001")
    assert any("sha256 mismatch" in issue.message for issue in issues)


def test_verify_detects_an_unrecorded_file(seeded):
    """A file added to a frozen version is reported."""
    root, _ = seeded
    (paths.input_version_dir(root, "Lisbon", "v001") / "sneaky.txt").write_text("hi")
    issues = inputs.verify_version(root, "Lisbon", "v001")
    assert any("not in the manifest" in issue.message for issue in issues)


def test_unpulled_lfs_pointer_gets_an_actionable_message(seeded, tmp_path):
    """A fresh clone leaves a tiny pointer where the GIS file should be."""
    root, _ = seeded
    gis_root = tmp_path / "gis"
    (gis_root / "Lisbon").mkdir(parents=True)
    (gis_root / "Lisbon" / "buildings.geojson").write_text(
        "version https://git-lfs.github.com/spec/v1\noid sha256:abc\nsize 1129469887\n"
    )
    issues = inputs.verify_version(root, "Lisbon", "v001", gis_root=gis_root)
    message = " ".join(issue.message for issue in issues)
    assert "git lfs pull" in message


def test_bundle_hash_ignores_non_simulation_files(seeded):
    """A README change must not invalidate the bundle identity."""
    root, _ = seeded
    manifest = inputs.read_manifest(paths.input_version_dir(root, "Lisbon", "v001"))
    entries = manifest.simulation_affecting_entries()
    assert bundle_sha256(entries) == manifest.bundle_sha256
    assert all(path != "README.md" for path, _ in entries)


def test_full_check_passes_on_a_seeded_repo(seeded):
    """`globi-data check` is clean straight after seeding."""
    root, _ = seeded
    index.rebuild(root, write=True)
    problems = [p for p in check.run_checks(root) if p.level == "error"]
    assert problems == [], problems


def test_index_generation_is_idempotent(seeded):
    """Regenerating twice reports no drift, so CI can gate on it."""
    root, _ = seeded
    index.rebuild(root, write=True)
    assert index.rebuild(root, write=False) == []


# --------------------------------------------------------------------------- #
# Drafts, promotion and retraction
# --------------------------------------------------------------------------- #


def test_draft_copies_current_without_publishing_it(seeded):
    """A draft exists but is not current and is not frozen."""
    root, _ = seeded
    manifest = inputs.draft_version(root, "Lisbon", summary="swap the components DB")
    assert manifest.version == "v002"

    pdir = paths.partner_dir(root, "Lisbon")
    assert paths.read_current(pdir).current == "v001"
    assert paths.read_versions(pdir).get("v002").status == "draft"
    assert "inputs/partners/Lisbon/v002" not in paths.read_published(root).paths()
    # External GIS records survive the copy, so lineage is not lost.
    assert inputs.read_manifest(pdir / "v002").external_files


def test_promoting_an_edited_draft_makes_it_current(seeded):
    """Merging a draft publishes it and freezes it."""
    root, _ = seeded
    inputs.draft_version(root, "Lisbon", summary="swap the components DB")
    (paths.input_version_dir(root, "Lisbon", "v002") / "components-lib.db").write_bytes(
        b"SQLite format 3\x00edited"
    )

    manifest = inputs.promote_version(root, "Lisbon", "v002")
    pdir = paths.partner_dir(root, "Lisbon")

    assert manifest.impact == "simulation-affecting"
    assert paths.read_current(pdir).current == "v002"
    assert paths.read_versions(pdir).get("v002").status == "active"
    assert paths.read_versions(pdir).get("v001").status == "superseded"
    assert "inputs/partners/Lisbon/v002" in paths.read_published(root).paths()


def test_promoting_an_unedited_draft_is_refused(seeded):
    """An untouched draft is a no-op version and must not be published."""
    root, _ = seeded
    inputs.draft_version(root, "Lisbon", summary="nothing yet")
    with pytest.raises(GlobiDataError, match="byte-identical"):
        inputs.promote_version(root, "Lisbon", "v002")


def test_retraction_does_not_touch_the_frozen_directory(seeded):
    """Retracting edits the ledger only, never the version itself."""
    root, _ = seeded
    version_dir = paths.input_version_dir(root, "Lisbon", "v001")
    before = inputs.manifest_sha(version_dir)

    inputs.retract_version(root, "Lisbon", "v001", reason="bad weather file")

    entry = paths.read_versions(paths.partner_dir(root, "Lisbon")).get("v001")
    assert entry.status == "retracted"
    assert entry.retracted_reason == "bad weather file"
    assert inputs.manifest_sha(version_dir) == before


# --------------------------------------------------------------------------- #
# Diffing
# --------------------------------------------------------------------------- #


def test_diff_reports_added_removed_and_modified(seeded):
    """`inputs diff` is how you decide whether a re-run is really needed."""
    root, partners_repo = seeded
    source = partners_repo / "data" / "partners" / "Lisbon"
    (source / "components-lib.db").write_bytes(b"SQLite format 3\x00new")
    (source / "weather_ftmy" / "Lisbon_ftmy_2050.zip").unlink()
    (source / "weather_ftmy" / "Lisbon_ftmy_2060.zip").write_bytes(b"PK\x03\x04new")
    inputs.create_version(root, "Lisbon", source, summary="refresh")

    diffs = {
        d.path: d.change for d in inputs.diff_versions(root, "Lisbon", "v001", "v002")
    }
    assert diffs["components-lib.db"] == "modified"
    assert diffs["weather_ftmy/Lisbon_ftmy_2050.zip"] == "removed"
    assert diffs["weather_ftmy/Lisbon_ftmy_2060.zip"] == "added"
