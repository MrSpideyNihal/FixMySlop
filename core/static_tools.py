"""
Static tools — subprocess wrappers for Ruff, Bandit, and Semgrep.
Parses their JSON output into Issue objects for unified consumption.
"""
import json
import subprocess
import shutil
from pathlib import Path
from typing import Optional
from core.issue import Issue
from macros import (
    TOOL_RUFF, TOOL_BANDIT, TOOL_SEMGREP,
    SEVERITY_HIGH, SEVERITY_MEDIUM, SEVERITY_LOW, SEVERITY_INFO,
    CATEGORY_SECURITY, CATEGORY_DEBT, CATEGORY_MAINTAINABILITY,
)
from utils.logger import get_logger

logger = get_logger(__name__)


class StaticToolRunner:
    """
    Runs static analysis tools (Ruff, Bandit, Semgrep) on source files
    and converts their output into Issue objects.
    """

    def __init__(self):
        """Initialize and detect available tools."""
        self._available = {
            TOOL_RUFF: shutil.which("ruff") is not None,
            TOOL_BANDIT: shutil.which("bandit") is not None,
            TOOL_SEMGREP: shutil.which("semgrep") is not None,
        }
        for tool, available in self._available.items():
            if available:
                logger.info("Static tool '%s' found", tool)
            else:
                logger.debug("Static tool '%s' not found on PATH", tool)

    def run(self, file_path: Path, content: str, language: str) -> list[Issue]:
        """
        Run all available static tools on a file and return combined issues.
        Only runs Python tools on .py files.
        """
        issues: list[Issue] = []

        if language == "python" or file_path.suffix == ".py":
            if self._available[TOOL_RUFF]:
                issues.extend(self._run_ruff(file_path))
            if self._available[TOOL_BANDIT]:
                issues.extend(self._run_bandit(file_path))

        if self._available[TOOL_SEMGREP]:
            issues.extend(self._run_semgrep(file_path))

        return issues

    def _run_ruff(self, file_path: Path) -> list[Issue]:
        """Run Ruff linter and parse results into Issues."""
        try:
            result = subprocess.run(
                ["ruff", "check", "--output-format=json", "--no-fix", str(file_path)],
                capture_output=True, text=True, timeout=30,
            )
            if not result.stdout.strip():
                return []

            data = json.loads(result.stdout)
            issues = []
            for item in data:
                severity = self._ruff_severity(item.get("code", ""))
                issues.append(Issue(
                    file_path=str(file_path),
                    line_start=item.get("location", {}).get("row", 0),
                    line_end=item.get("end_location", {}).get("row", 0),
                    severity=severity,
                    category=CATEGORY_MAINTAINABILITY,
                    rule_id=item.get("code", "ruff_unknown"),
                    title=item.get("message", "Ruff issue"),
                    description=item.get("message", ""),
                    evidence="",
                    source_tool=TOOL_RUFF,
                ))
            return issues
        except Exception as e:
            logger.warning("Ruff failed for %s: %s", file_path, e)
            return []

    def _run_bandit(self, file_path: Path) -> list[Issue]:
        """Run Bandit security scanner and parse results into Issues."""
        try:
            result = subprocess.run(
                ["bandit", "-f", "json", "-q", str(file_path)],
                capture_output=True, text=True, timeout=30,
            )
            if not result.stdout.strip():
                return []

            data = json.loads(result.stdout)
            issues = []
            for item in data.get("results", []):
                severity_map = {
                    "HIGH": SEVERITY_HIGH,
                    "MEDIUM": SEVERITY_MEDIUM,
                    "LOW": SEVERITY_LOW,
                }
                issues.append(Issue(
                    file_path=str(file_path),
                    line_start=item.get("line_number", 0),
                    line_end=item.get("line_number", 0),
                    severity=severity_map.get(item.get("issue_severity", ""), SEVERITY_MEDIUM),
                    category=CATEGORY_SECURITY,
                    rule_id=item.get("test_id", "bandit_unknown"),
                    title=item.get("issue_text", "Bandit issue"),
                    description=item.get("issue_text", ""),
                    evidence=item.get("code", ""),
                    source_tool=TOOL_BANDIT,
                ))
            return issues
        except Exception as e:
            logger.warning("Bandit failed for %s: %s", file_path, e)
            return []

    def _run_semgrep(self, file_path: Path) -> list[Issue]:
        """Run Semgrep and parse results into Issues."""
        try:
            result = subprocess.run(
                ["semgrep", "--json", "--quiet", str(file_path)],
                capture_output=True, text=True, timeout=60,
            )
            if not result.stdout.strip():
                return []

            data = json.loads(result.stdout)
            issues = []
            for item in data.get("results", []):
                severity_map = {
                    "ERROR": SEVERITY_HIGH,
                    "WARNING": SEVERITY_MEDIUM,
                    "INFO": SEVERITY_INFO,
                }
                issues.append(Issue(
                    file_path=str(file_path),
                    line_start=item.get("start", {}).get("line", 0),
                    line_end=item.get("end", {}).get("line", 0),
                    severity=severity_map.get(item.get("extra", {}).get("severity", ""), SEVERITY_MEDIUM),
                    category=CATEGORY_DEBT,
                    rule_id=item.get("check_id", "semgrep_unknown"),
                    title=item.get("extra", {}).get("message", "Semgrep issue"),
                    description=item.get("extra", {}).get("message", ""),
                    evidence=item.get("extra", {}).get("lines", ""),
                    source_tool=TOOL_SEMGREP,
                ))
            return issues
        except Exception as e:
            logger.warning("Semgrep failed for %s: %s", file_path, e)
            return []

    @staticmethod
    def _ruff_severity(code: str) -> str:
        """Map Ruff rule codes to severity levels."""
        if code.startswith(("S", "B")):
            return SEVERITY_HIGH  # Security / bugbear
        elif code.startswith(("E", "W")):
            return SEVERITY_MEDIUM  # Style / warnings
        elif code.startswith(("F",)):
            return SEVERITY_HIGH  # Pyflakes errors
        return SEVERITY_LOW

    def get_tool_versions(self) -> dict[str, Optional[str]]:
        """Return version strings for all available tools."""
        versions = {}
        for tool in (TOOL_RUFF, TOOL_BANDIT, TOOL_SEMGREP):
            if self._available[tool]:
                try:
                    result = subprocess.run(
                        [tool, "--version"],
                        capture_output=True, text=True, timeout=5,
                    )
                    versions[tool] = result.stdout.strip()
                except Exception:
                    versions[tool] = "unknown"
            else:
                versions[tool] = None
        return versions
