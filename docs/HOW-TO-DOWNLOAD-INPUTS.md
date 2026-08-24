# How to download a partner's input files

No software required. Everything here is done in a web browser.

## The quick way

1. Go to [`inputs/partners/`](../inputs/partners/).
2. Click the partner you want — for example `Lisbon`.
3. The page tells you which version is current, with a link to it.
4. Click that version's folder, then **Download** on any file you need.

To get everything at once, use the link on the partner page to that version's
**release**, and download the single `.zip`. That zip contains the complete set
of files for that version.

## What the files are

Every version folder has a `README.md` at the top explaining each file in plain
language. Broadly:

| File | What it is |
|---|---|
| `components-lib.db` | The component and material library |
| `semantic-fields.yaml` | The building attributes and their allowed values |
| `component-map.yaml` | How those attributes map to walls, HVAC, hot water |
| `gis-preprocessor.yml` | Rules for cleaning up the building shapes |
| `artifacts.yml` / `manifest.yml` | Point at everything else |
| `weather/` | Current-climate weather files |
| `weather_ftmy/` | Future-climate (2050) weather files |
| `input-version.yml` | The record of what this version contains |

Some partners use `.yml` where others use `.yaml`, and a few have extra files.
The version README always lists what is actually there.

## The building footprints are not here

`buildings.geojson` files are up to a gigabyte each. Keeping them here would
make this repository slow and awkward to download for everyone, including people
who only need a weather file.

They live in the `globi-partners-data` repository instead, at
`data/partners/<Partner>/buildings.geojson`. Each version records their exact
size and fingerprint, so it is always possible to confirm you have the right one.

If you have that repository checked out and the file looks tiny (a few hundred
bytes of text starting with `version https://git-lfs...`), run:

```bash
git lfs pull
```

## Which version should I use?

The current one, unless you have a reason. That is what the partner page points
at, and it is what new simulation runs use.

Older versions are kept so that results produced from them stay reproducible. If
you are trying to reproduce a specific set of results, look up that run under
[`outputs/runs/`](../outputs/runs/) — its record names the exact input version it
used.

## Checking you got the right file

Every file's fingerprint is recorded in `input-version.yml`. To confirm a
download:

```bash
shasum -a 256 components-lib.db
```

and compare it with the `sha256` next to that file in the manifest.
