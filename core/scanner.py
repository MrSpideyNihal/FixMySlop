"""
Scanner — walks a repo/folder, collects supported files,
respects .gitignore, skips binary and oversized files.
"""
from pathlib import Path
from typing import Iterator, Callable, Optional
from macros import SUPPORTED_EXTENSIONS, DEFAULT_MAX_FILE_SIZE_KB
from utils.file_utils import read_file_safe, parse_gitignore
from utils.logger import get_logger

logger = get_logger(__name__)


class Scanner:
    """
    Walks a directory tree and yields file paths ready for analysis.
    Respects .gitignore, skips node_modules/venv/__pycache__/etc.
    """

    SKIP_DIRS = {
        "node_modules", ".git", "__pycache__", ".venv", "venv",
        "env", "dist", "build", ".next", ".nuxt", "target",
        ".idea", ".vscode", "coverage", ".mypy_cache", ".ruff_cache",
    }

    def __init__(
        self,
        repo_path: str,
        max_file_size_kb: int = DEFAULT_MAX_FILE_SIZE_KB,
        extensions: Optional[set] = None,
    ):
        """Initialize scanner with repo path or file path and filters."""
        self.repo_path = Path(repo_path)
        self.max_file_size_kb = max_file_size_kb
        self.extensions = extensions or SUPPORTED_EXTENSIONS
        self._is_single_file = self.repo_path.is_file()
        if self._is_single_file:
            self._gitignore_patterns = []
        else:
            self._gitignore_patterns = parse_gitignore(self.repo_path / ".gitignore")

    def scan(
        self,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> Iterator[tuple[Path, str]]:
        """
        Yield (file_path, file_content) for each supported file.
        Calls progress_callback(current, total, filename) if provided.
        """
        all_files = list(self._collect_files())
        total = len(all_files)
        logger.info("Found %d files to scan in %s", total, self.repo_path)

        for i, path in enumerate(all_files):
            content = read_file_safe(path, self.max_file_size_kb)
            if content is None:
                continue
            if progress_callback:
                progress_callback(i + 1, total, path.name)
            yield path, content

    def _collect_files(self) -> Iterator[Path]:
        """Walk the repo and collect all supported, non-ignored files."""
        # Handle single file path
        if self._is_single_file:
            path = self.repo_path
            if path.suffix.lower() in self.extensions:
                try:
                    if path.stat().st_size <= self.max_file_size_kb * 1024:
                        yield path
                        return
                except OSError:
                    pass
            return

        # Directory walk
        for item in self.repo_path.rglob("*"):
            if not item.is_file():
                continue
            # Skip directories in SKIP_DIRS
            if any(part in self.SKIP_DIRS for part in item.parts):
                continue
            if item.suffix.lower() not in self.extensions:
                continue
            try:
                if item.stat().st_size > self.max_file_size_kb * 1024:
                    logger.debug("Skipping oversized file: %s", item)
                    continue
            except OSError:
                continue
            yield item

    @property
    def file_count(self) -> int:
        """Return total number of scannable files without reading them."""
        return sum(1 for _ in self._collect_files())
