# Manchester — input v001

Initial import of Manchester inputs from globi-partners-data.

- **Created:** 2026-08-24T16:22:13Z
- **Impact:** `simulation-affecting`  (changes here can change simulation results)
- **Assembled from:** `globi-partners-data` @ `a12d78a6` (`data/partners/Manchester`)

> This folder is frozen. To change anything, create a new version — do not edit
> these files in place.

## Files

| File | Size | What it is |
|---|---|---|
| `artifacts.yml` | 383 B | Points at the other input files. |
| `component-map-manchester-dsr.yml` | 1.9 KB |  |
| `component-map.yaml` | 746 B | Maps building attributes to envelope, HVAC and DHW components. |
| `components-lib.db` | 2.8 MB | Component and material library (SQLite). |
| `gis-preprocessor.yml` | 387 B | Rules for cleaning the building geometry. |
| `manifest.yml` | 161 B | Top-level description of the experiment (name, scenario). |
| `overheating-config.yml` | 292 B | Temperature thresholds for the overheating analysis. |
| `semantic-fields-manchester-dsr.yml` | 4.7 KB |  |
| `semantic-fields.yaml` | 4.8 KB | Declares the building attributes and their allowed values. |
| `weather/GBR_ENG_Manchester.AP.033340_TMYx.2009-2023.ddy` | 181.5 KB | Current climate — design-day conditions. |
| `weather/GBR_ENG_Manchester.AP.033340_TMYx.2009-2023.epw` | 1.6 MB | Current climate — hourly weather data. |
| `weather/GBR_ENG_Manchester.AP.033340_TMYx.2009-2023.zip` | 262.3 KB | Current climate — packaged weather files. |
| `weather_ftmy/Manchester_ENG_ftmy_2050_ssp126_CanESM5.ddy` | 181.5 KB | Future climate (2050) — design-day conditions. |
| `weather_ftmy/Manchester_ENG_ftmy_2050_ssp126_CanESM5.epw` | 1.7 MB | Future climate (2050) — hourly weather data. |
| `weather_ftmy/Manchester_ENG_ftmy_2050_ssp126_CanESM5.zip` | 276.3 KB | Future climate (2050) — packaged weather files. |

## Not stored here

These files are too large for this repository. Their fingerprints are recorded
so results stay traceable, but the bytes live elsewhere.

| File | Size | Where it lives | Why |
|---|---|---|---|
| `buildings.geojson` | 8.1 MB | `globi-partners-data` / `data/partners/Manchester/buildings.geojson` | 8 MB of geometry - kept under git-lfs in globi-partners-data where it already lives. |

## Not carried over from the source repo

Present in the source directory but deliberately excluded, so nothing was
dropped silently:

- `GloBI_manchester.db - not a recognised bundle file`
- `GloBI_manchester.xlsx - source spreadsheet; the simulation reads the .db built from it`
- `Manchester_ENG_ftmy_2050_ssp126_CanESM5.epw.txt - FTMY build intermediate; the real .epw is under weather_ftmy/`
- `manchester_floors_DSR.geojson - GIS geometry is not stored in this repo`
- `manchester_floors_No_DSR.geojson - GIS geometry is not stored in this repo`

## Fingerprint

- `bundle_sha256`: `e5ff2749ec5e7beaf381337b96a3a68e9aef4e3ae43bf253dea44de44df42352`

Verify this folder yourself with `globi-data inputs verify Manchester --version v001`.
