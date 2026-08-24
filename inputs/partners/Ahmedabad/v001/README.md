# Ahmedabad — input v001

Initial import of Ahmedabad inputs from globi-partners-data.

- **Created:** 2026-08-24T16:26:20Z
- **Impact:** `simulation-affecting`  (changes here can change simulation results)
- **Assembled from:** `globi-partners-data` @ `a12d78a6` (`data/partners/Ahmedabad`)

> This folder is frozen. To change anything, create a new version — do not edit
> these files in place.

## Files

| File | Size | What it is |
|---|---|---|
| `artifacts.yml` | 370 B | Points at the other input files. |
| `component-map.yaml` | 343 B | Maps building attributes to envelope, HVAC and DHW components. |
| `components-lib.db` | 507.9 KB | Component and material library (SQLite). |
| `gis-preprocessor.yml` | 387 B | Rules for cleaning the building geometry. |
| `hourly-data-config.yml` | 98 B | Which hourly variables to record. |
| `manifest.yml` | 176 B | Top-level description of the experiment (name, scenario). |
| `overheating-config.yml` | 292 B | Temperature thresholds for the overheating analysis. |
| `semantic-fields.yaml` | 569 B | Declares the building attributes and their allowed values. |
| `weather/IND_GJ_Ahmedabad.Intl.AP.426470_TMYx.2009-2023.ddy` | 182.6 KB | Current climate — design-day conditions. |
| `weather/IND_GJ_Ahmedabad.Intl.AP.426470_TMYx.2009-2023.epw` | 1.6 MB | Current climate — hourly weather data. |
| `weather/IND_GJ_Ahmedabad.Intl.AP.426470_TMYx.2009-2023.zip` | 264.9 KB | Current climate — packaged weather files. |
| `weather_ftmy/Ahmedabad_IND_ftmy_2050_ssp245_CanESM5.ddy` | 182.6 KB | Future climate (2050) — design-day conditions. |
| `weather_ftmy/Ahmedabad_IND_ftmy_2050_ssp245_CanESM5.epw` | 1.7 MB | Future climate (2050) — hourly weather data. |
| `weather_ftmy/Ahmedabad_IND_ftmy_2050_ssp245_CanESM5.zip` | 279.2 KB | Future climate (2050) — packaged weather files. |

## Not stored here

These files are too large for this repository. Their fingerprints are recorded
so results stay traceable, but the bytes live elsewhere.

| File | Size | Where it lives | Why |
|---|---|---|---|
| `buildings.geojson` | 122.2 MB | `globi-partners-data` / `data/partners/Ahmedabad/buildings.geojson` | 122 MB of geometry - kept under git-lfs in globi-partners-data where it already lives. |

## Not carried over from the source repo

Present in the source directory but deliberately excluded, so nothing was
dropped silently:

- `Ahmedabad_IND_ftmy_2050_ssp245_CanESM5.epw.txt - FTMY build intermediate; the real .epw is under weather_ftmy/`
- `components-lib-old.db - superseded backup of components-lib.db`

## Fingerprint

- `bundle_sha256`: `1707a65e325c925e5cb8bfa906f8f017aa84f60cfae9948f41c7c0adb2ad6b80`

Verify this folder yourself with `globi-data inputs verify Ahmedabad --version v001`.
