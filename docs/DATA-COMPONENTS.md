# What makes up a GloBI region

A GloBI region (a "partner") runs from a small set of data components. This
page lists each one, says what it is for, and sets out the **minimum GIS
data** a new region needs. GIS is the one component this repository does not
store.

Every requirement below comes from the preprocessor in `globi-partners-data`
(`packages/globi/src/globi/pipelines/gis.py` and `gis/utils.py`). If this page
and that code disagree, the code is right, so please fix this page.

---

## The components

| # | Component | Role in `globi.roles` | Typical file | Stored here? | Required? |
|---|---|---|---|---|---|
| 1 | Building stock (GIS) | `gis_file` | `buildings.geojson` | **No**: size and sha256 only | Yes |
| 2 | Semantic fields | `semantic_fields_file` | `semantic-fields.yaml` | Yes | Yes |
| 3 | Component library | `db_file` | `components-lib.db` | Yes | Yes |
| 4 | Component map | `component_map_file` | `component-map.yaml` | Yes | Yes |
| 5 | Weather | `epwzip_file` / `epwzip_file_local` | URL or `weather/*.zip` | Yes, or a URL | Yes, though it can be resolved automatically (see below) |
| 6 | GIS preprocessor config | `gis_preprocessor_config` | `gis-preprocessor.yml` | Yes | Yes; code defaults cover missing keys |
| 7 | Experiment manifest | `experiment_manifest` | `manifest.yml` | Yes | Yes, for experiment bundles |
| 8 | File config | `file_config` | `artifacts.yml` | Yes | Yes, for experiment bundles |
| 9 | Future weather | none | `weather_ftmy/*.zip` | Yes | Only for future-climate runs |
| 10 | Overheating config | `overheating_config` | `overheating-config.yml` | Yes | Optional |
| 11 | Hourly output config | none | `hourly-data-config.yml` | Yes | Optional |

### How they fit together

```
 GIS file ──(columns named in)──► semantic fields ──(values select)──► component map
    │                                    │                                   │
    │ footprint, height, ID              │ allowed categories                │ which DB entry
    ▼                                    ▼                                   ▼
 GIS preprocessor ─────────────────► one row per building ◄──────────── component library
    │  (filters, imputes, finds neighbours, assigns weather)
    ▼
 simulation (one EnergyPlus model per building, per scenario)
```

1. **Semantic fields** declare the categorical attributes that describe a
   building in this region, such as `Typology`, `Age_buckets` or `Region`, and
   the values each one may take. The same file also tells the preprocessor
   which GIS columns hold height, floors, ID, WWR, and so on (the `*_col`
   keys).
2. **Component map** chooses, for each part of the model (envelope, occupancy,
   lighting, HVAC, DHW and others), which semantic fields form the lookup key.
3. **Component library** is a SQLite database of constructions, schedules and
   systems, keyed by those lookup values.
4. **GIS** supplies the per-building facts: where the building is, its shape,
   its height, and its semantic field values.
5. **Weather** is an EPW zip. It can be set once for the whole region, set per
   building, or found automatically for each building.

Components 2 to 4 describe *what kinds* of building exist in the region.
Component 1 describes *which* buildings exist. The same archetype files can
serve any GIS file whose columns match them.

---

## GIS: the minimum a region needs

### File-level requirements

| Requirement | Detail | Failure if missing |
|---|---|---|
| Format | Anything `geopandas.read_file` reads (GeoJSON, GeoPackage, Shapefile), or GeoParquet (`.pq`/`.parquet`) | Read error |
| At least one row | Checked after every filtering step | `validate_has_rows` error |
| CRS declared | Must be **EPSG:4326**, **EPSG:3857**, or the exact `cart_crs` in the preprocessor config. Any other CRS is rejected, not reprojected | `GISFileHasNoCRSError` / `GISFileHasUnexpectedCRSError` |
| Geometry type | `Polygon` or `MultiPolygon`. Points and lines are dropped silently | Rows dropped |
| Surrounding buildings included | Neighbours for shading come from **the same file**, within `neighbor_threshold` (default 100 m). A file that holds only the target buildings will simulate them unshaded | No error; results are quietly wrong |

Shapefile note: column names are cut to 10 characters. The preprocessor
matches the cut names back to the names in the semantic fields file, so
`ActualHeig` for `ActualHeight` works.

### Per-building attributes

**Tier 1: required.** Without these the run fails.

| Attribute | Declared in semantic fields as | Type | Rules |
|---|---|---|---|
| Footprint | geometry column | Polygon | Reduced to its minimum rotated rectangle. Area must be 10 to 100,000 m² and edges 3 to 1,000 m (configurable) |
| Building ID | `Building_ID_col` | any; cast to string | Must be present, **non-null and unique**. Not auto-generated, despite a comment in the code saying otherwise |
| Height **or** number of floors | `Height_col` and/or `Num_Floors_col` | numeric | At least one is required (see below) |
| Every semantic field | `Fields[].Name` | categorical or numeric | Column must exist. Every value must appear in `Options`, or fall within `Min`/`Max`. **Nulls are rejected** |

The `scenario` column is the one exception. The preprocessor writes it from
the experiment's scenario, so the GIS file does not need to include it.

How height and floors combine:

| Provided | What happens |
|---|---|
| Height only | Floors = round(height / `f2f_height`); height is then snapped to floors × `f2f_height`. Null heights become `default_num_floors` × `f2f_height` |
| Floors only | Height = floors × `f2f_height`. **Null floor counts become `default_num_floors`** |
| Both | Both are used as given. **Rows with a null in either are dropped**, not imputed |

