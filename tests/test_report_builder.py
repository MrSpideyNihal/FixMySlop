"""Tests for core/report_builder.py."""
from core.report_builder import ReportBuilder
from core.issue import Issue
from macros import (
    SEVERITY_CRITICAL, SEVERITY_HIGH, SEVERITY_MEDIUM,
    REPORT_FORMAT_MARKDOWN, REPORT_FORMAT_JSON, REPORT_FORMAT_HTML,
    APP_NAME,
)


class TestReportBuilder:
    """Tests for the ReportBuilder class."""

    def test_build_report(self, sample_issues):
        """Should build a valid ScanReport from issues."""
        builder = ReportBuilder()
        report = builder.build(
            repo_path="/tmp/test",
            issues=sample_issues,
            total_files=5,
            scanned_files=3,
            scan_time_s=10.0,
            model_used="test-model",
        )
        assert report.repo_path == "/tmp/test"
        assert len(report.issues) == len(sample_issues)
        assert report.slop_score >= 0
        assert report.slop_score <= 100

    def test_slop_score_empty(self):
        """Slop score should be 0 with no issues."""
        builder = ReportBuilder()
        score = builder._compute_slop_score([], 10)
        assert score == 0.0

    def test_slop_score_with_critical(self):
        """Slop score should be higher with critical issues."""
        builder = ReportBuilder()
        issues = [
            Issue(file_path="a.py", line_start=1, line_end=1, severity=SEVERITY_CRITICAL),
        ]
        score = builder._compute_slop_score(issues, 1)
        assert score > 0

    def test_export_markdown(self, sample_report):
        """Markdown export should contain the app name and issues."""
        builder = ReportBuilder()
        md = builder.export(sample_report, REPORT_FORMAT_MARKDOWN)
        assert APP_NAME in md
        assert "Issues" in md

    def test_export_json(self, sample_report):
        """JSON export should be valid JSON with repo_path."""
        builder = ReportBuilder()
        import json
        data = json.loads(builder.export(sample_report, REPORT_FORMAT_JSON))
        assert data["repo_path"] == sample_report.repo_path

    def test_export_html(self, sample_report):
        """HTML export should contain basic HTML structure."""
        builder = ReportBuilder()
        html = builder.export(sample_report, REPORT_FORMAT_HTML)
        assert "<html" in html
        assert APP_NAME in html
