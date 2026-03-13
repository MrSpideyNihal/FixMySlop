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

    def chat(
        self,
        system: str,
        user: str,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> str:
        """Send a chat completion request and return the response text."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
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
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
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
        """Check if the backend is reachable."""
        try:
            self.client.models.list()
            return True
        except Exception:
            return False