After this step, buildings outside 3 to 300 m in height or 1 to 125 floors are
dropped. All of these limits are configurable.

So the absolute minimum GIS file has four columns: **geometry, a unique ID,
floors (or height), and one column per semantic field**. A region whose
semantic fields are all constant, such as a single `Region` value, still needs
those columns filled in on every row.

**Tier 2: optional, imputed if absent.** Include these when you have them.

| Attribute | Key | Default if absent or null | Valid range |
|---|---|---|---|
| Window-to-wall ratio | `WWR_col` | `default_wwr` (0.2 in code; partners set 0.3) | 0 to 1 |
| Basement | `Basement_col` | `default_basement` (`none`) | `none`, `unoccupied_unconditioned`, `unoccupied_conditioned`, `occupied_unconditioned`, `occupied_conditioned` |
| Attic | `Attic_col` | `default_attic` (`none`) | same five values |
| Exposed basement fraction | `Exposed_Basement_Frac_col` | `default_exposed_basement_frac` (0.25) | 0 to 1 |
| Weather file | `Weather_File_col` | the region's `epwzip_file`, else the nearest TMYx station within 500 km | URL or path to an EPW zip |

Rows whose values fall outside the valid range are **dropped**, not clamped.

`GFA_col` is accepted in the semantic fields file (Lisbon, Nairobi and
Sao_Paulo set it), but the preprocessor does not read it. Floor area comes from
the footprint rectangle multiplied by the number of floors.

**Tier 3: derived by the preprocessor.** Do not supply these.

Latitude/longitude, the rotated-rectangle footprint, long and short edge
lengths, orientation angle, aspect ratio, neighbour polygons, neighbour heights
and floors, floor-to-floor height, and the `GLOBI_*` file-pointer columns are
all computed. If you supply columns with these names, they may be overwritten.

### What each attribute controls

When deciding what to collect for a new region, this shows where the effort
pays off:

| Attribute | Drives | If it is poor |
|---|---|---|
| Footprint | Floor area, wall area per orientation, building geometry | Wrong energy totals across the board |
| Height / floors | Floor area, stacking, neighbour shading | Totals scale incorrectly |
| Semantic fields | Which archetype (construction, systems, schedules) each building gets | Wrong energy intensity |
| Neighbours | Solar shading | Cooling overestimated in dense areas |
| WWR | Solar gains and conduction | Moderate error; a regional default is usually adequate |
| Basement / attic | Ground and roof boundary conditions | Small error for most stock |

### Where a region's GIS data might come from

These are possible sources for each tier-1 attribute. The current partners use
a mix of them.

| Attribute | Possible sources |
|---|---|
| Footprints | Municipal cadastre, national mapping agency, OpenStreetMap, Microsoft or Google open building footprints, Overture Maps |
| Height / floors | LiDAR-derived heights, cadastre floor counts, OSM `building:levels`/`height`, global height products such as GHSL |
| Typology | Land-use or zoning layers, cadastre use codes, OSM `building=*` tags |
| Age | Cadastre construction year, census tract age distributions assigned to buildings |
| Other semantic fields (income, region, construction type) | Census or administrative boundaries joined spatially |

MA shows a different route. It has no building-level GIS file: it carries a
preprocessed table (`context-small.parquet`) together with census tract
boundaries (`tl_2024_25_tract.zip`). It is a raw bundle that is not connected
to `experiments.yaml`, so it is not a template for the standard pipeline.

---

## Current partners at a glance

The GIS columns each partner's semantic fields file declares:

| Partner | ID | Height | Floors | WWR | Semantic fields in the GIS file |
|---|---|---|---|---|---|
| Ahmedabad | `UNIQUE_ID` | `ActualHeig` | none | none | region, type, age_bracket |
| Lisbon | `building_id` | `height` | `num_storeys` | none | Region, City, Typology, Age_buckets |
| Manchester | `id` | `height` | `floors_in_building` | `wwr` | Region, Typology, Fabric, Windows, Floor_use, Heating, Cooling, Distribution, … |
| Nairobi | `id` | `height` | `num_storeys` | none | region, type |
| Sao_Paulo | `id` | `height` | `num_storeys` | `WWR` | region, typology, income |
| Singapore | `id` | `height` | `building_levels` | none | Region, typology |
| Trondheim | `id` | none | `num_floors` | none | Region, Typology, Age_bracket, Construction_type, DHW_type |
| MA | `building_id` | none | `num_floors` | none | Region, Typology, Age_bracket, 16 retrofit/system fields |

`scenario`/`Scenario` is left out of the last column because the preprocessor
supplies it. No partner currently supplies basement, attic or weather columns;
all of them rely on the defaults.

---

## Possible next step: a slim GIS file in each bundle

The GIS file is the only component that is not self-contained. The full
`buildings.geojson` files run to about a gigabyte because they carry every
attribute the partner sent. A version that keeps **only the tier 1 and tier 2
columns**, saved as GeoParquet, would be much smaller. For some partners it
might fit under the 25 MB limit on `inputs/`, which would make those bundles
fully runnable from this repository alone. Whether that holds depends on
footprint count and geometry detail, so each partner would need to be measured
before relying on it.

If this goes ahead, the slim file would:

- keep geometry, the ID column, height and/or floors, every semantic field, and
  any tier 2 columns the partner actually provides;
- stay in EPSG:4326;
- keep the buffer of surrounding buildings used for shading;
- be registered under the `gis_file` role like any other file. The full file
  would remain in `external_files` as the provenance source.
