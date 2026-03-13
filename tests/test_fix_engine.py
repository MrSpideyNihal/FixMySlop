"""Tests for core/fix_engine.py."""
from unittest.mock import MagicMock, patch
from core.fix_engine import FixEngine
from core.issue import Issue
from macros import SEVERITY_HIGH


class TestFixEngine:
    """Tests for the FixEngine class."""

    def test_generate_fix(self, mock_llm_client, tmp_path):
        """Should generate a diff string for an issue."""
        # Create a file for the issue to reference
        test_file = tmp_path / "test.py"
        test_file.write_text('x = 1\nprint(x)\n', encoding="utf-8")

        mock_llm_client.chat.return_value = "--- a/test.py\n+++ b/test.py\n@@ -1,2 +1,2 @@\n-x = 1\n+x: int = 1\n print(x)\n"

        issue = Issue(
            file_path=str(test_file),
            line_start=1,
            line_end=1,
            severity=SEVERITY_HIGH,
            title="Missing type annotation",
            description="Variable lacks type hint.",
            evidence="x = 1",
        )

        engine = FixEngine(mock_llm_client)
        diff = engine.generate_fix(issue)
        assert "---" in diff
        assert "+++" in diff
        assert issue.diff == diff

    def test_generate_fix_sets_diff_on_issue(self, mock_llm_client, tmp_path):
        """Should set the diff attribute on the issue object."""
        test_file = tmp_path / "test.py"
        test_file.write_text('pass\n', encoding="utf-8")

        mock_llm_client.chat.return_value = "diff content"

        issue = Issue(
            file_path=str(test_file),
            line_start=1,
            line_end=1,
            title="Test",
        )

        engine = FixEngine(mock_llm_client)
        engine.generate_fix(issue)
        assert issue.diff == "diff content"
