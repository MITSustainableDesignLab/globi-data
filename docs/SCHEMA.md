# Manifest schemas

Four kinds of file carry structure. Their models live in
[`src/globi_data/models.py`](../src/globi_data/models.py) and are validated on
every read, so anything here that is wrong will fail `globi-data check` rather
than being silently accepted.

---

## `input-version.yml`

Sits inside a frozen input version directory and describes it completely.

```yaml
schema_version: 1
kind: input-version
partner: Lisbon
version: v002
parent_version: v001
created_at: "2026-08-24T14:12:44Z"
created_by: {name: Darya Guettler, email: daryag@mit.edu}

summary: Corrected envelope U-values; ssp245 future weather.
impact: simulation-affecting        # or metadata-only
changes:
  - {path: components-lib.db, change: modified, note: "U-values for pre-1960"}
not_carried_over:
  - "components-lib-old.db - superseded backup of components-lib.db"

source:                             # where this bundle came from
  repo: globi-partners-data
  remote: https://github.com/MITSustainableDesignLab/globi-partners-data.git
  commit: 3f9a1c2e8b7d...
  dirty: false
  path: data/partners/Lisbon

globi:
  bundle_kind: experiment           # experiment | raw
  scenarios: {baseline: Baseline, alternative: Retrofit}
  roles:                            # role -> file in THIS bundle
    experiment_manifest: manifest.yml
    file_config: artifacts.yml
    gis_preprocessor_config: gis-preprocessor.yml
    db_file: components-lib.db
    semantic_fields_file: semantic-fields.yaml
    component_map_file: component-map.yaml
    epwzip_file: "https://climate.onebuilding.org/.../PRT_LB_Lisboa...zip"
    gis_file: "external:buildings.geojson"
  notes: null

files:
  - path: components-lib.db
    role: db_file
    bytes: 888832
    sha256: 3f79bb7b435b...
    simulation_affecting: true
    changed_from_parent: true

external_files:                     # recorded, not stored
  - path: buildings.geojson
    role: gis_file
    bytes: 1129469887
    sha256: 9a544bc480a7...
    stored_in:
      repo: globi-partners-data
      commit: 3f9a1c2e8b7d...
      path: data/partners/Lisbon/buildings.geojson
      storage: git-lfs
    resolver: $GLOBI_GIS_ROOT/Lisbon/buildings.geojson
    reason: 1129 MB of geometry - kept under git-lfs where it already lives.

remote_files: []                    # inputs pushed to S3 instead of git

totals: {file_count: 14, bytes: 6412873}
bundle_sha256: 9b71d224bd62...
```

### Why roles rather than filenames

Filenames are not consistent across partners. Sao_Paulo and MA use
`component-map.yml` where others use `component-map.yaml`; Trondheim has no
plain `manifest.yml`, only `manifest_LowEfficiency.yml` and
`manifest_HighEfficiency.yml`; MA has neither `artifacts.yml` nor `manifest.yml`;
Singapore's GIS file is `buildings-singapore.geojson` and its weather zip is a
local path rather than a URL.

So the manifest maps **roles** to whatever the file is actually called here, and
consumers resolve by role. The paths written inside `artifacts.yml` itself are
repo-root-relative and become meaningless once a bundle moves — treat them as
decorative and use `globi.roles` instead.

A `gis_file` value of `external:<name>` means "look it up in `external_files`".
An `epwzip_file` value starting `http://`, `https://` or `s3://` is a remote
reference used as-is; when the weather zip is stored here instead, the role is
`epwzip_file_local`.

### The three hashes

| Hash | What it covers | Why |
|---|---|---|
| A file's `sha256` | That file's bytes | Detects corruption or edits |
| `bundle_sha256` | All simulation-affecting files plus external files | The content identity of the bundle: drives the no-op guard and the tamper check |
| `manifest_sha256` | The bytes of `input-version.yml` itself | What an output version pins |

