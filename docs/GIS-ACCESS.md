# Building GIS access

Each input version records the **sha256 and byte size** of the partner `buildings.geojson` (or equivalent GIS file). The geometry file is **not** stored in this repository so clones stay small.

## Public launch stance

At launch, GIS footprints are **not redistributed from this repository**. Consumers get:

- fingerprints in `input-version.yml` for reproducibility
- resolver hints pointing at the historical `globi-partners-data` layout

If you need geometry for research, contact the lab or wait for a dedicated public GIS distribution (separate bucket or release asset). Do not assume private sibling-repo paths remain available after this repo goes public.

## Verifying you have the right file

When you obtain a GIS file elsewhere, compare its sha256 to the manifest:

```bash
shasum -a 256 buildings.geojson
```

It must match `external_files[].sha256` for role `gis_file` in that version’s `input-version.yml`.