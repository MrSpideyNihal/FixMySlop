"""
Git helpers — file listing that respects .gitignore exactly, and changed-file
detection for PR / pre-commit scans. Every function returns None when git
isn't available or the path isn't inside a repository.
"""
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from fixmyslop.utils.logger import get_logger

logger = get_logger(__name__)


def _git(cwd: Path, *args: str) -> Optional[str]:
    """Run a git command and return stdout, or None on any failure."""
    if shutil.which("git") is None:
        return None
    try:
        result = subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as e:
        logger.debug("git %s failed: %s", args, e)
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def git_root(path: Path) -> Optional[Path]:
    """Top-level directory of the repository containing `path`."""
    cwd = path if path.is_dir() else path.parent
    out = _git(cwd, "rev-parse", "--show-toplevel")
    return Path(out.strip()).resolve() if out else None


def is_ignored(path: Path) -> bool:
    """True when git ignores `path` (tracked files never are). False outside a repository."""
    return _git(path.parent, "check-ignore", "-q", path.name) is not None


def list_files(directory: Path) -> Optional[list[Path]]:
    """Tracked + untracked-but-not-ignored files under `directory`."""
    if git_root(directory) is None:
        return None
    out = _git(directory, "ls-files", "--cached", "--others", "--exclude-standard", "-z")
    if out is None:
        return None
    files = []
    for rel in out.split("\0"):
        if rel:
            path = directory / rel
            if path.is_file():
                files.append(path)
    return files


def tracked_files(directory: Path) -> Optional[list[str]]:
    """Paths tracked by Git under the repository containing `directory`."""
    root = git_root(directory)
    if root is None:
        return None
    out = _git(root, "ls-files", "-z")
    if out is None:
        logger.warning("Could not list tracked files in Git repository %s", root)
        return None
    return [name for name in out.split("\0") if name]


def default_base(cwd: Path) -> Optional[str]:
    """Best guess at the branch a PR targets: origin/HEAD, then main/master."""
    out = _git(cwd, "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD")
    if out:
        return out.strip().replace("refs/remotes/", "")
    for candidate in ("origin/main", "origin/master", "main", "master"):
        if _git(cwd, "rev-parse", "--verify", "--quiet", candidate) is not None:
            return candidate
    return None


def changed_files(directory: Path, base: Optional[str] = None) -> Optional[list[Path]]:
    """Files changed vs the merge-base with `base`, plus staged, unstaged and untracked files."""
    root = git_root(directory)
    if root is None:
        return None
    names: set[str] = set()
    base = base or default_base(root)
    if base:
        merge_base = _git(root, "merge-base", base, "HEAD")
        if merge_base:
            names.update((_git(root, "diff", "--name-only", "--diff-filter=ACMR", merge_base.strip()) or "").splitlines())
    names.update((_git(root, "diff", "--name-only", "--diff-filter=ACMR", "HEAD") or "").splitlines())
    names.update((_git(root, "diff", "--name-only", "--cached", "--diff-filter=ACMR") or "").splitlines())
    names.update((_git(root, "ls-files", "--others", "--exclude-standard") or "").splitlines())
    directory = directory.resolve()
    result = []
    for name in sorted(n for n in names if n):
        path = (root / name).resolve()
        if path.is_file() and (path == directory or directory in path.parents):
            result.append(path)
    return result
