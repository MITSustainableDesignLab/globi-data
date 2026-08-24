"""Thin wrappers over the ``git`` CLI.

Used for two things: capturing provenance about the repo a bundle came from,
and computing tree hashes for the immutability ledger. Everything here degrades
to ``None`` rather than raising when git is unavailable or the directory is not
a repo, because recording provenance must never be the reason a command fails.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

_GIT = "git"


def _run(args: list[str], cwd: Path) -> str | None:
    """Run a git command, returning stripped stdout or None on any failure."""
    try:
        result = subprocess.run(  # noqa: S603
            [_GIT, *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, ValueError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def is_repo(path: Path) -> bool:
    """Whether ``path`` is inside a git work tree."""
    return _run(["rev-parse", "--is-inside-work-tree"], path) == "true"


def repo_root(path: Path) -> Path | None:
    """Return the top level of the work tree containing ``path``."""
    top = _run(["rev-parse", "--show-toplevel"], path)
    return Path(top) if top else None


def head_commit(path: Path) -> str | None:
    """Return the full HEAD sha, or None if there are no commits yet."""
    return _run(["rev-parse", "HEAD"], path)


def is_dirty(path: Path) -> bool | None:
    """Whether the work tree has uncommitted changes."""
    status = _run(["status", "--porcelain"], path)
    if status is None:
        return None
    return bool(status)


def remote_url(path: Path, remote: str = "origin") -> str | None:
    """Return the URL configured for ``remote``."""
    return _run(["remote", "get-url", remote], path)


def describe(path: Path) -> str | None:
    """Return ``git describe --tags --always``, useful for a human-readable code version."""
    return _run(["describe", "--tags", "--always", "--dirty"], path)


def submodule_commit(repo: Path, submodule_path: str) -> str | None:
    """Return the commit a submodule is pinned at.

    ``git submodule status`` prefixes the sha with a status character (``-`` not
    initialised, ``+`` out of sync, ``U`` conflicts), which is stripped here.
    """
    out = _run(["submodule", "status", submodule_path], repo)
    if not out:
        return None
    token = out.split()[0]
    return token.lstrip("-+U ") or None


def tree_sha(repo: Path, rel_path: str, ref: str = "HEAD") -> str | None:
    """Return the tree object sha for a directory at a given ref.

    Any byte changed anywhere beneath the directory changes this value, which is
    what makes it a cheap immutability fingerprint for a published version dir.
    """
    return _run(["rev-parse", f"{ref}:{rel_path}"], repo)


def changed_paths(repo: Path, base: str, head: str = "HEAD") -> list[tuple[str, str]]:
    """Return ``(status, path)`` pairs for files changed between two refs.

    Status is git's name-status letter: ``A`` added, ``M`` modified, ``D``
    deleted, ``R###`` renamed. For renames only the destination path is
    reported, which is what the immutability check wants.
    """
    out = _run(["diff", "--name-status", f"{base}..{head}"], repo)
    if not out:
        return []
    changes: list[tuple[str, str]] = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            changes.append((parts[0], parts[-1]))
    return changes


def staged_paths(repo: Path) -> list[tuple[str, str]]:
    """Return ``(status, path)`` pairs for currently staged changes."""
    out = _run(["diff", "--cached", "--name-status"], repo)
    if not out:
        return []
    changes: list[tuple[str, str]] = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            changes.append((parts[0], parts[-1]))
    return changes


def merge_base(repo: Path, a: str, b: str) -> str | None:
    """Return the merge base of two refs."""
    return _run(["merge-base", a, b], repo)


def file_at_ref(repo: Path, ref: str, rel_path: str) -> str | None:
    """Return a file's contents at a given ref, or None if it did not exist."""
    return _run(["show", f"{ref}:{rel_path}"], repo)


@dataclass(frozen=True)
class RepoProvenance:
    """A snapshot of a git repo's identity, for recording in a manifest."""

    repo: str
    commit: str | None
    dirty: bool | None
    remote: str | None
    describe: str | None

    def to_dict(self) -> dict[str, object]:
        """Render as the mapping stored under a manifest's ``source``/``code`` keys."""
        data: dict[str, object] = {"repo": self.repo, "commit": self.commit}
        if self.dirty is not None:
            data["dirty"] = self.dirty
        if self.remote:
            data["remote"] = self.remote
        if self.describe:
            data["describe"] = self.describe
        return data


def capture(path: Path, name: str) -> RepoProvenance:
    """Capture the provenance of the repo containing ``path``."""
    return RepoProvenance(
        repo=name,
        commit=head_commit(path),
        dirty=is_dirty(path),
        remote=remote_url(path),
        describe=describe(path),
    )
