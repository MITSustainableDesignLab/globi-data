# Cambridge_UK — input v001

Initial import of Cambridge_UK inputs from globi-partners-data.

- **Created:** 2026-08-24T16:22:11Z
- **Impact:** `simulation-affecting`  (changes here can change simulation results)
- **Assembled from:** `globi-partners-data` @ `a12d78a6` (`data/partners/Cambridge_UK`)

> This folder is frozen. To change anything, create a new version — do not edit
> these files in place.

## Files

| File | Size | What it is |
|---|---|---|
| `artifacts.yml` | 386 B | Points at the other input files. |
| `component-map.yml` | 3.0 KB | Maps building attributes to envelope, HVAC and DHW components. |
| `components-lib.db` | 667.6 KB | Component and material library (SQLite). |
| `gis-preprocessor.yml` | 369 B | Rules for cleaning the building geometry. |
| `manifest.yml` | 190 B | Top-level description of the experiment (name, scenario). |
| `overheating-config.yml` | 292 B | Temperature thresholds for the overheating analysis. |
| `semantic-fields.yml` | 1.6 KB | Declares the building attributes and their allowed values. |

## Not stored here

These files are too large for this repository. Their fingerprints are recorded
so results stay traceable, but the bytes live elsewhere.

| File | Size | Where it lives | Why |
|---|---|---|---|
| `buildings.geojson` | 48.7 MB | `globi-partners-data` / `data/partners/Cambridge_UK/buildings.geojson` | 49 MB of geometry - kept under git-lfs in globi-partners-data where it already lives. |

## Fingerprint

- `bundle_sha256`: `37793b20fd82d9959ea85ae0437a5fae044d12611ad519719051ae27166b9d0c`

Verify this folder yourself with `globi-data inputs verify Cambridge_UK --version v001`.
