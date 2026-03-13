"""Tests for core/llm_client.py."""
import json
import pytest
from unittest.mock import MagicMock, patch
from core.llm_client import LLMClient


class TestLLMClient:
    """Tests for the LLMClient class."""

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
        mock_client.models.list.return_value = []

        client = LLMClient()
        assert client.is_available() is True

    @patch("core.llm_client.OpenAI")
    def test_is_available_failure(self, mock_openai_cls):
        """is_available should return False when backend is unreachable."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.models.list.side_effect = Exception("Connection refused")

        client = LLMClient()
        assert client.is_available() is False