`bundle_sha256` is a sha256 over `"{sha256}  {path}\n"` lines for every
simulation-affecting entry, sorted by path — the same format `shasum` emits, so
it can be reproduced with standard tools. `README.md` and `input-version.yml`
are excluded, which is why a documentation fix cannot invalidate downstream
results.

`manifest_sha256` is reproducible by hand:

```bash
shasum -a 256 inputs/partners/Lisbon/v002/input-version.yml
```

---

## `CURRENT.yml`

Lives beside the version directories, never inside one.

```yaml
schema_version: 1
partner: Lisbon
current: v002
manifest: v002/input-version.yml
manifest_sha256: 4a44dc153642...
bundle_sha256: 9b71d224bd62...
updated_at: "2026-08-24T14:12:44Z"
```

A file, not a symlink: symlinks break on Windows checkouts and render as a
20-byte text blob on GitHub.

Resolution order for consumers: an explicit `vNNN` → `CURRENT.yml` → the highest
version present (with a warning) → an error listing what is available.

---

## `versions.yml`

The mutable status of every version. Also outside the frozen directories — this
is what allows a bad version to be retracted without editing it.

```yaml
schema_version: 1
partner: Lisbon
versions:
  - {version: v001, status: superseded, created_at: "...", impact: simulation-affecting, summary: "..."}
  - {version: v002, status: active, created_at: "...", impact: simulation-affecting, summary: "..."}
```

`status` is one of:

| Status | Meaning |
|---|---|
| `draft` | Exists on a branch, still editable, not current, not frozen |
| `active` | The current version. Exactly one per partner |
| `superseded` | Was current, still valid and referenceable |
| `retracted` | Should not be used; `retracted_reason` says why |

---

## `output-version.yml`

The first four fields reproduce exactly what
`globi-partners latest-results --yaml-dir` writes, so existing consumers keep
working. Note that `version` there means the **scythe run version**; the
globi-data version is `output_version`.

```yaml
schema_version: 1
kind: output-version

# --- legacy-compatible block ---
experiment: Ahmedabad/tmy/BAU
version: v1.0.0
run_timestamp: "2026-06-08_12-27-10"
results:
  EnergyAndPeak: s3://ml-for-bem/globi-partners/Ahmedabad/tmy/BAU/v1.0.0/2026-06-08_12-27-10/final/EnergyAndPeak.pq

# --- version envelope ---
output_version: v001
parent_version: null
status: active
created_at: "2026-08-24T15:02:11Z"
summary: Backfilled from latest-results.csv.
partner: Ahmedabad
weather: tmy
scenario_kind: baseline
scenario_value: BAU

provenance:
  input:
    partner: Ahmedabad
    version: v001
    manifest_path: inputs/partners/Ahmedabad/v001/input-version.yml
    manifest_sha256: 4a44dc153642...
    bundle_sha256: 9b71d224bd62...
    confidence: inferred            # exact | inferred | unknown
    gis_file: {sha256: "...", bytes: 122168816}
    uploaded_artifacts: {}
  code:
    globi_partners_data: {commit: "...", dirty: false, remote: "..."}
    globi: {commit: "...", describe: "..."}
    scythe_engine: "1.3.0"
    python: "3.13.1"
  storage:
    bucket: ml-for-bem
    bucket_prefix: globi-partners
    run_prefix: s3://ml-for-bem/globi-partners/Ahmedabad/tmy/BAU/v1.0.0/2026-06-08_12-27-10
  run:
    scythe_version: v1.0.0
    run_timestamp: "2026-06-08_12-27-10"
  settings: {}

result_files:
  - result_key: EnergyAndPeak
    s3_uri: s3://.../EnergyAndPeak.pq
    bytes: null
    sha256: null
    sha256_source: none             # computed | none
    etag: null
    last_modified: null

totals: {file_count: 5, bytes: 0}
```

### `confidence`

