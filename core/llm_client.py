"""
LLM client — wraps openai-compatible API.
Works with Ollama, llama.cpp server, vLLM, or any OpenAI-compatible backend.
"""
import json
from typing import Generator
from openai import OpenAI
from utils.logger import get_logger
from macros import (
    DEFAULT_MODEL, DEFAULT_BASE_URL, DEFAULT_API_KEY,
    DEFAULT_TEMPERATURE, DEFAULT_MAX_TOKENS,
)

logger = get_logger(__name__)


class LLMClient:
    """
    Thin wrapper around the OpenAI-compatible chat completions API.
    Designed to work with any local backend: Ollama, llama.cpp, vLLM.
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        api_key: str = DEFAULT_API_KEY,
        model: str = DEFAULT_MODEL,
    ):
        """Initialize the LLM client with connection parameters."""
        self.base_url = base_url
        self.model = model
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        logger.info("LLMClient initialized: model=%s base_url=%s", model, base_url)

    def _create_completion(
        self,
        system: str,
        user: str,
        temperature: float,
        max_tokens: int,
        stream: bool = False,
    ):
        """Create a completion request with the currently active model."""
        return self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
        )

    def _list_model_ids(self) -> list[str]:
        """Return model ids from /models response for both real and mocked clients."""
        models_obj = self.client.models.list()
        data = getattr(models_obj, "data", models_obj)
        model_ids: list[str] = []

        for item in data or []:
            model_id = getattr(item, "id", None)
            if model_id is None and isinstance(item, dict):
                model_id = item.get("id")
            if model_id:
                model_ids.append(str(model_id))

        return model_ids

    def _pick_fallback_model(self, model_ids: list[str]) -> str:
        """Pick a sensible fallback model from available backend models."""
        if not model_ids:
            return ""

        current_family = self.model.split(":", 1)[0]
        same_family = [m for m in model_ids if m.split(":", 1)[0] == current_family]
        if same_family:
            return same_family[0]

        coder_models = [m for m in model_ids if "coder" in m.lower()]
        if coder_models:
            return coder_models[0]

        return model_ids[0]

    def _resolve_model_fallback(self) -> bool:
        """Switch to an available model if configured model is missing."""
        model_ids = self._list_model_ids()
        if not model_ids or self.model in model_ids:
            return False

        old_model = self.model
        fallback_model = self._pick_fallback_model(model_ids)
        if not fallback_model:
            return False

        self.model = fallback_model
        logger.warning(
            "Configured model '%s' not found. Falling back to '%s'.",
            old_model,
            fallback_model,
        )
        return True

    @staticmethod
    def _is_model_not_found_error(error: Exception) -> bool:
        """Detect model-not-found errors from OpenAI-compatible backends."""
        message = str(error).lower()
        return "model" in message and "not found" in message

    def chat(
        self,
        system: str,
        user: str,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> str:
        """Send a chat completion request and return the response text."""
        try:
            response = self._create_completion(system, user, temperature, max_tokens)
            return response.choices[0].message.content.strip()
        except Exception as e:
            if self._is_model_not_found_error(e) and self._resolve_model_fallback():
                logger.info("Retrying LLM request with fallback model '%s'", self.model)
                response = self._create_completion(system, user, temperature, max_tokens)
                return response.choices[0].message.content.strip()

            logger.error("LLM request failed: %s", e)
            raise

    def chat_stream(
        self,
        system: str,
        user: str,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> Generator[str, None, None]:
        """Stream a chat completion — yields tokens as they arrive."""
        try:
            stream = self._create_completion(
                system,
                user,
                temperature,
                max_tokens,
                stream=True,
            )
        except Exception as e:
            if self._is_model_not_found_error(e) and self._resolve_model_fallback():
                logger.info("Retrying streamed request with fallback model '%s'", self.model)
                stream = self._create_completion(
                    system,
                    user,
                    temperature,
                    max_tokens,
                    stream=True,
                )
            else:
                raise

        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    def parse_json_response(self, raw: str) -> any:
        """Parse JSON from LLM response.

        Tries direct parse first (preserves already-clean JSON),
        then falls back to extraction. Never raises.
        """
        if not raw or not raw.strip():
            logger.warning("LLM returned empty response — skipping")
            return []

        text = raw.strip()

        # Fast path: already valid JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Fallback: extract JSON array from within the text
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass

        logger.warning(
            "LLM returned malformed JSON (len=%d) — skipping. "
            "Tip: Use a code-tuned model like qwen2.5-coder:7b for better results.",
            len(raw),
        )
        return []

    def is_available(self) -> bool:
        """Check backend is reachable AND switch to
        a real model if configured one doesn't exist."""
        try:
            model_ids = self._list_model_ids()
            if not model_ids:
                return False
            if not self.model or self.model not in model_ids:
                fallback = self._pick_fallback_model(model_ids)
                if fallback:
                    logger.warning(
                        "Model '%s' not found — switching to '%s'",
                        self.model, fallback
                    )
                    self.model = fallback
            return True
        except Exception:
            return False
