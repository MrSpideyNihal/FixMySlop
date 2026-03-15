"""
Report builder — takes a list of Issue objects and assembles
a structured ScanReport with scoring and export methods.
"""
import csv
import io
import json
import dataclasses
from datetime import datetime
from core.issue import Issue, ScanReport
from macros import (
    SEVERITY_CRITICAL, SEVERITY_HIGH, SEVERITY_MEDIUM,
    REPORT_FORMAT_MARKDOWN, REPORT_FORMAT_HTML, REPORT_FORMAT_JSON,
    REPORT_FORMAT_CSV, REPORT_FORMAT_PDF,
    APP_NAME, APP_VERSION,
    SCAN_MODE_TURBO, SCAN_MODE_DEEP, DEFAULT_SCAN_MODE,
)
from utils.logger import get_logger

logger = get_logger(__name__)


def _scan_mode_summary(scan_mode: str) -> str:
    """Format the scan mode label for summaries and exports."""
    return "DEEP 🔍" if scan_mode == SCAN_MODE_DEEP else "TURBO ⚡"


class ReportBuilder:
    """
    Assembles a ScanReport from issues and exports to
    Markdown, HTML, JSON, CSV, or PDF.
    Computes a 'slop score' (0-100) representing overall debt level.
    """

    SEVERITY_WEIGHTS = {
        SEVERITY_CRITICAL: 10,
        SEVERITY_HIGH: 5,
        SEVERITY_MEDIUM: 2,
    }

    def build(
        self,
        repo_path: str,
        issues: list[Issue],
        total_files: int,
        scanned_files: int,
        scan_time_s: float,
        model_used: str,
        scan_mode: str = DEFAULT_SCAN_MODE,
    ) -> ScanReport:
        """Build and return a ScanReport from raw scan data."""
        report = ScanReport(
            repo_path=repo_path,
            scan_time_s=scan_time_s,
            total_files=total_files,
            scanned_files=scanned_files,
            issues=issues,
            model_used=model_used,
            scan_mode=scan_mode,
        )
        report.slop_score = self._compute_slop_score(issues, scanned_files)
        logger.info(
            "Report built: %d issues, slop score %.1f",
            len(issues), report.slop_score,
        )
        return report

    def _compute_slop_score(self, issues: list[Issue], file_count: int) -> float:
        """Compute 0-100 slop score based on weighted issue counts per file."""
        if file_count == 0:
            return 0.0
        total_weight = sum(
            self.SEVERITY_WEIGHTS.get(i.severity, 1) for i in issues
        )
        score = min(100.0, (total_weight / (file_count * 10)) * 100)
        return round(score, 1)

    def export(self, report: ScanReport, fmt: str = REPORT_FORMAT_MARKDOWN) -> str:
        """Export the report to the requested text format."""
        if fmt == REPORT_FORMAT_JSON:
            return self._to_json(report)
        elif fmt == REPORT_FORMAT_HTML:
            return self._to_html(report)
        elif fmt == REPORT_FORMAT_CSV:
            return self._to_csv(report)
        elif fmt == REPORT_FORMAT_PDF:
            return self._to_html(report)
        else:
            return self._to_markdown(report)

    def export_pdf(self, report: ScanReport, output_path: str):
        """Export report as a PDF file. Requires fpdf2."""
        try:
            from fpdf import FPDF
        except ImportError:
            logger.warning("fpdf2 not installed — saving as HTML instead")
            html = self._to_html(report)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html)
            logger.info("Install fpdf2 for PDF: pip install fpdf2")
            return

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        # Title
        pdf.set_font("Helvetica", "B", 20)
        pdf.cell(0, 12, f"{APP_NAME} Audit Report", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

        # Metadata
        pdf.set_font("Helvetica", "", 10)
        meta = [
            f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Repo: {report.repo_path}",
            f"Slop Score: {report.slop_score}/100",
            f"Mode: {_scan_mode_summary(report.scan_mode)}",
            f"Model: {report.model_used}",
            f"Files: {report.scanned_files}/{report.total_files}",
            f"Issues: {len(report.issues)}",
            f"Scan Time: {report.scan_time_s:.1f}s",
        ]
        for line in meta:
            pdf.cell(0, 6, line, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(6)

        # Issues table header
        pdf.set_font("Helvetica", "B", 9)
        col_w = [22, 55, 22, 30, 60]
        headers = ["Severity", "File", "Lines", "Category", "Title"]
        for w, h in zip(col_w, headers):
            pdf.cell(w, 8, h, border=1)
        pdf.ln()

        # Issues table rows
        pdf.set_font("Helvetica", "", 8)
        for issue in sorted(report.issues, key=lambda i: i.severity):
            pdf.cell(col_w[0], 7, issue.severity, border=1)
            pdf.cell(col_w[1], 7, str(issue.file_path)[-30:], border=1)
            pdf.cell(col_w[2], 7, f"{issue.line_start}-{issue.line_end}", border=1)
            pdf.cell(col_w[3], 7, issue.category[:16], border=1)
            pdf.cell(col_w[4], 7, issue.title[:32], border=1)
            pdf.ln()

        pdf.output(output_path)
        logger.info("PDF report saved: %s", output_path)

    def _to_csv(self, report: ScanReport) -> str:
        """Export report as CSV."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Severity", "File", "Line Start", "Line End",
            "Category", "Rule ID", "Title", "Description",
            "Evidence", "Source Tool",
        ])
        for issue in sorted(report.issues, key=lambda i: i.severity):
            writer.writerow([
                issue.severity,
                issue.file_path,
                issue.line_start,
                issue.line_end,
                issue.category,
                issue.rule_id,
                issue.title,
                issue.description,
                issue.evidence,
                issue.source_tool,
            ])
        return output.getvalue()

    def _to_markdown(self, report: ScanReport) -> str:
        """Export report as Markdown."""
        lines = [
            f"# {APP_NAME} Audit Report",
            f"**Version:** {APP_VERSION}  ",
            f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}  ",
            f"**Repo:** `{report.repo_path}`  ",
            f"**Slop Score:** {report.slop_score}/100  ",
            f"**Mode:** {_scan_mode_summary(report.scan_mode)}  ",
            f"**Model:** {report.model_used}  ",
            f"**Files Scanned:** {report.scanned_files}/{report.total_files}  ",
            f"**Issues Found:** {len(report.issues)}  ",
            "",
            "## Issues",
            "",
        ]
        for issue in sorted(report.issues, key=lambda i: i.severity):
            lines += [
                f"### [{issue.severity}] {issue.title}",
                f"**File:** `{issue.file_path}` (lines {issue.line_start}-{issue.line_end})  ",
                f"**Category:** {issue.category}  ",
                f"**Rule:** `{issue.rule_id}`  ",
                "",
                issue.description,
                "",
                "```",
                issue.evidence,
                "```",
                "",
            ]
        return "\n".join(lines)

    def _to_json(self, report: ScanReport) -> str:
        """Export report as JSON."""
        return json.dumps(dataclasses.asdict(report), indent=2)

    def _to_html(self, report: ScanReport) -> str:
        """Export report as HTML."""
        md_content = self._to_markdown(report)
        return (
            "<!DOCTYPE html>\n"
            "<html lang='en'>\n"
            "<head>\n"
            f"  <title>{APP_NAME} Audit Report</title>\n"
            "  <meta charset='utf-8'>\n"
            "  <style>\n"
            "    body { font-family: -apple-system, sans-serif; max-width: 900px; "
            "margin: 0 auto; padding: 20px; background: #0f1117; color: #e2e8f0; }\n"
            "    pre { background: #1a1f2e; padding: 16px; border-radius: 8px; "
            "overflow-x: auto; }\n"
            "    code { font-family: 'JetBrains Mono', monospace; }\n"
            "    h1 { color: #7c6af7; }\n"
            "    h3 { border-bottom: 1px solid #2d3452; padding-bottom: 4px; }\n"
            "  </style>\n"
            "</head>\n"
            "<body>\n"
            f"  <pre>{md_content}</pre>\n"
            "</body>\n"
            "</html>"
        )
