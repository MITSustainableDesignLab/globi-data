# Public result products

Simulation outputs checked into this repository are **pointers to S3**, not the parquet files themselves.

## What downloaders get

Each regional experiment (`<ISO>/<City>/<weather>/<scenario>`) exposes one processed file:

| `result_key` | Object |
|---|---|
| `emissions_by_building` | `emissions_by_building.parquet` |

The file is produced in `globi-partners-data` by `scripts/run_emissions_postprocessing.py` from the private scythe run tree. It is the public-facing product: emissions by building after regional emission factors are applied.

Raw scythe keys (`EnergyAndPeak`, `BasicOverheating`, …) are **not** published. They remain on the private `globi-partners` prefix for internal reprocessing only.

## S3 layout

Configurable in [`public_storage.yml`](../public_storage.yml). Default shape:

```text
s3://<bucket>/<bucket_prefix>/<experiment>/<output_version>/<filename>
```

Example:

```text
s3://ml-for-bem/globi-public/IN/Ahmedabad/tmy/BAU/v001/emissions_by_building.parquet
```

where `experiment` matches the repo path under `outputs/runs/`.

## Operator checklist (bucket)

- Create the bucket/prefix and upload every `emissions_by_building.parquet` (28 experiments).
- Allow anonymous `GetObject` on `globi-public/*` (or document credentialed access).
- Deny or omit public read on `globi-partners/*` raw `final/*.pq`.
- Update `public_storage.yml` if the bucket or prefix differs.
- Run `globi-data outputs verify --all` after upload.

## Recording new versions

After upload, record URIs with a CSV (`experiment`, `result_key`, `s3_uri`) and:

```bash
globi-data outputs record --experiment IN/Ahmedabad/tmy/BAU --from-csv results.csv --summary "..."
```

Or use the launch migration helper once paths are ISO-indexed.