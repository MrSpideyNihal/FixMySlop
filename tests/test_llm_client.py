"""Tests for core/llm_client.py."""
import json
import pytest
from unittest.mock import MagicMock, patch
from core.llm_client import LLMClient


class TestLLMClient:
    """Tests for the LLMClient class."""

    @staticmethod
    def _models_response(*model_ids: str):
        """Build a fake /models response object with .data[].id."""
        return MagicMock(data=[MagicMock(id=model_id) for model_id in model_ids])

    def test_parse_json_response_clean(self):
        """Should parse clean JSON."""
        client = LLMClient.__new__(LLMClient)
        result = client.parse_json_response('[{"a": 1}]')
        assert result == [{"a": 1}]

    def test_parse_json_response_with_fences(self):
        """Should strip markdown fences before parsing."""
        client = LLMClient.__new__(LLMClient)
        result = client.parse_json_response('```json\n[{"a": 1}]\n```')
        assert result == [{"a": 1}]

    def test_parse_json_response_invalid(self):
        """Should return empty list on invalid JSON (no crash)."""
        client = LLMClient.__new__(LLMClient)
        result = client.parse_json_response("not json at all")
        assert result == []

    def test_parse_json_response_empty(self):
        """Should return empty list on empty string."""
        client = LLMClient.__new__(LLMClient)
        result = client.parse_json_response("")
        assert result == []
        result = client.parse_json_response("   ")
        assert result == []

    @patch("core.llm_client.OpenAI")
    def test_is_available_success(self, mock_openai_cls):
        """is_available should return True when backend responds."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.models.list.return_value = self._models_response("qwen2.5-coder:3b")

        client = LLMClient()
        assert client.is_available() is True

    @patch("core.llm_client.OpenAI")
    def test_is_available_falls_back_to_available_model(self, mock_openai_cls):
        """is_available should switch to an installed model if configured one is missing."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.models.list.return_value = self._models_response("qwen2.5-coder:3b")

        client = LLMClient(model="qwen2.5-coder:7b")
        assert client.is_available() is True
        assert client.model == "qwen2.5-coder:3b"

    @patch("core.llm_client.OpenAI")
    def test_is_available_failure(self, mock_openai_cls):
        """is_available should return False when backend is unreachable."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.models.list.side_effect = Exception("Connection refused")

        client = LLMClient()
        assert client.is_available() is False

    @patch("core.llm_client.OpenAI")
    def test_chat_retries_with_fallback_model_on_not_found(self, mock_openai_cls):
        """chat should retry once with a fallback model when backend says model not found."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.models.list.return_value = self._models_response("qwen2.5-coder:3b")

        response = MagicMock()
        response.choices = [MagicMock(message=MagicMock(content="ok"))]
        mock_client.chat.completions.create.side_effect = [
            Exception("model 'qwen2.5-coder:7b' not found"),
            response,
        ]

        client = LLMClient(model="qwen2.5-coder:7b")
        result = client.chat("system", "user")

        assert result == "ok"
        assert client.model == "qwen2.5-coder:3b"
        assert mock_client.chat.completions.create.call_count == 2
