"""Tests for core/report_builder.py."""
import sys
import types
from pathlib import Path
from core.report_builder import ReportBuilder, _strip_emojis_for_pdf
from core.issue import Issue
from macros import (
    SEVERITY_CRITICAL, SEVERITY_HIGH, SEVERITY_MEDIUM,
    REPORT_FORMAT_MARKDOWN, REPORT_FORMAT_JSON, REPORT_FORMAT_HTML,
    APP_NAME, SCAN_MODE_TURBO,
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

    def test_strip_emojis_for_pdf(self):
        """Emoji-rich strings should be converted to PDF-safe labels."""
        text = "⚡ 🔍 ⚠ ✓ ⏳ 🔒 📊"
        cleaned = _strip_emojis_for_pdf(text)
        assert "⚡" not in cleaned
        assert "🔍" not in cleaned
        assert "⚠" not in cleaned
        assert "✓" not in cleaned
        assert "⏳" not in cleaned
        assert "🔒" not in cleaned
        assert "📊" not in cleaned
        assert "[TURBO]" in cleaned
        assert "[DEEP]" in cleaned
        assert "[!]" in cleaned
        assert "[OK]" in cleaned
        assert "[...]" in cleaned
        assert "[SEC]" in cleaned
        assert "[STATS]" in cleaned

    def test_export_pdf_strips_emoji_before_canvas_write(self, monkeypatch, sample_report, tmp_path):
        """PDF export should sanitize unsupported emoji characters before writing cells."""
        captured_text = []

        class FakeFPDF:
            def set_auto_page_break(self, auto=True, margin=15):
                return None

            def add_page(self):
                return None

            def set_font(self, family, style="", size=12):
                return None

            def cell(self, *args, **kwargs):
                text = kwargs.get("txt")
                if text is None and len(args) >= 3:
                    text = args[2]
                captured_text.append(str(text) if text is not None else "")

            def ln(self, h=None):
                return None

            def output(self, output_path):
                Path(output_path).write_text("fake-pdf", encoding="utf-8")

        fake_fpdf_module = types.SimpleNamespace(FPDF=FakeFPDF)
        monkeypatch.setitem(sys.modules, "fpdf", fake_fpdf_module)

        sample_report.scan_mode = SCAN_MODE_TURBO
        sample_report.model_used = "qwen2.5-coder:3b ⚡"
        sample_report.issues[0].title = "Unsafe path ⚠"
        sample_report.issues[0].category = "Security 🔒"

        output_path = tmp_path / "report.pdf"
        builder = ReportBuilder()
        builder.export_pdf(sample_report, str(output_path))

        assert output_path.exists()
        all_written = "\n".join(captured_text)
        for emoji in ("⚡", "🔍", "⚠", "✓", "⏳", "🔒", "📊"):
            assert emoji not in all_written
        assert "[TURBO]" in all_written
        assert "[!]" in all_written
        assert "[SEC]" in all_written
