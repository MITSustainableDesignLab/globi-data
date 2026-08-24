# globi-data

Input and output files for [GloBI](https://github.com/MITSustainableDesignLab/globi-partners-data)
building-energy simulation runs, kept in versions so nothing is ever overwritten.

The simulations themselves run from
[globi-partners-data](https://github.com/MITSustainableDesignLab/globi-partners-data).
This repository is where their **files** live.

---

## I just want to download a partner's input files

1. Open [`inputs/partners/`](inputs/partners/) and click the partner you want.
2. The top of that page tells you which version is current.
3. Open that version's folder and download the files — either one at a time with
   the download button, or the whole folder as a zip from the matching
   [release](../../releases).

Every version folder is complete on its own. You never need to combine folders,
and you never need to install anything.

**One exception:** the building footprint files (`buildings.geojson`) are not
stored here. They run to a gigabyte each, which would make this repository
painful to download. Each version records their exact size and fingerprint and
says where to find them, so results stay traceable. They live in
`globi-partners-data/data/partners/<Partner>/`.

---

## How versions work

Each partner's inputs are stored as numbered folders:

```
inputs/partners/Lisbon/
├── README.md        <- version history, start here
├── CURRENT.yml      <- says which version is current
├── versions.yml     <- status of every version
├── v001/            <- frozen
└── v002/            <- frozen
```

Two rules make this trustworthy:

**Published versions are never edited.** If an input needs to change, that is a
new version. The old one stays exactly as it was, so results produced from it
remain reproducible. This is enforced by a git hook and by CI, not just by
convention.

**Every version says whether it can change results.** A version is either
`simulation-affecting` (a component library, a weather file, a component map) or
`metadata-only` (a typo in a README). Only the first kind marks existing results
as needing a re-run — which is what keeps
[`outputs/STATUS.md`](outputs/STATUS.md) meaningful instead of permanently red.

---

## Outputs

Simulation results are large — roughly 11 GB of parquet files — so they stay in
S3. What is versioned here is the record of **where they are and what produced
them**: the input version, the code commits, the simulation run identifier, and
a fingerprint for every result file.

That record is what lets you ask "these numbers came from where?" and get a real
answer, and it is what
[`outputs/STATUS.md`](outputs/STATUS.md) uses to flag results whose inputs have
since changed.

Browse them under [`outputs/runs/`](outputs/runs/), or download the actual files:

```bash
globi-data outputs download Ahmedabad/tmy/BAU --dest ./results
```

---

## Layout

| Path | What it holds |
|---|---|
| `inputs/partners/<Partner>/vNNN/` | One frozen, self-contained input bundle |
| `outputs/runs/<Partner>/<weather>/<Scenario>/vNNN/` | Where one run's results live, plus full provenance |
| `outputs/batches/<Batch>/vNNN/` | Same, for run families too numerous to list individually (MA's census tracts) |
| `outputs/STATUS.md` | Which results are still up to date |
| `published.yml` | Ledger of frozen directories |
| `docs/` | Schema reference and how-to guides |

---

## Setup (only if you are maintaining the repo)

```bash
uv sync                  # or: uv sync --extra s3   for the S3 commands
uv run globi-data init-hooks
```

`init-hooks` installs the pre-commit check that refuses edits to published
versions. Do this once per clone.

To work with the sibling repo, point at it once:

```bash
export GLOBI_PARTNERS_ROOT=../globi-partners-data
```

## Common commands

```bash
globi-data inputs list                       # what exists
globi-data inputs show Lisbon                # files and fingerprints
globi-data inputs diff Lisbon v001 v002      # what changed between versions
globi-data status                            # which results are stale
globi-data check                             # everything CI runs

globi-data inputs new Lisbon \
    --from ../globi-partners-data/data/partners/Lisbon \
    --summary "Corrected envelope U-values"
```

There is also a browser-based route for adding a version that needs no software
installed — see [docs/HOW-TO-ADD-A-VERSION.md](docs/HOW-TO-ADD-A-VERSION.md).

## Documentation

- [docs/HOW-TO-DOWNLOAD-INPUTS.md](docs/HOW-TO-DOWNLOAD-INPUTS.md) — no CLI needed
- [docs/HOW-TO-ADD-A-VERSION.md](docs/HOW-TO-ADD-A-VERSION.md) — both routes
- [docs/SCHEMA.md](docs/SCHEMA.md) — every manifest field
- [CONTRIBUTING.md](CONTRIBUTING.md) — the rules that keep this trustworthy
