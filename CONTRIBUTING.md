# Contributing

This repository's value is that its records can be trusted. A few rules follow
from that; everything else is ordinary.

## The rules

**Never edit a published version.** Directories listed in `published.yml` are
permanent records — results elsewhere pin them by fingerprint, so changing one
silently breaks that lineage. The pre-commit hook and CI both refuse it. To
change an input, create a new version. To mark a bad one, use
`globi-data inputs retract`, which edits `versions.yml` outside the frozen
folder.

**Never put large files under `inputs/`.** The 25 MB warning and 90 MB hard limit
exist because the whole design rests on this repository staying quick to clone
and browse. GIS geometry and result parquets belong elsewhere; record them as
`external_files` or `remote_files` instead.

**Never add git-lfs.** An LFS pointer downloads as a few hundred bytes of text
for anyone who has not installed git-lfs, which defeats the point of inputs
being downloadable with no setup.

**Never let simulation code write into a version directory.** Generators in
globi-partners-data (`ma/weather.py`, `ma/baseline.py`) keep writing there;
promoting their output into a version is an explicit `globi-data inputs new`
step.

**Do not hand-edit generated files.** `inputs/README.md`, `inputs/index.yml`,
`outputs/README.md`, `outputs/index.yml`, `outputs/STATUS.md` and the per-partner
`README.md` files are rebuilt by `globi-data index --write` and checked in CI.

## Setup

```bash
uv sync                      # add --extra s3 for the S3 commands
uv run globi-data init-hooks # once per clone
```

## Before you push

```bash
uv run ruff check src/ tests/
uv run ruff format src/ tests/
uv run pyright
uv run pytest
uv run globi-data check
```

`globi-data check` is what CI runs. It needs no AWS credentials and no git-lfs,
by design.

## Adding a version

See [docs/HOW-TO-ADD-A-VERSION.md](docs/HOW-TO-ADD-A-VERSION.md). There is a
browser-based route that needs nothing installed.

## Naming

Partner directories match their names in globi-partners-data's
`data/experiments.yaml` — `Sao_Paulo`, `MACommercial`, `Cambridge_UK`. They are
not lowercased or normalised, because the other repository resolves them by
exact name.

Experiment directories under `outputs/runs/` mirror the scythe run name exactly,
including the `name:` override where one exists (`Sao_Paulo_Bela_Vista/tmy/noAC`,
whose inputs come from the `Sao_Paulo` bundle).

## Commits

Lowercase, imperative, no scope — matching globi-partners-data:

```
add lisbon input v002
record ahmedabad tmy results
fix weather lookup for pittsfield
```

One commit per partner when seeding or bulk-updating, so review stays readable.
