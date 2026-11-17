# GloBI public regional building inventory data

**Status: pre-onboarding draft.** Bucket name, AWS sponsorship account, and region are **TBD** pending [AWS Open Data Sponsorship Program](https://aws.amazon.com/opendata/open-data-sponsorship-program/) onboarding.

This page is the canonical **Documentation** reference for the public S3 dataset and the [Registry of Open Data on AWS](https://registry.opendata.aws) entry (`globi-regional-building-data`). It covers dataset purpose, bucket architecture, exact object layouts, storage footprint, programmatic access, cryptographic provenance, and bucket security posture.

Companion documentation in [`globi-data`](https://github.com/MITSustainableDesignLab/globi-data):

- [PUBLIC-PRODUCT.md](PUBLIC-PRODUCT.md) — processed output keys and post-processing pipeline
- [HOW-TO-DOWNLOAD-INPUTS.md](HOW-TO-DOWNLOAD-INPUTS.md) — plain-language glossary of input files
- [DATA-COMPONENTS.md](DATA-COMPONENTS.md) — semantic archetypes, SQLite component library, and GIS specs
- [SCHEMA.md](SCHEMA.md) — full YAML schema for input and output manifests
- [GIS-ACCESS.md](GIS-ACCESS.md) — building footprint distribution and sha256 verification
- [GloBI simulation engine](https://github.com/MITSustainableDesignLab/globi) — open-source urban building energy modeling software

---

## Scientific context and public value

Urban Building Energy Modeling (UBEM) evaluates decarbonization, grid peak demand, and extreme-heat resilience across entire cities, but reproducible inputs and building-level simulation results are rarely available in standardized, cloud-native formats.

The **Global Building Inventory (GloBI)** dataset provides:

1. **Self-contained regional input bundles (`globi-inputs/`)** — EnergyPlus-compatible SQLite material/HVAC libraries, semantic archetype mappings, and both historical Typical Meteorological Year (TMY) and mid-century (2050 SSP2-4.5) Future Typical Meteorological Year (FTMY) weather files.
2. **Building-level simulation results (`globi-public/`)** — Apache Parquet tables reporting annual/end-use energy and peak demand, indoor overheating metrics, and operational carbon emissions across paired policy/technology scenarios in seven countries (eight regions total).

Hosting both prefixes in a single public S3 bucket lets researchers, municipalities, and energy modelers query building-level Parquet directly from cloud compute (Amazon Athena, DuckDB, PyArrow, Spark on EMR/EC2) while fetching the exact input parameters that generated each run.

---

## Bucket architecture and prefixes

One public S3 bucket (configured in [`public_storage.yml`](../public_storage.yml)) exposes two top-level prefixes:

| S3 Prefix | Contents | Object count at launch | Footprint |
|-----------|----------|------------------------|-----------|
| `globi-inputs/` | Frozen regional input bundles (`<ISO>/<Partner>/vNNN/...`) | 130 files across 8 regional `v001` bundles | ~57 MB (uncompressed) |
| `globi-public/` | Building-level processed Parquet results (`<ISO>/<City>/<weather>/<Scenario>/<output_version>/*.parquet`) | 84 Parquet objects (28 experiments × 3 tables) | Columnar Parquet (size varies by city building stock; recorded per object in `output-version.yml`) |

### Why both Git and S3?

| Surface | Role | When to use |
|---------|------|-------------|
| **Amazon S3** (`globi-inputs/`, `globi-public/`) | Bulk data plane for cloud workflows, anonymous `aws s3` syncs, and zero-install Parquet analytics | Running simulations on EC2/Batch, querying results with DuckDB/PyArrow/Athena, or downloading bundles without cloning Git |
| **GitHub** (`MITSustainableDesignLab/globi-data`) | Immutable catalog of record (`published.yml`, `CURRENT.yml`, `versions.yml`, `STATUS.md`, sha256 manifests) | Resolving which `vNNN` is current, auditing staleness, checking diffs between versions, or using the `globi-data` CLI |

### Explicitly excluded from public S3

- **Raw simulator workfiles (`globi-partners/.../final/*.pq`)** — internal Scythe engine intermediates remain private; only curated, documented Parquet products are published under `globi-public/`.
- **Raw partner building footprints (`buildings.geojson`)** — multi-hundred-MB to multi-GB vector GIS files (e.g., ~1.13 GB for Lisbon) are excluded from `globi-inputs/` due to partner licensing and size constraints. Every `input-version.yml` records exact byte size and `sha256` so authorized users can verify external geometry (see [GIS-ACCESS.md](GIS-ACCESS.md)).
- **Surrogate model weights** — Massachusetts (`US/MA`) input bundles are included under `globi-inputs/US/MA/v001/`, while LightGBM surrogate weights are tracked separately under `outputs/surrogates/US/MA/`.

---

## Regional coverage and scenarios

Paths use ISO 3166-1 alpha-2 country codes (mapped in [`countries.yml`](../countries.yml)). Seven cities have full paired TMY + FTMY simulation outputs (7 cities × 2 weather horizons × 2 scenarios = **28 experiments**); Massachusetts (`US/MA`) provides regional input bundles used for surrogate modeling.

| ISO | Input path (`globi-inputs/`) | Output path prefix (`globi-public/`) | Weather horizons | Baseline scenario | Alternative scenario | Input bundle (`v001`) |
|-----|------------------------------|--------------------------------------|------------------|-------------------|----------------------|-----------------------|
| `BR` | `BR/Sao_Paulo/v001/` | `BR/Sao_Paulo_Bela_Vista/` | `tmy`, `ftmy` | `noAC` (unconditioned baseline) | `withAC` (cooling adoption) | 15 files (4.3 MB) |
| `GB` | `GB/Manchester/v001/` | `GB/Manchester/` | `tmy`, `ftmy` | `No_DSR` (standard heating control) | `DSR` (demand-side response) | 16 files (7.0 MB) |
| `IN` | `IN/Ahmedabad/v001/` | `IN/Ahmedabad/` | `tmy`, `ftmy` | `BAU` (business as usual) | `CC` (cool roofs / envelope) | 15 files (4.7 MB) |
| `KE` | `KE/Nairobi/v001/` | `KE/Nairobi/` | `tmy`, `ftmy` | `noAC` (natural ventilation) | `withAC` (mechanical cooling) | 15 files (4.7 MB) |
| `NO` | `NO/Trondheim/v001/` | `NO/Trondheim/` | `tmy`, `ftmy` | `LowEfficiency` | `HighEfficiency` (envelope/HVAC upgrade) | 15 files (4.9 MB) |
| `PT` | `PT/Lisbon/v001/` | `PT/Lisbon/` | `tmy`, `ftmy` | `Baseline` | `Retrofit` | 13 files (5.0 MB) |
| `SG` | `SG/Singapore/v001/` | `SG/Singapore/` | `tmy`, `ftmy` | `Baseline` | `Retrofit` | 14 files (4.3 MB) |
| `US` | `US/MA/v001/` | *(surrogate workflow)* | multi-station (`Boston`, `Worcester`, `Pittsfield`) | *(feature space)* | *(feature space)* | 27 files (21.9 MB) |

> **Note on Brazil naming:** Input bundles are keyed by partner `BR/Sao_Paulo/`, whereas simulation runs represent the Bela Vista district (`BR/Sao_Paulo_Bela_Vista/`). That mapping is declared in `countries.yml` under `run_aliases`.

---

## Detailed layout: Input bundles (`globi-inputs/`)

Each version directory is **immutable** once listed in [`published.yml`](../published.yml). Updating any simulation-affecting file mints a new version (`v002`, `v003`, …) rather than overwriting objects in place.

```text
s3://<bucket>/globi-inputs/<ISO>/<Partner>/<input_version>/
├── README.md                 # Human-readable inventory of files in this bundle
├── input-version.yml         # Per-file bytes, sha256, role bindings, bundle_sha256, GIS sha256
├── components-lib.db         # SQLite database of constructions, materials, schedules, HVAC templates
├── semantic-fields.yaml      # Allowed building attributes (typology, vintage, system types; .yml or .yaml)
├── component-map.yaml        # Mapping rules from semantic attributes to components-lib.db entries
├── gis-preprocessor.yml      # Footprint cleaning and attribute normalization rules (where applicable)
├── manifest.yml              # Experiment scenario definitions (experiment bundles)
├── artifacts.yml             # Historical source paths; resolve files via input-version.yml globi.roles
├── weather/                  # Historical climate (.epw, .ddy, .zip; e.g., TMYx 2009–2023)
└── weather_ftmy/             # Morphed future climate (.epw, .ddy, .zip; e.g., 2050 SSP2-4.5 CanESM5)
```

*(Exact extensions vary slightly by partner—for example `.yml` vs `.yaml`, or `context-small.parquet` in `US/MA`. Consumers should resolve functional roles through `globi.roles` in `input-version.yml`.)*

---

## Detailed layout: Processed results (`globi-public/`)

Every experiment directory under `globi-public/` exposes three standardized Apache Parquet files:

| `result_key` | Object filename | Contents |
|--------------|-----------------|----------|
| `energy_and_peak` | `energy_and_peak.parquet` | Building-level annual and end-use thermal/electric energy consumption and peak demand (public schema of `EnergyAndPeak`). |
| `overheating` | `overheating.parquet` | Building-level indoor thermal discomfort and overheating degree-hour metrics under TMY and 2050 FTMY weather (public schema of `BasicOverheating`). |
| `emissions_by_building` | `emissions_by_building.parquet` | Building-level operational greenhouse gas emissions after applying regional grid and fuel emission factors. |

Key structure:

```text
s3://<bucket>/globi-public/<ISO>/<City>/<weather>/<Scenario>/<output_version>/<filename>
```

Concrete example (4 scenarios × 3 files = 12 Parquet objects for Lisbon):

```text
s3://<bucket>/globi-public/PT/Lisbon/tmy/Baseline/v001/energy_and_peak.parquet
s3://<bucket>/globi-public/PT/Lisbon/tmy/Baseline/v001/overheating.parquet
s3://<bucket>/globi-public/PT/Lisbon/tmy/Baseline/v001/emissions_by_building.parquet
s3://<bucket>/globi-public/PT/Lisbon/tmy/Retrofit/v001/*.parquet
s3://<bucket>/globi-public/PT/Lisbon/ftmy/Baseline/v001/*.parquet
s3://<bucket>/globi-public/PT/Lisbon/ftmy/Retrofit/v001/*.parquet
```

All 28 experiment paths are indexed in [`outputs/index.yml`](../outputs/index.yml).

---

## Accessing the data (no AWS account required)

Public objects are served with `RequesterPays: false` and allow anonymous `s3:GetObject` and `s3:ListBucket` requests.

### 1. AWS CLI

List available regions and download an input bundle or result file without credentials:

```bash
# List regional input bundles
aws s3 ls s3://<bucket>/globi-inputs/ --no-sign-request

# Download the complete Lisbon v001 input bundle (~5 MB)
aws s3 sync \
  s3://<bucket>/globi-inputs/PT/Lisbon/v001/ \
  ./Lisbon-v001 \
  --no-sign-request

# Download one experiment's Parquet tables
aws s3 sync \
  s3://<bucket>/globi-public/IN/Ahmedabad/ftmy/CC/v001/ \
  ./Ahmedabad-ftmy-CC \
  --no-sign-request
```

### 2. Python (`pyarrow` / `pandas` / `s3fs`)

Query Parquet files directly from S3 using anonymous access:

```python
import pyarrow.dataset as ds
from pyarrow import fs

s3 = fs.S3FileSystem(anonymous=True, region="us-east-1")  # region confirmed at onboarding

uri = "<bucket>/globi-public/PT/Lisbon/tmy/Baseline/v001/energy_and_peak.parquet"
table = ds.dataset(uri, filesystem=s3, format="parquet").to_table()
df = table.to_pandas()
print(df.head())
```

### 3. DuckDB (SQL over S3 Parquet, zero local download)

Compare baseline vs. retrofit emissions across an entire city in SQL:

```sql
INSTALL httpfs;
LOAD httpfs;
SET s3_region = 'us-east-1';

SELECT
  'Baseline' AS scenario,
  COUNT(*)   AS n_buildings
FROM read_parquet('s3://<bucket>/globi-public/PT/Lisbon/tmy/Baseline/v001/emissions_by_building.parquet')
UNION ALL
SELECT
  'Retrofit' AS scenario,
  COUNT(*)   AS n_buildings
FROM read_parquet('s3://<bucket>/globi-public/PT/Lisbon/tmy/Retrofit/v001/emissions_by_building.parquet');
```

### 4. `globi-data` CLI (version-resolved downloads + integrity checks)

The [`globi-data`](https://github.com/MITSustainableDesignLab/globi-data) Python CLI resolves `CURRENT.yml` automatically so workflows do not hardcode S3 paths:

```bash
uv run globi-data inputs list
uv run globi-data inputs show Lisbon
uv run globi-data outputs download PT/Lisbon/tmy/Baseline --dest ./results
uv run globi-data status   # checks whether any output version is stale relative to inputs
```

---

## Versioning, immutability, and provenance

Every simulation output is cryptographically linked to its input bundle:

1. **Per-file and bundle hashes (`input-version.yml`)** — Every file inside `globi-inputs/<ISO>/<Partner>/vNNN/` has its byte count and `sha256` recorded, rolled up into a deterministic `bundle_sha256`.
2. **Output-to-input pinning (`output-version.yml`)** — Each experiment's manifest records `provenance.input.manifest_path`, `bundle_sha256`, and external `gis_file.sha256`, plus S3 object metadata (`bytes`, `sha256`, `etag`) for all three Parquet files.
3. **Automatic staleness tracking (`outputs/STATUS.md`)** — When a new `simulation-affecting` input version (`v002`) is promoted in `CURRENT.yml`, `globi-data status` flags downstream results that were computed against `v001`. Documentation-only changes (`impact: metadata-only`) do not mark runs stale.
4. **Non-destructive retractions** — Published `vNNN/` prefixes are never mutated or deleted in place. If an error is discovered, `versions.yml` marks the version `retracted` with a note pointing to its replacement, preserving reproducibility for prior citations.

---

## Update cadence and lifecycle

- **Input bundles (`globi-inputs/`):** Updated as partner cities refine building archetypes, HVAC libraries, or weather projections, and as new cities join GloBI.
- **Processed results (`globi-public/`):** Updated when new scenarios are simulated or when existing experiments are re-run against newly published input versions.
- **Retention:** Historical `vNNN/` prefixes remain readable indefinitely to keep published papers and downstream benchmarks reproducible.

---

## Onboarding & bucket operations checklist (MIT SDL operators)

1. **Provision bucket:** Create the dedicated AWS Open Data Program S3 bucket in the agreed region (`RequesterPays` disabled).
2. **Scope public bucket policy** strictly to the two public prefixes (`s3:ListBucket` with `s3:prefix` condition on `globi-inputs/*` and `globi-public/*`, and anonymous `s3:GetObject` on `arn:aws:s3:::<bucket>/globi-inputs/*` and `arn:aws:s3:::<bucket>/globi-public/*`).
3. **Sync input bundles:**
   ```bash
   for dir in inputs/*/*/v001; do
     aws s3 sync "$dir/" "s3://<bucket>/globi-${dir}/" --exclude ".DS_Store"
   done
   ```
4. **Upload processed Parquet outputs** for all 28 experiments (84 `.parquet` objects) under `s3://<bucket>/globi-public/`.
5. **Publish bucket landing page:** Upload a static `index.html` / `README.html` at the bucket root linking to this document and the Registry entry (per the AWS Open Data Provider Handbook).
6. **Finalize configuration & verify:** Update [`public_storage.yml`](../public_storage.yml), re-record or update output manifests so `s3_uri`, `bytes`, `etag`, and `sha256` reflect live objects, and run:
   ```bash
   uv run globi-data inputs verify --all
   uv run globi-data outputs verify --all
   uv run globi-data check
   ```
7. **Submit Registry PR:** Replace `TBD` placeholders in `datasets/globi-regional-building-data.yaml` and open the PR against [`awslabs/open-data-registry`](https://github.com/awslabs/open-data-registry).

---

## License, citation, and contact

- **License:** Metadata, manifests, schemas, and `globi-data` tooling are released under the [MIT License](../LICENSE). Underlying municipal or partner building attributes may carry source attribution terms documented in each region's `vNNN/README.md`; raw partner GIS footprints are not distributed in this bucket.
- **Citation:** Please cite the GloBI project (MIT Sustainable Design Lab) and reference *GloBI Regional Building Inventory Data* via the Registry of Open Data on AWS (`https://registry.opendata.aws/globi-regional-building-data`). A peer-reviewed publication DOI will be added upon publication.
- **Contact & support:** MIT Sustainable Design Lab — `sd-lab-admin@mit.edu` (or open an issue on [`MITSustainableDesignLab/globi-data`](https://github.com/MITSustainableDesignLab/globi-data/issues); security reports per [SECURITY.md](../SECURITY.md)).