- **`exact`** — the input version was recorded when the run was submitted.
- **`inferred`** — reconstructed during backfill. It is an assumption: the bytes
  that produced those results are not provably that version. Shown separately in
  `STATUS.md` and never silently upgraded.
- **`unknown`** — no input bundle existed to pin.

### `bucket_prefix`

Always parsed from the observed URI, never read from the environment. The
checked-in URIs use `globi-partners` while `globi-partners-data/.env` currently
sets `SCYTHE_STORAGE_BUCKET_PREFIX=globi`; reconstructing a URI from the
environment would look in the wrong place.

### Batches

Some run families are too numerous for one directory each — MA allocates roughly
355 specs per census tract across about 1600 tracts. Those use
`outputs/batches/<Batch>/vNNN/` with the same envelope, but `results:` is
replaced by a `result_index` pointing at a `results.csv`, plus an `allocation`
block.

---

## `surrogate-version.yml`

A trained surrogate model for one partner: semantic fields, weather and
geometry go in; end-use energy (and so EUI) comes out. It lives at
`outputs/surrogates/<Partner>/vNNN/`, beside a `transforms.yml`.

Weather is a model **input**, not a directory level, so one surrogate covers
current and future climate. That is why there is no `<weather>/` in the path,
unlike `outputs/runs/`.

The only surrogate so far is MA residential,
[`outputs/surrogates/MA/v001/`](../outputs/surrogates/MA/v001/). It uses
epengine's LightGBM layout: one `.lgb` per target under `model.files`, with
`space.yml` as the transforms. It was recorded with `globi-data surrogates
record`. The schema also accepts globi's single-file layout (`model.s3_uri` plus
a `transforms.yml`), for when globi saves a final model.

`CURRENT.yml` and `versions.yml` sit beside the `vNNN/` folders, as they do for
inputs. `surrogates promote` writes both.

```yaml
schema_version: 1
kind: surrogate-version
partner: MA
surrogate_version: v001
status: active                      # draft | active | superseded | retracted
summary: 'ma-webapp v5 (2025-10-01) iteration 2: ...'

model:                              # the regressor itself stays in S3
  backend: lgb                      # xgb | lgb | nn
  format: lightgbm-text
  files:                            # one file per target, each pinned by sha256
    - {target: Energy.Heating, s3_uri: s3://ml-for-bem/hatchet/ma-webapp/.../Energy.Heating.lgb, bytes: 11768755, sha256: 5bb6...}
  # or, a single file predicting every target, instead of files:
  # s3_uri: s3://.../model.ubj
  # sha256: ...

transforms:                         # stored HERE, pinned by hash
  path: space.yml                   # transforms.yml for globi
  format: epengine-space            # globi-transformers | epengine-space
  sha256: ...
  s3_uri: s3://ml-for-bem/hatchet/ma-webapp/.../space.yml

features:                           # one entry per model input
  - {name: feature.semantic.Heating, source: semantic, kind: categorical, semantic_field: Heating}
  - {name: feature.weather.file, source: weather, kind: categorical}
  - {name: feature.geometry.long_edge, source: geometry, kind: continuous}

weather_options: []                 # optional: each weather value -> a file in the pinned input bundle

targets:
  - {name: Energy.Heating, unit: "kWh/m2/yr, per conditioned floor area",
     description: "Annual Heating demand, before system efficiency (COP)"}
derived_outputs: []                 # e.g. {name: EUI, unit: ..., formula: "sum(Energy.*)"}

metrics:                            # held-out folds, averaged; empty when unknown
  split: test
  per_target: {}

provenance:
  input: {partner: MA, version: v001, manifest_sha256: 5e7870ef..., confidence: inferred}
  code: {...}
  storage: {bucket: ml-for-bem, bucket_prefix: hatchet, run_prefix: s3://ml-for-bem/hatchet/ma-webapp/...}
  training:
    experiment_id: ma-webapp/v5-20251001-105947/iter-002/train/0/models
    previous_experiment_ids: []       # earlier iterations of the training loop
```

