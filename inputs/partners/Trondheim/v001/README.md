# Trondheim — input v001

Initial import of Trondheim inputs from globi-partners-data.

- **Created:** 2026-08-24T16:26:23Z
- **Impact:** `simulation-affecting`  (changes here can change simulation results)
- **Assembled from:** `globi-partners-data` @ `a12d78a6` (`data/partners/Trondheim`)

> This folder is frozen. To change anything, create a new version — do not edit
> these files in place.

## Files

| File | Size | What it is |
|---|---|---|
| `artifacts.yml` | 374 B | Points at the other input files. |
| `component-map.yaml` | 412 B | Maps building attributes to envelope, HVAC and DHW components. |
| `components-lib.db` | 647.2 KB | Component and material library (SQLite). |
| `gis-preprocessor.yml` | 387 B | Rules for cleaning the building geometry. |
| `manifest_HighEfficiency.yml` | 187 B | Top-level description of the experiment (name, scenario). |
| `manifest_LowEfficiency.yml` | 186 B |  |
| `overheating-config.yml` | 292 B | Temperature thresholds for the overheating analysis. |
| `semantic-fields.yaml` | 641 B | Declares the building attributes and their allowed values. |
| `weather/NOR_TR_Trondheim.AP-Vaernes.012710_TMYx.2009-2023.ddy` | 183.0 KB | Current climate — design-day conditions. |
| `weather/NOR_TR_Trondheim.AP-Vaernes.012710_TMYx.2009-2023.epw` | 1.6 MB | Current climate — hourly weather data. |
| `weather/NOR_TR_Trondheim.AP-Vaernes.012710_TMYx.2009-2023.zip` | 295.3 KB | Current climate — packaged weather files. |
| `weather_ftmy/Trondheim_NOR_ftmy_2050_ssp126_CanESM5.ddy` | 183.0 KB | Future climate (2050) — design-day conditions. |
| `weather_ftmy/Trondheim_NOR_ftmy_2050_ssp126_CanESM5.epw` | 1.7 MB | Future climate (2050) — hourly weather data. |
| `weather_ftmy/Trondheim_NOR_ftmy_2050_ssp126_CanESM5.zip` | 327.7 KB | Future climate (2050) — packaged weather files. |

## Not stored here

These files are too large for this repository. Their fingerprints are recorded
so results stay traceable, but the bytes live elsewhere.

| File | Size | Where it lives | Why |
|---|---|---|---|
| `buildings.geojson` | 1.2 MB | `globi-partners-data` / `data/partners/Trondheim/buildings.geojson` | 1 MB of geometry - kept under git-lfs in globi-partners-data where it already lives. |

## Not carried over from the source repo

Present in the source directory but deliberately excluded, so nothing was
dropped silently:

- `Trondheim_NOR_ftmy_2050_ssp126_CanESM5.epw.txt - FTMY build intermediate; the real .epw is under weather_ftmy/`

## Warnings

- No plain manifest.yml; carrying manifest_HighEfficiency.yml, manifest_LowEfficiency.yml and naming manifest_HighEfficiency.yml as the experiment manifest. The scenario actually run is set by experiments.yaml, not by this file. Also carried: manifest_LowEfficiency.yml.

## Fingerprint

- `bundle_sha256`: `00ce4d0038514c9b3179804ad481170876993dc85437b11e26414863c660e20d`

Verify this folder yourself with `globi-data inputs verify Trondheim --version v001`.
