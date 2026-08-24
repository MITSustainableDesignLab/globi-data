# Nairobi — input v001

Initial import of Nairobi inputs from globi-partners-data.

- **Created:** 2026-08-24T16:22:13Z
- **Impact:** `simulation-affecting`  (changes here can change simulation results)
- **Assembled from:** `globi-partners-data` @ `a12d78a6` (`data/partners/Nairobi`)

> This folder is frozen. To change anything, create a new version — do not edit
> these files in place.

## Files

| File | Size | What it is |
|---|---|---|
| `artifacts.yml` | 371 B | Points at the other input files. |
| `component-map.yaml` | 285 B | Maps building attributes to envelope, HVAC and DHW components. |
| `components-lib.db` | 462.8 KB | Component and material library (SQLite). |
| `gis-preprocessor.yml` | 387 B | Rules for cleaning the building geometry. |
| `hourly-data-config.yml` | 98 B | Which hourly variables to record. |
| `manifest.yml` | 173 B | Top-level description of the experiment (name, scenario). |
| `overheating-config.yml` | 292 B | Temperature thresholds for the overheating analysis. |
| `semantic-fields.yaml` | 523 B | Declares the building attributes and their allowed values. |
| `weather/KEN_NB_Nairobi-Kenyatta.Intl.AP.637400_TMYx.2009-2023.ddy` | 183.9 KB | Current climate — design-day conditions. |
| `weather/KEN_NB_Nairobi-Kenyatta.Intl.AP.637400_TMYx.2009-2023.epw` | 1.6 MB | Current climate — hourly weather data. |
| `weather/KEN_NB_Nairobi-Kenyatta.Intl.AP.637400_TMYx.2009-2023.zip` | 269.8 KB | Current climate — packaged weather files. |
| `weather_ftmy/Nairobi_KEN_ftmy_2050_ssp245_CanESM5.ddy` | 183.9 KB | Future climate (2050) — design-day conditions. |
| `weather_ftmy/Nairobi_KEN_ftmy_2050_ssp245_CanESM5.epw` | 1.7 MB | Future climate (2050) — hourly weather data. |
| `weather_ftmy/Nairobi_KEN_ftmy_2050_ssp245_CanESM5.zip` | 288.2 KB | Future climate (2050) — packaged weather files. |

## Not stored here

These files are too large for this repository. Their fingerprints are recorded
so results stay traceable, but the bytes live elsewhere.

| File | Size | Where it lives | Why |
|---|---|---|---|
| `buildings.geojson` | 43.8 MB | `globi-partners-data` / `data/partners/Nairobi/buildings.geojson` | 44 MB of geometry - kept under git-lfs in globi-partners-data where it already lives. |

## Not carried over from the source repo

Present in the source directory but deliberately excluded, so nothing was
dropped silently:

- `Nairobi_KEN_ftmy_2050_ssp245_CanESM5.epw.txt - FTMY build intermediate; the real .epw is under weather_ftmy/`
- `components-lib-og.db - superseded backup of components-lib.db`
- `manifest_noAC.yml - redundant scenario manifest; manifest.yml is the one carried`

## Fingerprint

- `bundle_sha256`: `1612a3709614df96e89bd99da8fc47b40ac93eb6a091b797415431826d2d2e86`

Verify this folder yourself with `globi-data inputs verify Nairobi --version v001`.
