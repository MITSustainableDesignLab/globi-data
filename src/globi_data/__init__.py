"""Versioned inputs and outputs for GloBI simulation runs.

See the repository README for the layout and docs/SCHEMA.md for the manifest
schemas. The short version:

- ``inputs/partners/<Partner>/vNNN/`` is a frozen, self-contained input bundle.
- ``outputs/runs/<Partner>/<weather>/<Scenario>/vNNN/`` records where a run's
  results live in S3 and exactly which inputs and code produced them.
- Mutable state (``CURRENT.yml``, ``versions.yml``) lives beside the version
  directories, never inside them.
"""

__version__ = "0.1.0"
