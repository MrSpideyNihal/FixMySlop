"""
ScanPanel — folder picker, model selector, scan options, run button.
Runs scan in a QThread so the UI stays responsive.
All scan results emitted via signals.
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QFileDialog, QLabel, QCheckBox, QProgressBar,
    QFrame, QScrollArea,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject
from ui.widgets.model_selector import ModelSelectorWidget
from core.scanner import Scanner
from core.analyzer import Analyzer
from core.llm_client import LLMClient
from core.report_builder import ReportBuilder
from core.issue import Issue, ScanReport
from utils.config import Config
from utils.logger import get_logger
import time

logger = get_logger(__name__)


class ScanWorker(QObject):
    """Runs the full scan pipeline in a background thread."""

    progress = pyqtSignal(int, int, str)     # current, total, filename
    complete = pyqtSignal(object)             # ScanReport
    failed = pyqtSignal(str)                  # error message

    def __init__(self, repo_path: str, config: Config):
        """Initialize scan worker with repo path and config."""
        super().__init__()
        self.repo_path = repo_path
        self.config = config

    def run(self):
        """Execute the full scan pipeline."""
        try:
            client = None
            if self.config.get("use_llm", True):
                client = LLMClient(
                    base_url=self.config.base_url,
                    api_key=self.config.api_key,
                    model=self.config.model,
                )
                if not client.is_available():
                    self.failed.emit(
                        f"Cannot reach LLM backend at {self.config.base_url}. "
                        "Is Ollama running?"
                    )
                    return

            scanner = Scanner(self.repo_path)
            analyzer = Analyzer(
                llm_client=client,
                use_static_tools=self.config.get("use_ruff", True),
            )
            builder = ReportBuilder()
            all_issues: list[Issue] = []
            start = time.time()

            for file_path, content in scanner.scan(
                progress_callback=lambda c, t, n: self.progress.emit(c, t, n)
            ):
                issues = analyzer.analyze_file(file_path, content)
                all_issues.extend(issues)

            report = builder.build(
                repo_path=self.repo_path,
                issues=all_issues,
                total_files=scanner.file_count,
                scanned_files=scanner.file_count,
                scan_time_s=time.time() - start,
                model_used=self.config.model,
            )
            self.complete.emit(report)
        except Exception as e:
            logger.error("Scan failed: %s", e)
            self.failed.emit(str(e))


class ScanPanel(QWidget):
    """The scan configuration and execution panel."""

    scan_complete = pyqtSignal(object)    # ScanReport
    scan_failed = pyqtSignal(str)

    def __init__(self, config: Config, parent=None):
        """Initialize scan panel with config."""
        super().__init__(parent)
        self.config = config
        self._thread = None
        self._worker = None
        self._build_ui()

    def _build_ui(self):
        """Build the scan panel layout."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(48, 40, 48, 40)
        layout.setSpacing(20)

        # Title
        title = QLabel("Scan Repository")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        subtitle = QLabel("Select a codebase to analyze for bugs, security issues, and AI debt.")
        subtitle.setObjectName("SectionSubtitle")
        layout.addWidget(subtitle)

        # Repository path
        path_label = QLabel("Repository Path")
        path_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(path_label)

        path_row = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Path to repo or folder...")
        browse_btn = QPushButton("Browse")
        browse_btn.setObjectName("SecondaryButton")
        browse_btn.clicked.connect(self._browse)
        path_row.addWidget(self.path_input, 1)
        path_row.addWidget(browse_btn)
        layout.addLayout(path_row)

        # Model selection
        layout.addSpacing(8)
        model_label = QLabel("LLM Model")
        model_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(model_label)

        self.model_selector = ModelSelectorWidget(self.config)
        self.model_selector.model_changed.connect(self._update_estimate)
        layout.addWidget(self.model_selector)

        # Scan estimate label (shown under model selector)
        self.estimate_label = QLabel("")
        self.estimate_label.setStyleSheet(
            "background: #141820; border: 1px solid #1e2433; border-radius: 8px; "
            "padding: 12px 16px; color: #8892a4; font-size: 12px;"
        )
        self.estimate_label.setWordWrap(True)
        self.estimate_label.setVisible(False)
        layout.addWidget(self.estimate_label)

        # Analysis options
        layout.addSpacing(8)
        options_label = QLabel("Analysis Options")
        options_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(options_label)

        self.use_ruff = QCheckBox("Ruff (Python linting)")
        self.use_bandit = QCheckBox("Bandit (Security analysis)")
        self.use_semgrep = QCheckBox("Semgrep (Pattern rules)")
        self.use_llm = QCheckBox("LLM Deep Analysis")

        self.use_ruff.setChecked(self.config.get("use_ruff", True))
        self.use_bandit.setChecked(self.config.get("use_bandit", True))
        self.use_semgrep.setChecked(self.config.get("use_semgrep", False))
        self.use_llm.setChecked(True)
        self.use_llm.toggled.connect(self._update_estimate)

        for cb in [self.use_ruff, self.use_bandit, self.use_semgrep, self.use_llm]:
            layout.addWidget(cb)

        # Progress area
        layout.addSpacing(16)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #8892a4;")
        layout.addWidget(self.status_label)

        layout.addStretch()

        # Scan button
        self.scan_btn = QPushButton("Start Scan")
        self.scan_btn.setObjectName("PrimaryButton")
        self.scan_btn.setFixedHeight(48)
        self.scan_btn.clicked.connect(self._start_scan)
        layout.addWidget(self.scan_btn)

        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _browse(self):
        """Open folder picker dialog."""
        path = QFileDialog.getExistingDirectory(self, "Select Repository")
        if path:
            self.path_input.setText(path)
            self._update_estimate()

    def _update_estimate(self):
        """Refresh the scan time estimate label."""
        path = self.path_input.text().strip()
        if not path or not self.use_llm.isChecked():
            self.estimate_label.setVisible(False)
            return

        from pathlib import Path as P
        from utils.system_info import estimate_scan_time, _detect_gpu
        repo = P(path)
        if not repo.exists():
            self.estimate_label.setVisible(False)
            return

        try:
            scanner = Scanner(str(repo))
            total = scanner.file_count
            model = self.model_selector.selected_model
            gpu = _detect_gpu()
            est = estimate_scan_time(total, model, gpu["vram_gb"])

            self.estimate_label.setText(
                f"📊  {total} files  •  {est['hardware']}  •  "
                f"Estimated: {est['total_human']}\n"
                f"Tip: Uncheck LLM Deep Analysis for instant static-only scan"
            )
            self.estimate_label.setVisible(True)
        except Exception:
            self.estimate_label.setVisible(False)

    def _start_scan(self):
        """Launch the scan in a background thread."""
        path = self.path_input.text().strip()
        if not path:
            self.status_label.setText("Please select a folder first.")
            return

        self.scan_btn.setEnabled(False)
        self.scan_btn.setText("Scanning...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Initializing scan...")

        # Update config with current selections
        self.config.set("use_llm", self.use_llm.isChecked())

        self._thread = QThread()
        self._worker = ScanWorker(path, self.config)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.complete.connect(self._on_complete)
        self._worker.failed.connect(self._on_failed)
        self._thread.start()

    def _on_progress(self, current: int, total: int, filename: str):
        """Update progress bar during scan."""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_label.setText(f"Scanning: {filename} ({current}/{total})")

    def _on_complete(self, report: ScanReport):
        """Handle scan completion."""
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("Start Scan")
        self.progress_bar.setVisible(False)
        self.status_label.setText(
            f"Done — {len(report.issues)} issues found in {report.scan_time_s:.1f}s"
        )
        self._thread.quit()
        self.scan_complete.emit(report)

    def _on_failed(self, error: str):
        """Handle scan failure."""
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("Start Scan")
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Error: {error}")
        self._thread.quit()
        self.scan_failed.emit(error)
