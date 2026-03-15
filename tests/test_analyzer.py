"""Tests for core/analyzer.py."""
from pathlib import Path
from unittest.mock import MagicMock
from core.analyzer import Analyzer
from core.issue import Issue


class TestAnalyzer:
    """Tests for the Analyzer class."""

    def test_analyzer_with_mock_llm(self, mock_llm_client, temp_repo):
        """Analyzer should use mock LLM and return issues."""
        mock_llm_client.chat.return_value = '[{"line_start":1,"line_end":2,"severity":"MEDIUM","category":"AI Smell","rule_id":"test","title":"Test issue","description":"Test","evidence":"x=1"}]'
        mock_llm_client.parse_json_response.return_value = [
            {"line_start": 1, "line_end": 2, "severity": "MEDIUM",
             "category": "AI Smell", "rule_id": "test",
             "title": "Test issue", "description": "Test", "evidence": "x=1"}
        ]

        analyzer = Analyzer(llm_client=mock_llm_client, use_static_tools=False)
        issues = analyzer.analyze_file(
            Path(temp_repo / "main.py"),
            "x = 1\n",
        )
        assert len(issues) == 1
        assert issues[0].title == "Test issue"

    def test_analyzer_without_llm(self, temp_repo):
        """Analyzer should work without an LLM client (static-only mode)."""
        analyzer = Analyzer(llm_client=None, use_static_tools=False)
        issues = analyzer.analyze_file(
            Path(temp_repo / "main.py"),
            'print("hello")\n',
        )
        assert isinstance(issues, list)

    def test_deduplication(self, mock_llm_client):
        """Analyzer should deduplicate issues with same file + line + rule."""
        analyzer = Analyzer(llm_client=None, use_static_tools=False)
        issues = [
            Issue(file_path="a.py", line_start=1, line_end=1, rule_id="r1", title="A"),
            Issue(file_path="a.py", line_start=1, line_end=1, rule_id="r1", title="A dup"),
            Issue(file_path="a.py", line_start=2, line_end=2, rule_id="r1", title="B"),
        ]
        unique = analyzer._deduplicate(issues)
        assert len(unique) == 2

    def test_language_detection(self):
        """Analyzer should detect language from file extension."""
        analyzer = Analyzer(llm_client=None, use_static_tools=False)
        assert analyzer._detect_language(Path("test.py")) == "python"
        assert analyzer._detect_language(Path("test.js")) == "javascript"
        assert analyzer._detect_language(Path("test.rs")) == "rust"
        assert analyzer._detect_language(Path("test.unknown")) == "code"

    def test_issue_normalization_from_llm_non_string_fields(self):
        """Issue payloads with list evidence and string line numbers should be normalized."""
        analyzer = Analyzer(llm_client=None, use_static_tools=False)
        payload = [{
            "line_start": "12",
            "line_end": "14",
            "severity": "HIGH",
            "category": "Security",
            "rule_id": "llm_test",
            "title": "Potential issue",
            "description": "Check this branch.",
            "evidence": ["if user_input:", "execute(query)"],
        }]

        issues = analyzer._build_issues(payload, Path("sample.py"))

        assert len(issues) == 1
        assert issues[0].line_start == 12
        assert issues[0].line_end == 14
        assert isinstance(issues[0].evidence, str)
        assert "if user_input:" in issues[0].evidence
        assert "execute(query)" in issues[0].evidence
