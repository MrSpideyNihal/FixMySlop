"""Tests for core/static_tools.py."""
import shutil
from core.static_tools import StaticToolRunner


class TestStaticToolRunner:
    """Tests for the StaticToolRunner class."""

    def test_init_detects_tools(self):
        """Should detect whether ruff/bandit/semgrep are installed."""
        runner = StaticToolRunner()
        assert isinstance(runner._available, dict)
        assert "ruff" in runner._available
        assert "bandit" in runner._available
        assert "semgrep" in runner._available

    def test_run_on_non_python_file(self, tmp_path):
        """Should return empty list for non-Python files with Python-only tools."""
        js_file = tmp_path / "app.js"
        js_file.write_text('console.log("hello");\n', encoding="utf-8")

        runner = StaticToolRunner()
        # Force semgrep to not available for this test
        runner._available["semgrep"] = False
        issues = runner.run(js_file, 'console.log("hello");\n', "javascript")
        assert isinstance(issues, list)

    def test_ruff_severity_mapping(self):
        """Should map ruff codes to appropriate severity levels."""
        assert StaticToolRunner._ruff_severity("S101") == "HIGH"  # Security
        assert StaticToolRunner._ruff_severity("E501") == "MEDIUM"  # Style
        assert StaticToolRunner._ruff_severity("F401") == "HIGH"  # Pyflakes
        assert StaticToolRunner._ruff_severity("D100") == "LOW"  # Default

    def test_get_tool_versions(self):
        """Should return version strings or None for each tool."""
        runner = StaticToolRunner()
        versions = runner.get_tool_versions()
        assert isinstance(versions, dict)
        assert "ruff" in versions
