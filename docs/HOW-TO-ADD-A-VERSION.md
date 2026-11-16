# How to add a new version

Published versions are never edited. Changing an input means creating a new
version beside the old one. There are two routes.

---

## Route 1 — in the browser, nothing installed

1. Go to the repository's **Actions** tab.
2. Choose **Start a new input version** and click **Run workflow**.
3. Enter the partner name and one line describing what you are changing.
4. Wait a moment. A pull request appears, containing a new version folder that
   is a copy of the current one.
5. Open that folder on the pull request's branch and edit it with GitHub's own
   buttons:
   - **Add file → Upload files** to replace a components library or drop in a
     new weather file. Uploading a file with an existing name replaces it.
   - The **⋯ → Delete file** menu to remove one.
6. Each time you push, a bot recomputes all the fingerprints and rewrites
   `input-version.yml` and `README.md`. You do not have to touch those.
7. When the pull request looks right, merge it. That publishes the version,
   makes it current, and builds a downloadable zip.

If you change your mind, close the pull request. A version identical to the one
before it is rejected anyway.

---

## Route 2 — from the command line

```bash
globi-data inputs new Lisbon \
    --from ../globi-partners-data/data/partners/Lisbon \
    --summary "Corrected envelope U-values for the pre-1960 typology"
```

This curates the source directory — real inputs in, backups and build
intermediates out — hashes everything, works out what changed, and writes the
new version. Then commit:

```bash
git add inputs published.yml
git commit -m "add lisbon input v002"
```

Useful flags:

| Flag | Why |
|---|---|
| `--dry-run` | Show what would happen without writing anything |
| `--include '<glob>'` | Force-carry a file the curation would skip |
| `--impact metadata-only` | Override the automatic classification |
| `--allow-noop` | Permit a version identical to its parent (needs a summary) |

---

## What gets carried, and what does not

The curation keeps the files reachable from the bundle's configuration, plus
everything under `weather/` and `weather_ftmy/`. It leaves behind backups
(`components-lib-old.db`), build intermediates (`*.epw.txt`), source
spreadsheets, and GIS geometry.

Nothing disappears silently: every skipped file is listed with its reason in the
version's `README.md` under "Not carried over". If something was skipped that
should not have been, re-run with `--include`.

---

## `simulation-affecting` versus `metadata-only`

Every version is classified as one or the other, and it decides whether existing
results get flagged for a re-run.

- **`simulation-affecting`** — a components library, weather file, component
  map, semantic fields, or the GIS file changed. Results built on the previous
  version are marked **stale**.
- **`metadata-only`** — only documentation changed. Results stay valid.

The classification is derived automatically from what actually changed. Override
it with `--impact` only when you have a specific reason, because it is what
keeps [`outputs/STATUS.md`](../outputs/STATUS.md) honest.

---

## Something is wrong with a version I already published

Do not edit it — results recorded elsewhere pin it by fingerprint, and changing
it silently breaks that lineage. `globi-data check` reports any such edit.

Instead, either publish a corrected version, or mark the bad one as retracted:

```bash
globi-data inputs retract Lisbon v002 --reason "weather file was for the wrong year"
```

That edits `versions.yml`, which lives outside the frozen folder. The version
stays readable, and its status is visible to anyone browsing.

---

## Seeing what changed

```bash
globi-data inputs diff Lisbon v001 v002
```

Lists every file added, removed or modified, with sizes and fingerprints. This
is how you decide whether a re-run is genuinely needed.

---

## Recording a new surrogate model

Surrogates follow the same draft → promote route. For an epengine LightGBM
model (one `*.lgb` per target plus a `space.yml`, as the MA model is):

```bash
uv sync --extra s3
globi-data surrogates record MA \
  --from s3://ml-for-bem/hatchet/ma-webapp/<run>/iter-NNN/train/0/models/ \
  --summary "what changed in this model"
```

This copies `space.yml` in, downloads every model file once to record its
sha256, annotates the features from their names, and writes the next `vNNN` as a
draft. Target units are written as `unconfirmed`. Set them in the draft's
`surrogate-version.yml`, along with any metrics you have, then run:

```bash
globi-data surrogates promote MA v002
```

`promote` refuses while any unit is `unconfirmed` or `check` reports an error.
The new version becomes current, the old one is marked superseded, and the
directory is frozen. Anyone who fetches `current` gets the new model. Anyone who
pinned `v001` keeps the old one.

To use a model, see [`examples/ma-surrogate.ipynb`](../examples/ma-surrogate.ipynb),
or run `globi-data surrogates fetch MA`.
