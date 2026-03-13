"""
Issue dataclass — represents a single detected problem in the codebase.
All analyzers produce Issue objects. Report builder consumes them.
"""
from dataclasses import dataclass, field
from macros import SEVERITY_MEDIUM, CATEGORY_AI_SMELL


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
    tool_versions: dict = field(default_factory=dict)
