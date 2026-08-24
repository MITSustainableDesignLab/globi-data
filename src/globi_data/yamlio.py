"""Deterministic YAML read/write.

Manifests are hashed, diffed in pull requests, and read by non-technical users,
so the serialisation has to be stable and readable. Key order follows the model
definition rather than being alphabetised, block style is forced, and long
strings are not wrapped mid-word.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class _Dumper(yaml.SafeDumper):
    """SafeDumper that indents list items under their parent key."""

    def increase_indent(self, flow: bool = False, indentless: bool = False) -> None:
        return super().increase_indent(flow, False)


def _str_representer(dumper: _Dumper, data: str) -> yaml.Node:
    """Render multi-line strings as literal blocks so they stay readable."""
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


_Dumper.add_representer(str, _str_representer)


def dumps(data: Any) -> str:
    """Serialise to a deterministic YAML string."""
    return yaml.dump(
        data,
        Dumper=_Dumper,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
        width=100,
    )


def write(path: Path, data: Any, *, header: str | None = None) -> None:
    """Write YAML to ``path``, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = dumps(data)
    if header:
        commented = "\n".join(f"# {line}".rstrip() for line in header.splitlines())
        text = f"{commented}\n{text}"
    path.write_text(text, encoding="utf-8")


def read(path: Path) -> Any:
    """Load YAML from ``path``."""
    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def loads(text: str) -> Any:
    """Parse a YAML string."""
    return yaml.safe_load(text)
