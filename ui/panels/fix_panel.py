"""
Fix panel — side-by-side diff viewer with apply/reject per fix.
Generates fixes via LLM and shows them in the diff viewer.
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QSplitter, QFrame,
    QScrollArea,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject
from core.issue import Issue, ScanReport
from core.fix_engine import FixEngine
from core.llm_client import LLMClient
from core.patch_applier import PatchApplier
from ui.widgets.diff_viewer import DiffViewer
from ui.widgets.severity_badge import SeverityBadge
from ui.widgets.toast import ToastManager
from utils.config import Config
from utils.logger import get_logger

logger = get_logger(__name__)


class _FixWorker(QObject):
    """Background worker to generate a fix for an issue."""

    finished = pyqtSignal(str, object)   # diff, issue
    failed = pyqtSignal(str)

    def __init__(self, issue: Issue, config: Config):
        """Initialize fix worker."""
        super().__init__()
        self.issue = issue
        self.config = config

    def run(self):
        """Generate the fix."""
        try:
            client = LLMClient(
                base_url=self.config.base_url,
                api_key=self.config.api_key,
                model=self.config.model,
            )
            engine = FixEngine(client)
            diff = engine.generate_fix(self.issue)
            self.finished.emit(diff, self.issue)
        except Exception as e:
            self.failed.emit(str(e))


class FixPanel(QWidget):
    """
    Fix panel — lists issues on the left, shows diffs on the right.
    Generates and applies fixes per issue.
    """

    def __init__(self, config: Config, parent=None):
        """Initialize the fix panel."""
        super().__init__(parent)
        self.config = config
        self._report = None
        self._thread = None
        self._worker = None
        self._current_issue = None
        self._build_ui()

    def _build_ui(self):
        """Build the fix panel layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QWidget()
        header.setFixedHeight(64)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(24, 0, 24, 0)

        title = QLabel("Fix Engine")
        title.setObjectName("SectionTitle")
        h_layout.addWidget(title)

        h_layout.addStretch()
        self._status = QLabel("")
        self._status.setStyleSheet("color: #8892a4;")
        h_layout.addWidget(self._status)
        layout.addWidget(header)

        # Splitter
        splitter = QSplitter(Qt.Horizontal)

        # Left: issue list
        self._issue_list = QListWidget()
        self._issue_list.currentRowChanged.connect(self._on_issue_selected)
        splitter.addWidget(self._issue_list)

        # Right: diff viewer + actions
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(12)

        self._diff_viewer = DiffViewer()
        right_layout.addWidget(self._diff_viewer, 1)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self._generate_btn = QPushButton("Generate Fix")
        self._generate_btn.setObjectName("PrimaryButton")
        self._generate_btn.clicked.connect(self._generate_fix)
        btn_row.addWidget(self._generate_btn)

        self._apply_btn = QPushButton("Apply Fix")
        self._apply_btn.setObjectName("SecondaryButton")
        self._apply_btn.setEnabled(False)
        self._apply_btn.clicked.connect(self._apply_fix)
        btn_row.addWidget(self._apply_btn)

        self._reject_btn = QPushButton("Reject")
        self._reject_btn.setObjectName("DangerButton")
        self._reject_btn.setEnabled(False)
        self._reject_btn.clicked.connect(self._reject_fix)
        btn_row.addWidget(self._reject_btn)

        btn_row.addStretch()
        right_layout.addLayout(btn_row)

        splitter.addWidget(right)
        splitter.setSizes([300, 700])
        layout.addWidget(splitter)

    def load_report(self, report: ScanReport):
        """Load issues from a scan report into the issue list."""
        self._report = report
        self._issue_list.clear()
        for issue in report.issues:
            item = QListWidgetItem(f"[{issue.severity}] {issue.title}")
            item.setData(Qt.UserRole, issue)
            self._issue_list.addItem(item)
        self._status.setText(f"{len(report.issues)} issues available for fixing")

    def _on_issue_selected(self, row: int):
        """Handle issue selection from the list."""
        if row < 0:
            return
        item = self._issue_list.item(row)
        self._current_issue = item.data(Qt.UserRole)

        if self._current_issue.diff:
            self._diff_viewer.load_diff(self._current_issue.diff)
            self._apply_btn.setEnabled(True)
            self._reject_btn.setEnabled(True)
        else:
            self._diff_viewer.load_before_after(
                f"Select 'Generate Fix' to create a diff for:\n\n"
                f"  {self._current_issue.title}\n"
                f"  {self._current_issue.file_path}\n"
                f"  Lines {self._current_issue.line_start}-{self._current_issue.line_end}",
                "",
            )
            self._apply_btn.setEnabled(False)
            self._reject_btn.setEnabled(False)

    def _generate_fix(self):
        """Generate a fix for the currently selected issue."""
        if not self._current_issue:
            return

        self._generate_btn.setEnabled(False)
        self._generate_btn.setText("Generating...")
        self._status.setText("Generating fix...")

        self._thread = QThread()
        self._worker = _FixWorker(self._current_issue, self.config)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_fix_generated)
        self._worker.failed.connect(self._on_fix_failed)
        self._thread.start()

    def _on_fix_generated(self, diff: str, issue: Issue):
        """Handle successful fix generation."""
        self._generate_btn.setEnabled(True)
        self._generate_btn.setText("Generate Fix")
        self._diff_viewer.load_diff(diff)
        self._apply_btn.setEnabled(True)
        self._reject_btn.setEnabled(True)
        self._status.setText("Fix generated — review the diff")
        self._thread.quit()

    def _on_fix_failed(self, error: str):
        """Handle fix generation failure."""
        self._generate_btn.setEnabled(True)
        self._generate_btn.setText("Generate Fix")
        self._status.setText(f"Fix generation failed: {error}")
        self._thread.quit()

    def _apply_fix(self):
        """Apply the generated fix to the file."""
        if not self._current_issue or not self._current_issue.diff:
            return

        applier = PatchApplier()
        success = applier.apply(self._current_issue.file_path, self._current_issue.diff)

        if success:
            self._current_issue.applied = True
            self._status.setText("Fix applied successfully!")
            self._apply_btn.setEnabled(False)
        else:
            self._status.setText("Failed to apply fix — check the diff")

    def _reject_fix(self):
        """Reject the current fix and clear the diff viewer."""
        if self._current_issue:
            self._current_issue.diff = ""
            self._diff_viewer.load_before_after("Fix rejected.", "")
            self._apply_btn.setEnabled(False)
            self._reject_btn.setEnabled(False)
            self._status.setText("Fix rejected")
