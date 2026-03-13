"""Tests for core/scanner.py."""
from pathlib import Path
from core.scanner import Scanner


class TestScanner:
    """Tests for the Scanner class."""

    def test_scanner_finds_python_files(self, temp_repo):
        """Scanner should find .py files in the temp repo."""
        scanner = Scanner(str(temp_repo))
        count = scanner.file_count
        assert count >= 2  # main.py + helpers.py

    def test_scanner_yields_file_content(self, temp_repo):
        """Scanner should yield (path, content) tuples."""
        scanner = Scanner(str(temp_repo))
        files = list(scanner.scan())
        assert len(files) >= 2
        for path, content in files:
            assert isinstance(path, Path)
            assert isinstance(content, str)
            assert len(content) > 0

    def test_scanner_skips_git_directory(self, temp_repo):
        """Scanner should skip .git directories."""
        git_dir = temp_repo / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text("dummy", encoding="utf-8")

        scanner = Scanner(str(temp_repo))
        files = list(scanner.scan())
        paths = [str(p) for p, _ in files]
        assert not any(".git" in p for p in paths)

    def test_scanner_respects_max_file_size(self, temp_repo):
        """Scanner should skip files larger than max_file_size_kb."""
        big_file = temp_repo / "big.py"
        big_file.write_text("x = 1\n" * 100000, encoding="utf-8")

        scanner = Scanner(str(temp_repo), max_file_size_kb=1)
        files = list(scanner.scan())
        paths = [p.name for p, _ in files]
        assert "big.py" not in paths

    def test_scanner_progress_callback(self, temp_repo):
        """Scanner should call the progress callback."""
        scanner = Scanner(str(temp_repo))
        calls = []
        for _ in scanner.scan(progress_callback=lambda c, t, n: calls.append((c, t, n))):
            pass
        assert len(calls) > 0
        for current, total, name in calls:
            assert current <= total
            assert isinstance(name, str)
