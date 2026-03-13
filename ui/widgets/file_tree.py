"""
File tree widget — custom QTreeWidget showing scanned files with issue counts.
"""
from pathlib import Path
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem
from PyQt5.QtCore import pyqtSignal
from macros import SEVERITY_COLORS


class FileTreeWidget(QTreeWidget):
    """
    Custom tree showing scanned files grouped by directory,
    with issue counts and severity indicators per file.
    """

    file_selected = pyqtSignal(str)  # Emits file path when selected

    def __init__(self, parent=None):
        """Initialize the file tree widget."""
        super().__init__(parent)
        self.setHeaderLabels(["File", "Issues", "Severity"])
        self.setColumnWidth(0, 250)
        self.setColumnWidth(1, 60)
        self.setColumnWidth(2, 80)
        self.setRootIsDecorated(True)
        self.setAlternatingRowColors(False)
        self.itemClicked.connect(self._on_item_clicked)

    def load_issues(self, issues: list):
        """Populate the tree from a list of Issue objects."""
        self.clear()
        # Group issues by file
        file_groups: dict[str, list] = {}
        for issue in issues:
            file_groups.setdefault(issue.file_path, []).append(issue)

        # Group files by directory
        dir_groups: dict[str, dict] = {}
        for fpath, file_issues in file_groups.items():
            p = Path(fpath)
            dir_name = str(p.parent)
            dir_groups.setdefault(dir_name, {})[fpath] = file_issues

        for dir_name, files in sorted(dir_groups.items()):
            dir_item = QTreeWidgetItem([dir_name, "", ""])
            dir_item.setExpanded(True)
            self.addTopLevelItem(dir_item)

            for fpath, file_issues in sorted(files.items()):
                count = len(file_issues)
                max_severity = self._max_severity(file_issues)
                file_item = QTreeWidgetItem([
                    Path(fpath).name,
                    str(count),
                    max_severity,
                ])
                file_item.setData(0, 256, fpath)  # Store full path as user data
                color = SEVERITY_COLORS.get(max_severity, "#90A4AE")
                file_item.setForeground(2, self._make_color(color))
                dir_item.addChild(file_item)

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Emit file_selected signal when a file item is clicked."""
        fpath = item.data(0, 256)
        if fpath:
            self.file_selected.emit(fpath)

    def _max_severity(self, issues: list) -> str:
        """Return the highest severity from a list of issues."""
        from macros import SEVERITY_ORDER
        for sev in SEVERITY_ORDER:
            if any(i.severity == sev for i in issues):
                return sev
        return "INFO"

    @staticmethod
    def _make_color(hex_color: str):
        """Create a QColor from a hex string."""
        from PyQt5.QtGui import QColor
        return QColor(hex_color)
