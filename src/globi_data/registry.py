"""Reading globi-partners-data's experiment registry.

``data/experiments.yaml`` in the sibling repo is the list of which runs get
tasked. It is not versioned here — it is tasking configuration, not data — but
two things in it are worth copying into manifests so they can be read without
the other repo present: which scenarios a partner compares, and which arm of
that comparison a given scenario label is.
"""

from __future__ import annotations

from pathlib import Path

from . import yamlio


def _partners(experiments_yaml: Path) -> dict[str, dict]:
    """Return the ``partners`` mapping, or an empty dict if unreadable."""
    if not experiments_yaml.exists():
        return {}
    data = yamlio.read(experiments_yaml) or {}
    partners = data.get("partners") or {}
    return {name: (config or {}) for name, config in partners.items()}


def load_partner_scenarios(experiments_yaml: Path) -> dict[str, dict[str, str]]:
    """Map each partner to its ``{baseline: ..., alternative: ...}`` scenarios.

    Keyed by both the directory name and the run-name override (``name:``), so
    ``Sao_Paulo`` and ``Sao_Paulo_Bela_Vista`` both resolve.
    """
    out: dict[str, dict[str, str]] = {}
    for partner, config in _partners(experiments_yaml).items():
        scenarios = config.get("scenarios") or {}
        if not scenarios:
            continue
        out[partner] = dict(scenarios)
        override = config.get("name")
        if override:
            out[override] = dict(scenarios)
    return out


def load_partner_aliases(experiments_yaml: Path) -> dict[str, str]:
    """Map run names back to the partner directory that holds their inputs.

    A partner may run under a different name than its directory: ``Sao_Paulo``
    is tasked as ``Sao_Paulo_Bela_Vista`` via the registry's ``name:`` override,
    so results filed under that run name still need to pin the ``Sao_Paulo``
    input bundle.
    """
    aliases: dict[str, str] = {}
    for partner, config in _partners(experiments_yaml).items():
        override = config.get("name")
        if override and override != partner:
            aliases[override] = partner
    return aliases


def load_scenario_kinds(experiments_yaml: Path) -> dict[tuple[str, str], str]:
    """Map ``(partner, scenario_value)`` to ``baseline`` or ``alternative``."""
    mapping: dict[tuple[str, str], str] = {}
    for partner, config in _partners(experiments_yaml).items():
        name = config.get("name", partner)
        for kind, value in (config.get("scenarios") or {}).items():
            mapping[(partner, value)] = kind
            mapping[(name, value)] = kind
    return mapping
