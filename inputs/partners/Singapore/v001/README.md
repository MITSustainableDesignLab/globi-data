# Singapore — input v001

Initial import of Singapore inputs from globi-partners-data.

- **Created:** 2026-08-24T16:26:23Z
- **Impact:** `simulation-affecting`  (changes here can change simulation results)
- **Assembled from:** `globi-partners-data` @ `a12d78a6` (`data/partners/Singapore`)

> This folder is frozen. To change anything, create a new version — do not edit
> these files in place.

## Files

| File | Size | What it is |
|---|---|---|
| `artifacts.yml` | 318 B | Points at the other input files. |
| `component-map.yaml` | 326 B | Maps building attributes to envelope, HVAC and DHW components. |
| `components-lib.db` | 577.5 KB | Component and material library (SQLite). |
| `gis-preprocessor.yml` | 387 B | Rules for cleaning the building geometry. |
| `manifest.yml` | 171 B | Top-level description of the experiment (name, scenario). |
| `overheating-config.yml` | 292 B | Temperature thresholds for the overheating analysis. |
| `semantic-fields.yaml` | 722 B | Declares the building attributes and their allowed values. |
| `weather/SGP_Singapore.486980_IWEC.ddy` | 29.7 KB | Current climate — design-day conditions. |
| `weather/SGP_Singapore.486980_IWEC.epw` | 1.6 MB | Current climate — hourly weather data. |
| `weather/SGP_Singapore.486980_IWEC.zip` | 222.5 KB | Current-climate weather file (stored here). |
| `weather_ftmy/Singapore_ftmy_2050_ssp245_CanESM5.ddy` | 29.7 KB | Future climate (2050) — design-day conditions. |
| `weather_ftmy/Singapore_ftmy_2050_ssp245_CanESM5.epw` | 1.7 MB | Future climate (2050) — hourly weather data. |
| `weather_ftmy/Singapore_ftmy_2050_ssp245_CanESM5.zip` | 241.2 KB | Future climate (2050) — packaged weather files. |

## Not stored here

These files are too large for this repository. Their fingerprints are recorded
so results stay traceable, but the bytes live elsewhere.

| File | Size | Where it lives | Why |
|---|---|---|---|
| `buildings-singapore.geojson` | 147.5 MB | `globi-partners-data` / `data/partners/Singapore/buildings-singapore.geojson` | 147 MB of geometry - kept under git-lfs in globi-partners-data where it already lives. |

## Not carried over from the source repo

Present in the source directory but deliberately excluded, so nothing was
dropped silently:

- `SGP_Singapore-Changi_TMYx_2009-2023_patched.zip - not a recognised bundle file`
- `Singapore_ftmy_2050_ssp245_CanESM5.epw.txt - FTMY build intermediate; the real .epw is under weather_ftmy/`
- `sg_buildings_v5 2.geojson - GIS geometry is not stored in this repo`

## Fingerprint

- `bundle_sha256`: `a73e157857bf6c50456e34b9a3bc71c33d9536719ca5f27039aa94635f59d298`

Verify this folder yourself with `globi-data inputs verify Singapore --version v001`.
