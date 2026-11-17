# Public result products

Simulation outputs checked into this repository are **pointers to S3**, not the parquet files themselves.

For the [AWS Open Data Registry](https://registry.opendata.aws), see [PUBLIC-DATA.md](PUBLIC-DATA.md) (inputs under `globi-inputs/` and results under `globi-public/`) and the draft entry in [`registry/draft/`](../registry/draft/).

## What downloaders get

Each regional experiment (`<ISO>/<City>/<weather>/<scenario>`) exposes these processed files:

| `result_key` | Object | What it is |
|---|---|---|
| `energy_and_peak` | `energy_and_peak.parquet` | Energy use and peak demand for each building. Public form of `EnergyAndPeak`. |
| `overheating` | `overheating.parquet` | Overheating for each building. Public form of `BasicOverheating`. |
| `emissions_by_building` | `emissions_by_building.parquet` | Emissions by building after regional emission factors are applied. |

`emissions_by_building` is produced in `globi-partners-data` by `scripts/run_emissions_postprocessing.py`. Energy, peak, and overheating are the same simulation outputs as `EnergyAndPeak` and `BasicOverheating`, published here under the public names above.

Raw scythe objects on the private `globi-partners` prefix (`final/*.pq`) are **not** published. Downloaders use the public files in this table.

## S3 layout

Configurable in [`public_storage.yml`](../public_storage.yml). Default shape:

```text
s3://<bucket>/<outputs_prefix>/<experiment>/<output_version>/<filename>
```

Example:

```text
s3://ml-for-bem/globi-public/IN/Ahmedabad/tmy/BAU/v001/energy_and_peak.parquet
```

where `experiment` matches the repo path under `outputs/runs/`.

## Operator checklist (bucket)

- Create the bucket/prefix and upload `energy_and_peak.parquet`, `overheating.parquet`, and `emissions_by_building.parquet` for every experiment (28 experiments).
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