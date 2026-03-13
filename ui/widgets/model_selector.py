"""
Model selector widget — dropdown that queries backend for available models.
"""
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QComboBox, QPushButton
from PyQt5.QtCore import QThread, pyqtSignal, QObject
from core.model_detector import ModelDetector
from utils.config import Config
from utils.logger import get_logger

logger = get_logger(__name__)


class _ModelFetchWorker(QObject):
    """Background worker to fetch models from backend."""

    finished = pyqtSignal(list)  # list of model names
    error = pyqtSignal(str)

    def __init__(self, base_url: str):
        """Initialize worker with backend URL."""
        super().__init__()
        self.base_url = base_url

    def run(self):
        """Fetch models from the backend."""
        try:
            detector = ModelDetector()
            models = detector.get_all_models(self.base_url)
            self.finished.emit(models)
        except Exception as e:
            self.error.emit(str(e))


class ModelSelectorWidget(QWidget):
    """
    Dropdown for selecting an LLM model.
    Has a refresh button that queries the backend for available models.
    """

    model_changed = pyqtSignal(str)

    def __init__(self, config: Config, parent=None):
        """Initialize model selector with config for defaults."""
        super().__init__(parent)
        self.config = config
        self._thread = None
        self._worker = None
        self._build_ui()

    def _build_ui(self):
        """Build the selector layout."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.combo = QComboBox()
        self.combo.setEditable(True)
        self.combo.setMinimumWidth(200)
        self.combo.setCurrentText(self.config.model)
        self.combo.currentTextChanged.connect(self.model_changed.emit)
        layout.addWidget(self.combo, 1)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setObjectName("SecondaryButton")
        self.refresh_btn.clicked.connect(self.refresh_models)
        layout.addWidget(self.refresh_btn)

    def refresh_models(self):
        """Fetch available models from the backend in a background thread."""
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("Loading...")

        self._thread = QThread()
        self._worker = _ModelFetchWorker(self.config.base_url)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_models_fetched)
        self._worker.error.connect(self._on_fetch_error)
        self._thread.start()

    def _on_models_fetched(self, models: list[str]):
        """Handle successful model fetch."""
        current = self.combo.currentText()
        self.combo.clear()
        self.combo.addItems(models)
        if current in models:
            self.combo.setCurrentText(current)
        elif models:
            self.combo.setCurrentText(models[0])

        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("Refresh")
        self._thread.quit()
        logger.info("Fetched %d models from backend", len(models))

    def _on_fetch_error(self, error: str):
        """Handle model fetch failure."""
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("Refresh")
        self._thread.quit()
        logger.warning("Failed to fetch models: %s", error)

    @property
    def selected_model(self) -> str:
        """Return the currently selected model name."""
        return self.combo.currentText()