### `transforms.yml` / `space.yml`

`format: epengine-space` is epengine's `RegressorInputSpec`: an ordered list of
features, each with either `values` (categorical, index-encoded) or `min`/`max`
(continuous, min-max scaled). It has no targets, which come from
`model.files[].target`.

`format: globi-transformers` is a verbatim dump of globi's `Transformers`
(`globi/models/surrogate/transforms.py`). It is the model's contract: the
ordered feature list, which features are continuous and how they are scaled,
the category list for every categorical feature (`cat_map`), and the target
names with the output scaler. It is small text, so it is kept in git where
anyone can read it without credentials.

### Feature sources

| `source` | Where a user gets the value | `default` |
|---|---|---|
| `semantic` | A semantic field of the pinned input version | not used; the user supplies it |
| `weather` | One of `weather_options` | the current-climate file |
| `geometry` | The GIS preprocessor (height, floors, footprint, shading) | **required** to run from semantic fields alone |
| `extra_space` | Basement/attic flags | as for geometry |

A feature with no `default` that is not `semantic` raises a warning. A
surrogate trained on geometry cannot be driven from semantic fields alone
unless every such input has a documented value.

Features that are constant in the training data are dropped by globi.
epengine keeps them: MA's `feature.semantic.Region` has one value, and two
monthly cooling-degree-day features have `min == max`, so they scale to NaN,
which LightGBM treats as missing. That matches training.

### What `globi-data check` verifies

| Check | Level |
|---|---|
| `transforms.yml` matches its `sha256` | error |
| `features` and `targets` name exactly what `transforms.yml` lists, with matching kinds | error |
| Every trained category of a `semantic` feature is an Option in the pinned semantic fields | error |
| An Option the model never saw (globi would encode it as `-1` and still predict) | warning |
| `weather_options` equal the weather feature's categories, and each `input_file` is in the pinned bundle | error |
| The pinned input manifest still matches `manifest_sha256` | error |
| `example: true` together with `status: active` | error |
| A model file without `sha256` | warning |

`globi-data surrogates fetch` re-checks each model file's `sha256` on every
call. An S3 object that was overwritten after recording is an error, never a
silent model swap.

### Before this is usable

- **globi does not save a final model.** The training loop keeps one model
  per CV fold, and `finalize` leaves a `TODO: save the final model?`
  (`globi/pipelines/training.py`). Until it writes one model and its
  `transforms.yml`, there is nothing for `model.s3_uri` to point at.
- **The weather feature is commented out.**
  `feature.weather.file` is disabled in
  `GloBIBuildingSpec.computed_features` (`globi/models/tasks.py`). The example
  assumes it is turned back on under that name.
- **Not yet in generated pages.** Surrogates are validated by `globi-data
  check` and have their own CLI (`globi-data surrogates`), but `index --write`
  does not list them in `outputs/README.md` or `STATUS.md` yet. `record` only
  understands epengine's layout so far.

---

## `published.yml`

The append-only immutability ledger, at the repository root.

```yaml
schema_version: 1
entries:
  - path: inputs/partners/Lisbon/v001
    tree_sha: null
    bundle_sha256: 9b71d224bd62...
    published_at: "2026-08-24T09:00:00Z"
    published_commit: null
```

Anything listed here must never be modified. `globi-data check --since <base>`
reports violations; it reads the ledger *as of the merge base*, so a version
created inside a pull request stays editable there and freezes the moment it
merges. A version is only treated as frozen once its files are actually in the
baseline, so a version's own first commit is never mistaken for tampering.

This is advisory by default. To make it a gate, install the optional pre-commit
hook with `globi-data init-hooks` and drop `continue-on-error` from the
corresponding step in `.github/workflows/validate.yml`.

It lives at the repository root deliberately: adding entries never perturbs the
directories it records.
