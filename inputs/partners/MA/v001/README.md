# MA — input v001

Initial import of MA inputs from globi-partners-data.

- **Created:** 2026-08-24T16:22:12Z
- **Impact:** `simulation-affecting`  (changes here can change simulation results)
- **Assembled from:** `globi-partners-data` @ `a12d78a6` (`data/partners/MA`)

> This folder is frozen. To change anything, create a new version — do not edit
> these files in place.

## Files

| File | Size | What it is |
|---|---|---|
| `component-map.yml` | 3.3 KB | Maps building attributes to envelope, HVAC and DHW components. |
| `components-lib.db` | 569.3 KB | Component and material library (SQLite). |
| `context-small.parquet` | 2.7 MB | Pre-processed building context table. |
| `overheating-config.yml` | 292 B | Temperature thresholds for the overheating analysis. |
| `runs/ma/allocation-manifest.csv` | 1.5 MB | Record of how a previous batch of runs was allocated. |
| `semantic-fields.yml` | 2.2 KB | Declares the building attributes and their allowed values. |
| `tl_2024_25_tract.zip` | 4.5 MB |  |
| `weather-lookup.yml` | 124.2 KB | Maps each area to its weather station. |
| `weather/Boston/weather/USA_MA_Boston-Logan.Intl.AP.725090_TMYx.2009-2023.ddy` | 183.0 KB | Current climate — design-day conditions. |
| `weather/Boston/weather/USA_MA_Boston-Logan.Intl.AP.725090_TMYx.2009-2023.epw` | 1.6 MB | Current climate — hourly weather data. |
| `weather/Boston/weather/USA_MA_Boston-Logan.Intl.AP.725090_TMYx.2009-2023.zip` | 278.8 KB | Current climate — packaged weather files. |
| `weather/Boston/weather_ftmy/Boston__MA__USA_ftmy_2050_ssp245_CanESM5.ddy` | 183.0 KB | Future climate (2050) — design-day conditions. |
| `weather/Boston/weather_ftmy/Boston__MA__USA_ftmy_2050_ssp245_CanESM5.epw` | 1.6 MB | Future climate (2050) — hourly weather data. |
| `weather/Boston/weather_ftmy/Boston__MA__USA_ftmy_2050_ssp245_CanESM5.zip` | 280.1 KB | Future climate (2050) — packaged weather files. |
| `weather/Pittsfield/weather/USA_MA_Pittsfield.Muni.AP.744104_TMYx.2009-2023.ddy` | 182.6 KB | Current climate — design-day conditions. |
| `weather/Pittsfield/weather/USA_MA_Pittsfield.Muni.AP.744104_TMYx.2009-2023.epw` | 1.6 MB | Current climate — hourly weather data. |
| `weather/Pittsfield/weather/USA_MA_Pittsfield.Muni.AP.744104_TMYx.2009-2023.zip` | 292.1 KB | Current climate — packaged weather files. |
| `weather/Pittsfield/weather_ftmy/Pittsfield_MA_ftmy_2050_ssp245_CanESM5.ddy` | 182.6 KB | Future climate (2050) — design-day conditions. |
| `weather/Pittsfield/weather_ftmy/Pittsfield_MA_ftmy_2050_ssp245_CanESM5.epw` | 1.7 MB | Future climate (2050) — hourly weather data. |
| `weather/Pittsfield/weather_ftmy/Pittsfield_MA_ftmy_2050_ssp245_CanESM5.zip` | 310.3 KB | Future climate (2050) — packaged weather files. |
| `weather/Worcester/weather/USA_MA_Worcester.Rgnl.AP.725100_TMYx.2009-2023.ddy` | 182.3 KB | Current climate — design-day conditions. |
| `weather/Worcester/weather/USA_MA_Worcester.Rgnl.AP.725100_TMYx.2009-2023.epw` | 1.6 MB | Current climate — hourly weather data. |
| `weather/Worcester/weather/USA_MA_Worcester.Rgnl.AP.725100_TMYx.2009-2023.zip` | 284.0 KB | Current climate — packaged weather files. |
| `weather/Worcester/weather_ftmy/Worcester_MA_ftmy_2050_ssp245_CanESM5.ddy` | 182.3 KB | Future climate (2050) — design-day conditions. |
| `weather/Worcester/weather_ftmy/Worcester_MA_ftmy_2050_ssp245_CanESM5.epw` | 1.7 MB | Future climate (2050) — hourly weather data. |
| `weather/Worcester/weather_ftmy/Worcester_MA_ftmy_2050_ssp245_CanESM5.zip` | 306.4 KB | Future climate (2050) — packaged weather files. |

## Not carried over from the source repo

Present in the source directory but deliberately excluded, so nothing was
dropped silently:

- `weather/Boston/Boston__MA__USA_ftmy_2050_ssp245_CanESM5.epw.txt - FTMY build intermediate; the real .epw is under weather_ftmy/`
- `weather/Pittsfield/Pittsfield_MA_ftmy_2050_ssp245_CanESM5.epw.txt - FTMY build intermediate; the real .epw is under weather_ftmy/`
- `weather/Worcester/Worcester_MA_ftmy_2050_ssp245_CanESM5.epw.txt - FTMY build intermediate; the real .epw is under weather_ftmy/`

## Fingerprint

- `bundle_sha256`: `d53a3ab202de33c5d25f132c40302f058776efcad7ec5e5d572b25d0dde54ebb`

Verify this folder yourself with `globi-data inputs verify MA --version v001`.
