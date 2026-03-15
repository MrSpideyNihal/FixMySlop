"""
Report panel — displays audit results with file tree, issue list,
and severity badges. Allows filtering and sorting.
"""
from datetime import datetime
from pathlib import Path
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSplitter,
    QScrollArea, QFrame, QComboBox, QPushButton, QFileDialog, QMessageBox,
)
from PyQt5.QtCore import Qt, pyqtSignal
from core.issue import ScanReport
from core.report_builder import ReportBuilder
from ui.widgets.file_tree import FileTreeWidget
from ui.widgets.issue_card import IssueCard
from ui.widgets.severity_badge import SeverityBadge
from utils.config import Config
from macros import (
    SEVERITY_ORDER,
    SCAN_MODE_DEEP,
    REPORT_FORMAT_MARKDOWN,
    REPORT_FORMAT_HTML,
    REPORT_FORMAT_JSON,
    REPORT_FORMAT_CSV,
    REPORT_FORMAT_PDF,
    REPORTS_DIR,
)


class ReportPanel(QWidget):
    """
    Audit results panel — file tree on left, issue cards on right.
    Supports filtering by severity and file.
    """

    fix_requested = pyqtSignal(object)  # Issue

    def __init__(self, config: Config, parent=None):
        """Initialize the report panel."""
        super().__init__(parent)
        self.config = config
        self._report = None
        self._report_builder = ReportBuilder()
        self._build_ui()

    def _build_ui(self):
        """Build the report panel layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header bar
        header = QWidget()
        header.setFixedHeight(64)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 0, 24, 0)

        title = QLabel("Audit Report")
        title.setObjectName("SectionTitle")
        header_layout.addWidget(title)
        header_layout.addStretch()

        # Severity filter
        self._filter_combo = QComboBox()
        self._filter_combo.addItem("All Severities")
        for sev in SEVERITY_ORDER:
            self._filter_combo.addItem(sev)
        self._filter_combo.currentTextChanged.connect(self._apply_filter)
        header_layout.addWidget(self._filter_combo)

        self._export_format_combo = QComboBox()
        self._export_format_combo.addItem("Markdown (.md)", (REPORT_FORMAT_MARKDOWN, "md"))
        self._export_format_combo.addItem("HTML (.html)", (REPORT_FORMAT_HTML, "html"))
        self._export_format_combo.addItem("JSON (.json)", (REPORT_FORMAT_JSON, "json"))
        self._export_format_combo.addItem("CSV (.csv)", (REPORT_FORMAT_CSV, "csv"))
        self._export_format_combo.addItem("PDF (.pdf)", (REPORT_FORMAT_PDF, "pdf"))
        header_layout.addWidget(self._export_format_combo)

        self._download_btn = QPushButton("Download Report")
        self._download_btn.setObjectName("SecondaryButton")
        self._download_btn.setEnabled(False)
        self._download_btn.clicked.connect(self._download_report)
        header_layout.addWidget(self._download_btn)

        # Stats labels
        self._stats_label = QLabel("")
        self._stats_label.setStyleSheet("color: #8892a4;")
        header_layout.addWidget(self._stats_label)

        layout.addWidget(header)

        # Splitter: file tree | issue list
        splitter = QSplitter(Qt.Horizontal)

        # Left: File tree
        self._file_tree = FileTreeWidget()
        self._file_tree.file_selected.connect(self._on_file_selected)
        splitter.addWidget(self._file_tree)

        # Right: Issue cards
        right_widget = QWidget()
        self._issues_layout = QVBoxLayout(right_widget)
        self._issues_layout.setContentsMargins(16, 16, 16, 16)
        self._issues_layout.setSpacing(12)
        self._issues_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(right_widget)
        splitter.addWidget(scroll)

        splitter.setSizes([300, 700])
        layout.addWidget(splitter)

    def load_report(self, report: ScanReport):
        """Load a scan report and display its contents."""
        self._report = report
        self._download_btn.setEnabled(True)
        self._file_tree.load_issues(report.issues)
        mode_label = "DEEP 🔍" if report.scan_mode == SCAN_MODE_DEEP else "TURBO ⚡"
        self._stats_label.setText(
            f"Mode: {mode_label}  •  "
            f"{len(report.issues)} issues  •  "
            f"Slop Score: {report.slop_score}/100  •  "
            f"{report.scanned_files} files  •  "
            f"{report.scan_time_s:.1f}s"
        )
        self._display_issues(report.issues)

    def _display_issues(self, issues: list):
        """Clear and re-render issue cards."""
        # Clear existing
        while self._issues_layout.count() > 1:
            item = self._issues_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not issues:
            empty = QLabel("No issues found! Your code looks clean. 🎉")
            empty.setStyleSheet("color: #8892a4; padding: 48px;")
            empty.setAlignment(Qt.AlignCenter)
            self._issues_layout.insertWidget(0, empty)
            return

        for issue in sorted(issues, key=lambda i: SEVERITY_ORDER.index(i.severity)
                            if i.severity in SEVERITY_ORDER else 99):
            card = IssueCard(issue)
            card.fix_requested.connect(self.fix_requested.emit)
            self._issues_layout.insertWidget(self._issues_layout.count() - 1, card)

    def _apply_filter(self, severity: str):
        """Filter displayed issues by severity."""
        if not self._report:
            return
        if severity == "All Severities":
            self._display_issues(self._report.issues)
        else:
            filtered = [i for i in self._report.issues if i.severity == severity]
            self._display_issues(filtered)

    def _on_file_selected(self, file_path: str):
        """Filter issues to show only those from the selected file."""
        if not self._report:
            return
        filtered = [i for i in self._report.issues if i.file_path == file_path]
        self._display_issues(filtered)

    def _download_report(self):
        """Save the current report in the selected output format."""
        if not self._report:
            QMessageBox.information(self, "No Report", "Run a scan first to export a report.")
            return

        format_data = self._export_format_combo.currentData()
        if not format_data:
            return

        report_format, extension = format_data
        file_filters = {
            "md": "Markdown Files (*.md)",
            "html": "HTML Files (*.html)",
            "json": "JSON Files (*.json)",
            "csv": "CSV Files (*.csv)",
            "pdf": "PDF Files (*.pdf)",
        }

        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"fixmyslop_report_{timestamp}.{extension}"
        default_path = REPORTS_DIR / default_name

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Audit Report",
            str(default_path),
            file_filters.get(extension, "All Files (*)"),
        )
        if not save_path:
            return

        output_path = Path(save_path)
        if output_path.suffix.lower() != f".{extension}":
            output_path = output_path.with_suffix(f".{extension}")

        try:
            if report_format == REPORT_FORMAT_PDF:
                self._report_builder.export_pdf(self._report, str(output_path))
            else:
                exported = self._report_builder.export(self._report, fmt=report_format)
                output_path.write_text(exported, encoding="utf-8")
            QMessageBox.information(
                self,
                "Report Saved",
                f"Saved report to:\n{output_path}",
            )
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Export Failed",
                f"Could not save report:\n{exc}",
            )
