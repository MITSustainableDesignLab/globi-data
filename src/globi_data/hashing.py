"""Content hashing primitives.

Every integrity guarantee in this repo reduces to one of three hashes:

``file_sha256``
    The sha256 of a single file's bytes.

``bundle_sha256``
    The content identity of a whole input bundle: a hash over the
    ``sha256  path`` lines of its simulation-affecting files. Two bundles with
    the same ``bundle_sha256`` would produce the same simulation, which is what
    makes the no-op guard and the tamper check possible.

``manifest_sha256``
    The sha256 of a version manifest file's own bytes. This is what an output
    version pins, and it is deliberately reproducible by hand with
    ``shasum -a 256 input-version.yml``.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from pathlib import Path

_CHUNK = 1024 * 1024


def file_sha256(path: Path) -> str:
    """Return the hex sha256 of a file's bytes, read in chunks."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while chunk := handle.read(_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def file_size(path: Path) -> int:
    """Return a file's size in bytes."""
    return path.stat().st_size


def bundle_sha256(entries: Iterable[tuple[str, str]]) -> str:
    r"""Hash a set of ``(path, sha256)`` pairs into one bundle identity.

    The input is sorted by path first, so the result does not depend on the
    order files were discovered in. Each entry contributes one
    ``"{sha256}  {path}\\n"`` line, matching the format ``shasum`` itself emits
    so the value can be reproduced with standard tools.

    Args:
        entries: ``(path, sha256)`` pairs. Callers are responsible for
            filtering out non-simulation-affecting files.

    Returns:
        The hex sha256 of the assembled manifest text.
    """
    digest = hashlib.sha256()
    for path, sha in sorted(entries, key=lambda pair: pair[0]):
        digest.update(f"{sha}  {path}\n".encode())
    return digest.hexdigest()


def text_sha256(text: str) -> str:
    """Return the hex sha256 of a string's UTF-8 encoding."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
