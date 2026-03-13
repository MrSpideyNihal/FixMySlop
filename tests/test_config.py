"""Tests for utils/config.py."""
import yaml
from utils.config import Config, DEFAULTS


class TestConfig:
    """Tests for the Config class."""

    def test_defaults_loaded(self, tmp_path, monkeypatch):
        """Config should load with sane defaults when no file exists."""
        monkeypatch.setattr("macros.CONFIG_DIR", tmp_path)
        monkeypatch.setattr("macros.CONFIG_FILE", tmp_path / "config.yaml")
        monkeypatch.setattr("utils.config.CONFIG_DIR", tmp_path)
        monkeypatch.setattr("utils.config.CONFIG_FILE", tmp_path / "config.yaml")

        config = Config()
        assert config.model == DEFAULTS["model"]
        assert config.base_url == DEFAULTS["base_url"]
        assert config.theme == DEFAULTS["theme"]

    def test_save_and_reload(self, tmp_path, monkeypatch):
        """Config should persist and reload correctly."""
        config_file = tmp_path / "config.yaml"
        monkeypatch.setattr("macros.CONFIG_DIR", tmp_path)
        monkeypatch.setattr("macros.CONFIG_FILE", config_file)
        monkeypatch.setattr("utils.config.CONFIG_DIR", tmp_path)
        monkeypatch.setattr("utils.config.CONFIG_FILE", config_file)

        config = Config()
        config.set("model", "custom-model:latest")
        assert config_file.exists()

        config2 = Config()
        assert config2.model == "custom-model:latest"

    def test_get_with_fallback(self, tmp_path, monkeypatch):
        """Config.get should return fallback for missing keys."""
        monkeypatch.setattr("macros.CONFIG_DIR", tmp_path)
        monkeypatch.setattr("macros.CONFIG_FILE", tmp_path / "config.yaml")
        monkeypatch.setattr("utils.config.CONFIG_DIR", tmp_path)
        monkeypatch.setattr("utils.config.CONFIG_FILE", tmp_path / "config.yaml")

        config = Config()
        assert config.get("nonexistent_key", "fallback") == "fallback"
