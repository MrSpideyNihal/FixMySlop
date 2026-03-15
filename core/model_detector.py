"""
Model detector — probes known local backend ports and lists available models.
Supports Ollama, llama.cpp server, vLLM, and any OpenAI-compatible endpoint.
"""
import requests
from typing import Optional
from macros import KNOWN_BACKENDS
from utils.logger import get_logger

logger = get_logger(__name__)


class ModelDetector:
    """
    Probes local inference backends and returns available models.
    Tries all known ports for fast detection.
    """

    def detect_running_backends(self) -> dict[str, list[str]]:
        """
        Returns dict of {backend_name: [model_names]} for all running backends.
        """
        results = {}
        for name, url in KNOWN_BACKENDS.items():
            models = self._probe_backend(url)
            if models is not None:
                results[name] = models
                logger.info(
                    "Found backend '%s' at %s with %d models",
                    name, url, len(models),
                )
        return results

    def _probe_backend(
        self,
        base_url: str,
        timeout: float = 2.0,
    ) -> Optional[list[str]]:
        """Try to list models at a backend. Returns model list or None if unreachable."""
        try:
            resp = requests.get(
                f"{base_url}/models",
                timeout=timeout,
            )
            if resp.status_code == 200:
                data = resp.json()
                return [m["id"] for m in data.get("data", [])]
        except Exception:
            pass
        return None

    def get_all_models(self, base_url: str) -> list[str]:
        """Get all models from a specific backend URL."""
        models = self._probe_backend(base_url)
        return models or []


def get_best_available_model(base_url: str = None) -> str:
    """Query backend and return best available model.
    Prefers coder models. Returns empty string if nothing found."""
    from macros import KNOWN_BACKENDS
    urls_to_try = [base_url] if base_url else list(KNOWN_BACKENDS.values())
    detector = ModelDetector()
    for url in urls_to_try:
        models = detector._probe_backend(url)
        if not models:
            continue
        coder = [m for m in models if "coder" in m.lower()]
        if coder:
            return coder[0]
        return models[0]
    return ""
