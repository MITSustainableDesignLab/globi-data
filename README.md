# globi-data

Input and output files for the GloBI project.

The simulations themselves run from
[globi](https://github.com/MITSustainableDesignLab/globi).
This repository is where their **files** live.

---

## I just want to download a partner's input files

1. Open [`inputs/`](inputs/) and pick a country folder (ISO code), then the city/partner.
2. The top of that page tells you which version is current.
3. Open that version's folder and download the files.

Every version folder is complete on its own. You never need to combine folders,
and you never need to install anything.

**GIS:** building footprints are not stored here. See
[docs/GIS-ACCESS.md](docs/GIS-ACCESS.md).

---

## How versions work

Each region's inputs live under a country code:

```
inputs/PT/Lisbon/
├── README.md
├── CURRENT.yml
├── versions.yml
├── v001/
└── v002/
```

**Published versions are never edited.** New simulation-affecting changes get a new version.
See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Outputs

Processed result parquets live in S3. This repo records **where they are** and what
produced them. Raw scythe outputs are not published.

```bash
globi-data outputs download PT/Lisbon/tmy/Baseline --dest ./results
```

Product shape: [docs/PUBLIC-PRODUCT.md](docs/PUBLIC-PRODUCT.md).

Browse [`outputs/runs/`](outputs/runs/) (paths start with `<ISO>/<City>/…`).

---

## Layout

| Path | What it holds |
|---|---|
| `inputs/<ISO>/<City>/vNNN/` | Frozen input bundle |
| `outputs/runs/<ISO>/<City>/<weather>/<Scenario>/vNNN/` | Processed results + provenance |
| `outputs/surrogates/<ISO>/<City>/vNNN/` | Surrogate manifest (MA) |
| `countries.yml` | City folder → ISO code |
| `public_storage.yml` | Public S3 bucket/prefix (mutable) |
| `outputs/STATUS.md` | Staleness report |

---

## Setup (maintainers)

```bash
uv sync                  # uv sync --extra s3 for S3 commands
```

```bash
export GLOBI_PARTNERS_ROOT=../globi-partners-data
```

```bash
globi-data inputs list
globi-data inputs show Lisbon
globi-data status
globi-data check
```

---

## Documentation

- [docs/HOW-TO-DOWNLOAD-INPUTS.md](docs/HOW-TO-DOWNLOAD-INPUTS.md)
- [docs/HOW-TO-ADD-A-VERSION.md](docs/HOW-TO-ADD-A-VERSION.md)
- [docs/PUBLIC-PRODUCT.md](docs/PUBLIC-PRODUCT.md)
- [docs/PUBLIC-DATA.md](docs/PUBLIC-DATA.md) (public S3 / Registry documentation)
- [registry/draft/](registry/draft/) (draft open-data-registry YAML)
- [docs/GIS-ACCESS.md](docs/GIS-ACCESS.md)
- [docs/SCHEMA.md](docs/SCHEMA.md)
- [SECURITY.md](SECURITY.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)