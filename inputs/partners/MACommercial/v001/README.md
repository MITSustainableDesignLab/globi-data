# MACommercial — input v001

Initial import of MACommercial inputs from globi-partners-data.

- **Created:** 2026-08-24T16:22:13Z
- **Impact:** `simulation-affecting`  (changes here can change simulation results)
- **Assembled from:** `globi-partners-data` @ `a12d78a6` (`data/partners/MACommercial`)

> This folder is frozen. To change anything, create a new version — do not edit
> these files in place.

## Files

| File | Size | What it is |
|---|---|---|
| `artifacts.yml` | 407 B | Points at the other input files. |
| `component-map.yaml` | 841 B | Maps building attributes to envelope, HVAC and DHW components. |
| `components.db` | 856.1 KB | Component and material library (SQLite). |
| `gis-preprocessor.yml` | 387 B | Rules for cleaning the building geometry. |
| `hourly-data-config.yml` | 109 B | Which hourly variables to record. |
| `manifest.yml` | 197 B | Top-level description of the experiment (name, scenario). |
| `semantic-fields.yaml` | 2.2 KB | Declares the building attributes and their allowed values. |

## Not stored here

These files are too large for this repository. Their fingerprints are recorded
so results stay traceable, but the bytes live elsewhere.

| File | Size | Where it lives | Why |
|---|---|---|---|
| `buildings.geojson` | 239.0 MB | `globi-partners-data` / `data/partners/MACommercial/buildings.geojson` | 239 MB of geometry - kept under git-lfs in globi-partners-data where it already lives. |

## Fingerprint

- `bundle_sha256`: `bfa4ea0679f2a7dd8fa2d0220441707f8c7e026d26383302ec1910f8a49a0ac4`

Verify this folder yourself with `globi-data inputs verify MACommercial --version v001`.
