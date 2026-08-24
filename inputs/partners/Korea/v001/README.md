# Korea — input v001

Initial import of Korea inputs from globi-partners-data.

- **Created:** 2026-08-24T16:22:12Z
- **Impact:** `simulation-affecting`  (changes here can change simulation results)
- **Assembled from:** `globi-partners-data` @ `a12d78a6` (`data/partners/Korea`)

> This folder is frozen. To change anything, create a new version — do not edit
> these files in place.

## Files

| File | Size | What it is |
|---|---|---|
| `KoBI_Template_260126_ver2.db` | 352.3 KB |  |
| `KoBI_Template_260126_ver2.xlsx` | 1.9 MB |  |
| `buildings.parquet` | 2.1 MB |  |
| `component-map.yml` | 3.5 KB | Maps building attributes to envelope, HVAC and DHW components. |
| `component-map_v1.yml` | 3.6 KB |  |
| `components-lib.db` | 864.3 KB | Component and material library (SQLite). |
| `korea_template-internal-mass.db` | 921.6 KB |  |
| `korea_template.db` | 983.0 KB |  |
| `korea_template.xlsx` | 1.9 MB |  |
| `korea_template_v2.db` | 983.0 KB |  |
| `semantic-fields-KR-res.yaml` | 2.7 KB |  |
| `semantic-fields.yaml` | 2.9 KB | Declares the building attributes and their allowed values. |

## Not stored here

These files are too large for this repository. Their fingerprints are recorded
so results stay traceable, but the bytes live elsewhere.

| File | Size | Where it lives | Why |
|---|---|---|---|
| `korea_sample.geojson` | 2.0 MB | `globi-partners-data` / `data/partners/Korea/korea_sample.geojson` | 2 MB of geometry - kept under git-lfs in globi-partners-data where it already lives. |

## Fingerprint

- `bundle_sha256`: `73142d0e238baaede6a1ebb653460adc9b238ef85395e69280fc50bbbe168bdf`

Verify this folder yourself with `globi-data inputs verify Korea --version v001`.
