"""
Settings panel — model config, backend URL, API key, theme, preferences.
All changes auto-save to ~/.fixmyslop/config.yaml.
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QCheckBox, QGroupBox, QFormLayout,
    QScrollArea, QFrame, QDoubleSpinBox,
)
from PyQt5.QtCore import pyqtSignal
from utils.config import Config
from ui.theme import get_available_themes
from macros import (
    KNOWN_BACKENDS, DEFAULT_MODEL, DEFAULT_BASE_URL,
    DEFAULT_API_KEY, DEFAULT_TEMPERATURE,
)
from utils.logger import get_logger

logger = get_logger(__name__)


class SettingsPanel(QWidget):
    """Settings panel for model, backend, theme, and preferences."""

    theme_changed = pyqtSignal(str)

    def __init__(self, config: Config, parent=None):
        """Initialize settings panel with config."""
        super().__init__(parent)
        self.config = config
        self._build_ui()

    def _build_ui(self):
        """Build the settings layout."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(48, 40, 48, 40)
        layout.setSpacing(24)

        # Title
        title = QLabel("Settings")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        subtitle = QLabel("Configure your LLM backend, analysis preferences, and UI theme.")
        subtitle.setObjectName("SectionSubtitle")
        layout.addWidget(subtitle)

        # ─── LLM Backend ────────────────────────────────────────────────
        llm_group = QGroupBox("LLM Backend")
        llm_layout = QFormLayout(llm_group)
        llm_layout.setSpacing(12)

        self._backend_combo = QComboBox()
        for name, url in KNOWN_BACKENDS.items():
            self._backend_combo.addItem(f"{name} ({url})", url)
        self._backend_combo.addItem("Custom", "")
        self._backend_combo.currentIndexChanged.connect(self._on_backend_changed)
        llm_layout.addRow("Backend:", self._backend_combo)

        self._url_input = QLineEdit(self.config.base_url)
        self._url_input.setPlaceholderText("http://localhost:11434/v1")
        llm_layout.addRow("API URL:", self._url_input)

        self._api_key_input = QLineEdit(self.config.api_key)
        self._api_key_input.setPlaceholderText("ollama")
        self._api_key_input.setEchoMode(QLineEdit.Password)
        llm_layout.addRow("API Key:", self._api_key_input)

        self._model_input = QLineEdit(self.config.model)
        self._model_input.setPlaceholderText(DEFAULT_MODEL)
        llm_layout.addRow("Model:", self._model_input)

        self._temp_spin = QDoubleSpinBox()
        self._temp_spin.setRange(0.0, 2.0)
        self._temp_spin.setSingleStep(0.1)
        self._temp_spin.setValue(self.config.temperature)
        llm_layout.addRow("Temperature:", self._temp_spin)

        layout.addWidget(llm_group)

        # ─── Static Analysis Tools ───────────────────────────────────────
        tools_group = QGroupBox("Static Analysis Tools")
        tools_layout = QVBoxLayout(tools_group)

        self._ruff_cb = QCheckBox("Enable Ruff (Python linting)")
        self._ruff_cb.setChecked(self.config.get("use_ruff", True))
        tools_layout.addWidget(self._ruff_cb)

        self._bandit_cb = QCheckBox("Enable Bandit (Security scanning)")
        self._bandit_cb.setChecked(self.config.get("use_bandit", True))
        tools_layout.addWidget(self._bandit_cb)

        self._semgrep_cb = QCheckBox("Enable Semgrep (Pattern rules)")
        self._semgrep_cb.setChecked(self.config.get("use_semgrep", False))
        tools_layout.addWidget(self._semgrep_cb)

        layout.addWidget(tools_group)

        # ─── Appearance ──────────────────────────────────────────────────
        appearance_group = QGroupBox("Appearance")
        appearance_layout = QFormLayout(appearance_group)

        self._theme_combo = QComboBox()
        themes = get_available_themes()
        if themes:
            self._theme_combo.addItems(themes)
        else:
            self._theme_combo.addItems(["dark", "light"])
        current = self.config.theme
        idx = self._theme_combo.findText(current)
        if idx >= 0:
            self._theme_combo.setCurrentIndex(idx)
        appearance_layout.addRow("Theme:", self._theme_combo)

        layout.addWidget(appearance_group)

        # ─── File Handling ───────────────────────────────────────────────
        file_group = QGroupBox("File Handling")
        file_layout = QVBoxLayout(file_group)

        self._backup_cb = QCheckBox("Create .bak backups before applying fixes")
        self._backup_cb.setChecked(self.config.get("auto_backup", True))
        file_layout.addWidget(self._backup_cb)

        layout.addWidget(file_group)

        # ─── Save button ────────────────────────────────────────────────
        layout.addStretch()

        btn_row = QHBoxLayout()
        save_btn = QPushButton("Save Settings")
        save_btn.setObjectName("PrimaryButton")
        save_btn.setFixedHeight(44)
        save_btn.clicked.connect(self._save)
        btn_row.addStretch()
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _on_backend_changed(self, index: int):
        """Update URL field when a preset backend is selected."""
        url = self._backend_combo.currentData()
        if url:
            self._url_input.setText(url)

    def _save(self):
        """Save all settings to config."""
        self.config.set("base_url", self._url_input.text().strip())
        self.config.set("api_key", self._api_key_input.text().strip())
        self.config.set("model", self._model_input.text().strip())
        self.config.set("temperature", self._temp_spin.value())
        self.config.set("use_ruff", self._ruff_cb.isChecked())
        self.config.set("use_bandit", self._bandit_cb.isChecked())
        self.config.set("use_semgrep", self._semgrep_cb.isChecked())
        self.config.set("auto_backup", self._backup_cb.isChecked())

        new_theme = self._theme_combo.currentText()
        if new_theme != self.config.theme:
            self.config.set("theme", new_theme)
            self.theme_changed.emit(new_theme)

        logger.info("Settings saved")
