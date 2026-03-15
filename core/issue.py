"""
Issue dataclass — represents a single detected problem in the codebase.
All analyzers produce Issue objects. Report builder consumes them.
"""
import json
from dataclasses import dataclass, field
from macros import SEVERITY_MEDIUM, CATEGORY_AI_SMELL, SCAN_MODE_TURBO


def _to_int(value, fallback: int = 0) -> int:
    """Coerce a value to int, returning fallback on failure."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _to_text(value) -> str:
    """Coerce arbitrary values into display-safe text for UI/export."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        if all(not isinstance(item, (dict, list)) for item in value):
            return "\n".join(str(item) for item in value)
        try:
            return json.dumps(value)
        except (TypeError, ValueError):
            return str(value)
    if isinstance(value, dict):
        try:
            return json.dumps(value)
        except (TypeError, ValueError):
            return str(value)
    return str(value)


@dataclass
class Issue:
    """A single detected problem in a source file."""

    file_path: str
    line_start: int
    line_end: int
    severity: str = SEVERITY_MEDIUM
    category: str = CATEGORY_AI_SMELL
    rule_id: str = ""
    title: str = ""
    description: str = ""
    evidence: str = ""          # The actual code snippet that caused the issue
    suggested_fix: str = ""     # LLM-generated fix description
    diff: str = ""              # Unified diff patch string
    source_tool: str = "llm"    # "ruff", "bandit", "semgrep", or "llm"
    applied: bool = False

    def __post_init__(self):
        """Normalize types to keep downstream UI/renderers robust."""
        self.file_path = _to_text(self.file_path)
        self.line_start = _to_int(self.line_start, 0)
        self.line_end = _to_int(self.line_end, self.line_start)
        if self.line_end < self.line_start:
            self.line_end = self.line_start
        self.severity = _to_text(self.severity)
        self.category = _to_text(self.category)
        self.rule_id = _to_text(self.rule_id)
        self.title = _to_text(self.title)
        self.description = _to_text(self.description)
        self.evidence = _to_text(self.evidence)
        self.suggested_fix = _to_text(self.suggested_fix)
        self.diff = _to_text(self.diff)
        self.source_tool = _to_text(self.source_tool)


@dataclass
class ScanReport:
    """Complete scan results for a repository."""

    repo_path: str
    scan_time_s: float
    total_files: int
    scanned_files: int
    issues: list[Issue] = field(default_factory=list)
    slop_score: float = 0.0     # 0-100 overall debt percentage
    model_used: str = ""
    scan_mode: str = SCAN_MODE_TURBO
    tool_versions: dict = field(default_factory=dict)
