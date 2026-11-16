# Agent runbook

This repository stores the **input and output files** of GloBI simulation runs,
in versions. The simulations themselves live in the sibling repository
`globi-partners-data`.

## Repo map

| Path | What it is |
|---|---|
| `inputs/partners/<Partner>/vNNN/` | A frozen, self-contained input bundle |
| `inputs/partners/<Partner>/CURRENT.yml` | Which version is current |
| `inputs/partners/<Partner>/versions.yml` | Mutable status of every version |
| `outputs/runs/<Partner>/<weather>/<Scenario>/vNNN/` | Where a run's results live in S3, plus provenance |
| `outputs/batches/<Batch>/vNNN/` | Same, for run families too numerous to list individually |
| `outputs/surrogates/<Partner>/vNNN/` | A trained surrogate: manifest + `transforms.yml`; model in S3 |
| `outputs/STATUS.md` | Generated: which results are stale |
| `published.yml` | Append-only ledger of frozen directories |
| `countries.yml` | Mutable: ISO country code of each partner (input folder name) |
| `src/globi_data/` | The `globi-data` CLI |
| `docs/SCHEMA.md` | Every manifest field |
| `docs/DATA-COMPONENTS.md` | The components of a region; minimum GIS requirements |

## Rules

1. **Directories listed in `published.yml` are immutable.** Create a new version;
   never edit in place. To mark a bad version, use `globi-data inputs retract` —
   it touches `versions.yml` only. Currently advisory: `globi-data check --since
   <ref>` reports violations and CI surfaces them, but neither blocks, and the
   pre-commit hook is not installed by default.
2. **Mutable state lives outside version directories.** `CURRENT.yml` and
   `versions.yml` sit beside the `vNNN/` folders. Do not move them in.
3. **No git-lfs, and nothing over 25 MB, under `inputs/`.** CI fails on both.
   This one *is* a hard gate.
4. **Generated files are generated.** Do not hand-edit `inputs/README.md`,
   `*/index.yml`, `outputs/STATUS.md`, or per-partner `README.md`. Run
   `globi-data index --write`.

## Commands

```bash
uv sync                                   # add --extra s3 for S3 commands

uv run globi-data inputs list
uv run globi-data inputs show Lisbon
uv run globi-data inputs diff Lisbon v001 v002
uv run globi-data inputs verify --all
uv run globi-data status
uv run globi-data check                   # everything CI runs

uv run globi-data surrogates list
uv run globi-data surrogates show MA
uv run globi-data surrogates fetch MA     # -> ~/.cache/globi-data/surrogates/MA/vNNN/
uv run globi-data surrogates record MA --from s3://... --summary "..."   # draft
uv run globi-data surrogates promote MA vNNN
```

`examples/ma-surrogate.ipynb` downloads and runs the MA surrogate
(`uv sync --extra surrogate`).

Validation before pushing:

```bash
uv run ruff check src/ tests/ && uv run ruff format src/ tests/
uv run pyright && uv run pytest && uv run globi-data check
```

## Things that will trip you up

**Filenames are not consistent across partners.** Sao_Paulo and MA use `.yml`
where others use `.yaml`; Trondheim has no plain `manifest.yml`; MA has neither
`artifacts.yml` nor `manifest.yml`; Singapore's GIS file is
`buildings-singapore.geojson`. Resolve files through `globi.roles` in the
manifest, never by assuming a name.

**Paths inside `artifacts.yml` are wrong here, by design.** They are
repo-root-relative to globi-partners-data and become meaningless once a bundle
moves. They are kept verbatim for reference; `globi.roles` is the truth.

**GIS files are not in this repository.** `buildings.geojson` stays under
git-lfs in globi-partners-data. Each version records its size and sha256. A file
of ~133 bytes there means git-lfs was not pulled.

**`bucket_prefix` is parsed from the URI, never from the environment.** The
checked-in URIs use `globi-partners`; `globi-partners-data/.env` sets
`SCYTHE_STORAGE_BUCKET_PREFIX=globi`. They have drifted. Reconstructing a URI
from the environment looks in the wrong place.

**`confidence: inferred` means assumed, not observed.** The 28 backfilled output
versions pin `v001` because that is the only version that exists, not because it
was recorded at run time. Do not upgrade these to `exact`.

**In an output manifest, `version` is the scythe run version, not the globi-data
version.** That field name is fixed by compatibility with
`globi-partners latest-results --yaml-dir`. The globi-data version is
`output_version`.

**Surrogate outputs are per m², before COP.** The MA surrogate predicts thermal
demand per conditioned floor area, so changing the heating system does not move
`Energy.Heating`. `targets[].unit` in the manifest is the authority.

**`impact` decides staleness.** A version that only changes documentation is
`metadata-only` and must not mark results stale. Do not override the automatic
classification without a reason.

## Do not assume live state

Result URIs in output manifests are records of where files were, not proof they
are still there. Use `globi-data outputs verify` (needs credentials) before
claiming an object exists.

## Not yet done

The consumer side in globi-partners-data is not wired up: `_partner_dir` there
still resolves `data/partners/<Partner>`, not this repository. See the
"Integration" section of the plan. Until that lands, this repository is a
complete, validated record that nothing reads from automatically.
