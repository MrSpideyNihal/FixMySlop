"""
Pytest fixtures — mock LLM client, temp repo factory, shared test data.
"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock
from core.issue import Issue, ScanReport
from macros import SEVERITY_HIGH, SEVERITY_MEDIUM, CATEGORY_SECURITY, CATEGORY_AI_SMELL


@pytest.fixture
def temp_repo(tmp_path):
    """Create a temporary repository with sample files for testing."""
    # Python files
    py_file = tmp_path / "main.py"
    py_file.write_text(
        'import os\n\ndef hello():\n    print("hello")\n\nhello()\n',
        encoding="utf-8",
    )

    sub_dir = tmp_path / "utils"
    sub_dir.mkdir()
    util_file = sub_dir / "helpers.py"
    util_file.write_text(
        'def add(a, b):\n    return a + b\n',
        encoding="utf-8",
    )

    # Gitignore
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("__pycache__/\n*.pyc\n", encoding="utf-8")

    # Non-Python file (should be included based on extension)
    js_file = tmp_path / "app.js"
    js_file.write_text('console.log("hello");\n', encoding="utf-8")

    return tmp_path


@pytest.fixture
def sample_issue():
    """Return a sample Issue for testing."""
    return Issue(
        file_path="/tmp/test/main.py",
        line_start=3,
        line_end=5,
        severity=SEVERITY_HIGH,
        category=CATEGORY_SECURITY,
        rule_id="sql_injection",
        title="Possible SQL injection",
        description="User input is passed directly into an SQL query.",
        evidence='cursor.execute(f"SELECT * FROM users WHERE id={user_id}")',
        source_tool="llm",
    )


@pytest.fixture
def sample_issues():
    """Return a list of sample Issues for testing."""
    return [
        Issue(
            file_path="/tmp/test/main.py",
            line_start=3,
            line_end=5,
            severity=SEVERITY_HIGH,
            category=CATEGORY_SECURITY,
            rule_id="sql_injection",
            title="SQL injection risk",
            description="Unsanitized input in query.",
            source_tool="llm",
        ),
        Issue(
            file_path="/tmp/test/main.py",
            line_start=10,
            line_end=12,
            severity=SEVERITY_MEDIUM,
            category=CATEGORY_AI_SMELL,
            rule_id="broad_except",
            title="Broad exception handler",
            description="Catching all exceptions hides real errors.",
            source_tool="ruff",
        ),
        Issue(
            file_path="/tmp/test/utils/helpers.py",
            line_start=1,
            line_end=2,
            severity=SEVERITY_MEDIUM,
            category=CATEGORY_AI_SMELL,
            rule_id="missing_docstring",
            title="Missing docstring",
            description="Function lacks a docstring.",
            source_tool="ruff",
        ),
    ]


@pytest.fixture
def sample_report(sample_issues):
    """Return a sample ScanReport for testing."""
    return ScanReport(
        repo_path="/tmp/test",
        scan_time_s=12.5,
        total_files=5,
        scanned_files=3,
        issues=sample_issues,
        slop_score=35.0,
        model_used="qwen2.5-coder:7b",
    )


@pytest.fixture
def mock_llm_client():
    """Return a mock LLM client."""
    client = MagicMock()
    client.is_available.return_value = True
    client.chat.return_value = '[]'
    client.parse_json_response.return_value = []
    return client
