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
