"""
Config — loads ~/.fixmyslop/config.yaml, provides typed access,
saves changes back. Always returns sane defaults if file is missing.
"""
import yaml
from pathlib import Path
from macros import (
    CONFIG_FILE, CONFIG_DIR, DEFAULT_MODEL, DEFAULT_BASE_URL,
    DEFAULT_API_KEY, DEFAULT_TEMPERATURE, DEFAULT_THEME, DEFAULT_FONT_SIZE,
    DEFAULT_LANGUAGE,
)
from utils.logger import get_logger

logger = get_logger(__name__)

DEFAULTS = {
    "model": DEFAULT_MODEL,
    "base_url": DEFAULT_BASE_URL,
    "api_key": DEFAULT_API_KEY,
    "temperature": DEFAULT_TEMPERATURE,
    "theme": DEFAULT_THEME,
    "font_size": DEFAULT_FONT_SIZE,
    "language": DEFAULT_LANGUAGE,
    "use_ruff": True,
    "use_bandit": True,
    "use_semgrep": False,
    "auto_backup": True,
    "recent_paths": [],
}


class Config:
    """Singleton-style config loader and writer."""

    def __init__(self):
        """Initialize config by loading from disk or using defaults."""
        self._data: dict = {}
        self.load()

    def load(self):
        """Load config from disk. Fall back to defaults if file missing."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                self._data = yaml.safe_load(f) or {}
        else:
            self._data = {}
        # Merge with defaults (missing keys get defaults)
        for key, val in DEFAULTS.items():
            self._data.setdefault(key, val)

    def save(self):
        """Persist current config to disk."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            yaml.dump(self._data, f, default_flow_style=False)
        logger.debug("Config saved to %s", CONFIG_FILE)

    def get(self, key: str, fallback=None):
        """Get a config value by key, with optional fallback."""
        return self._data.get(key, fallback if fallback is not None else DEFAULTS.get(key))

    def set(self, key: str, value):
        """Set a config value and persist to disk."""
        self._data[key] = value
        self.save()

    # ─── Typed accessors for common settings ─────────────────────────────
    @property
    def model(self) -> str:
        """Return the configured model tag."""
        return self.get("model")

    @property
    def base_url(self) -> str:
        """Return the configured backend API URL."""
        return self.get("base_url")

    @property
    def api_key(self) -> str:
        """Return the configured API key."""
        return self.get("api_key")

    @property
    def theme(self) -> str:
        """Return the configured UI theme name."""
        return self.get("theme")

    @property
    def temperature(self) -> float:
        """Return the configured LLM temperature."""
        return self.get("temperature")

    @property
    def font_size(self) -> int:
        """Return the configured UI base font size in px."""
        return int(self.get("font_size", DEFAULTS["font_size"]))
