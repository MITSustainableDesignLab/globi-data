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

Anything listed here must never be modified. Enforced by
[`.githooks/pre-commit`](../.githooks/pre-commit) locally and by
`globi-data check --since <base>` in CI, which reads the ledger *as of the merge
base* — so a version created inside a pull request stays editable there and
freezes the moment it merges.

It lives at the repository root deliberately: adding entries never perturbs the
directories it records.
