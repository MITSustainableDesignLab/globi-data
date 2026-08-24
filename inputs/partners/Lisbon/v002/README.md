# Lisbon — input v002

mutate db

- **Created:** 2026-08-24T16:23:28Z
- **Impact:** `simulation-affecting`  (changes here can change simulation results)
- **Previous version:** [`v001`](../v001/)
- **Assembled from:** `globi-partners-data` @ `a12d78a6` (`data/partners/Lisbon`)

> This folder is frozen. To change anything, create a new version — do not edit
> these files in place.

## Files

| File | Size | What it is |
|---|---|---|
| `artifacts.yml` | 362 B | Points at the other input files. |
| `component-map.yaml` | 1.6 KB | Maps building attributes to envelope, HVAC and DHW components. |
| `components-lib.db` | 888.8 KB | Component and material library (SQLite). |
| `gis-preprocessor.yml` | 387 B | Rules for cleaning the building geometry. |
| `manifest.yml` | 172 B | Top-level description of the experiment (name, scenario). |
| `semantic-fields.yaml` | 1.8 KB | Declares the building attributes and their allowed values. |
| `weather/PRT_LB_Lisboa.Portela.AP.085360_TMYx.2009-2023.ddy` | 182.3 KB | Current climate — design-day conditions. |
| `weather/PRT_LB_Lisboa.Portela.AP.085360_TMYx.2009-2023.epw` | 1.6 MB | Current climate — hourly weather data. |
| `weather/PRT_LB_Lisboa.Portela.AP.085360_TMYx.2009-2023.zip` | 257.4 KB | Current climate — packaged weather files. |
| `weather_ftmy/Lisbon_POR_ftmy_2050_ssp245_CanESM5.ddy` | 182.3 KB | Future climate (2050) — design-day conditions. |
| `weather_ftmy/Lisbon_POR_ftmy_2050_ssp245_CanESM5.epw` | 1.7 MB | Future climate (2050) — hourly weather data. |
| `weather_ftmy/Lisbon_POR_ftmy_2050_ssp245_CanESM5.zip` | 266.3 KB | Future climate (2050) — packaged weather files. |

## Not stored here

These files are too large for this repository. Their fingerprints are recorded
so results stay traceable, but the bytes live elsewhere.

| File | Size | Where it lives | Why |
|---|---|---|---|
| `buildings.geojson` | 1.1 GB | `globi-partners-data` / `data/partners/Lisbon/buildings.geojson` | 1129 MB of geometry - kept under git-lfs in globi-partners-data where it already lives. |

## What changed

| File | Change | Note |
|---|---|---|
| `README.md` | removed |  |
| `components-lib.db` | modified |  |

## Not carried over from the source repo

Present in the source directory but deliberately excluded, so nothing was
dropped silently:

- `.DS_Store - macOS metadata`
- `Lisbon_POR_ftmy_2050_ssp245_CanESM5.epw.txt - FTMY build intermediate; the real .epw is under weather_ftmy/`

## Fingerprint

- `bundle_sha256`: `3079f5379d817c7509607906209dd12262388fde70a814954847a572779c0bef`

Verify this folder yourself with `globi-data inputs verify Lisbon --version v002`.
