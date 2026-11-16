# Sao_Paulo — input v001

Initial import of Sao_Paulo inputs from globi-partners-data.

- **Created:** 2026-08-24T16:26:22Z
- **Impact:** `simulation-affecting`  (changes here can change simulation results)
- **Assembled from:** `globi-partners-data` @ `a12d78a6` (`data/partners/Sao_Paulo`)

> This folder is frozen. To change anything, create a new version — do not edit
> these files in place.

## Files

| File | Size | What it is |
|---|---|---|
| `artifacts.yml` | 379 B | Points at the other input files. |
| `component-map.yml` | 394 B | Maps building attributes to envelope, HVAC and DHW components. |
| `components-lib.db` | 426.0 KB | Component and material library (SQLite). |
| `gis-preprocessor.yml` | 387 B | Rules for cleaning the building geometry. |
| `hourly-data-config.yml` | 98 B | Which hourly variables to record. |
| `manifest.yml` | 230 B | Top-level description of the experiment (name, scenario). |
| `overheating-config.yml` | 292 B | Temperature thresholds for the overheating analysis. |
| `semantic-fields.yml` | 2.0 KB | Declares the building attributes and their allowed values. |
| `weather/BRA_SP_Guaratingueta.AP.837080_TMYx.2009-2023.ddy` | 13.3 KB | Current climate — design-day conditions. |
| `weather/BRA_SP_Guaratingueta.AP.837080_TMYx.2009-2023.epw` | 1.6 MB | Current climate — hourly weather data. |
| `weather/BRA_SP_Guaratingueta.AP.837080_TMYx.2009-2023.zip` | 284.5 KB | Current climate — packaged weather files. |
| `weather_ftmy/Guaratingueta_BRA_ftmy_2050_ssp245_CanESM5.ddy` | 13.3 KB | Future climate (2050) — design-day conditions. |
| `weather_ftmy/Guaratingueta_BRA_ftmy_2050_ssp245_CanESM5.epw` | 1.7 MB | Future climate (2050) — hourly weather data. |
| `weather_ftmy/Guaratingueta_BRA_ftmy_2050_ssp245_CanESM5.zip` | 302.6 KB | Future climate (2050) — packaged weather files. |

## Not stored here

These files are too large for this repository. Their fingerprints are recorded
so results stay traceable, but the bytes live elsewhere.

| File | Size | Where it lives | Why |
|---|---|---|---|
| `buildings.geojson` | 7.5 MB | `globi-partners-data` / `data/partners/Sao_Paulo/buildings.geojson` | 7 MB of geometry - kept under git-lfs in globi-partners-data where it already lives. |

## Not carried over from the source repo

Present in the source directory but deliberately excluded, so nothing was
dropped silently:

- `Guaratingueta_BRA_ftmy_2050_ssp245_CanESM5.epw.txt - FTMY build intermediate; the real .epw is under weather_ftmy/`
- `components-lib-old.db - superseded backup of components-lib.db`

## Fingerprint

- `bundle_sha256`: `1dd5337fb5084dc13005d19e6733138b66e2dc359b850c45e927dffe5936e665`

Verify this folder yourself with `globi-data inputs verify Sao_Paulo --version v001`.
