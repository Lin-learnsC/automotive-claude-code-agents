#!/usr/bin/env python3
"""
Unit tests for KimiAdapter in LLM Council.

These tests mock the OpenAI client to verify KimiAdapter behavior
without requiring network access or API keys.
"""

import asyncio
import logging
import os
from unittest.mock import MagicMock, patch

import pytest

from tools.llm_council import KimiAdapter, ModelConfig, ResponseCache


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def kimi_config() -> ModelConfig:
    """Standard Kimi test configuration."""
    return ModelConfig(
        name="kimi-latest",
        provider="kimi",
        api_key_env="KIMI_API_KEY",
        endpoint="https://api.moonshot.cn/v1",
        max_tokens=1024,
        temperature=0.3,
    )


@pytest.fixture
def mock_cache() -> ResponseCache:
    """Fresh response cache for each test."""
    return ResponseCache(max_size=10, default_ttl=300)


@pytest.fixture
def sample_messages():
    """Sample chat messages."""
    return [
        {"role": "user", "content": "What is the best RTOS for BMS?"}
    ]


@pytest.fixture
def sample_system_prompt() -> str:
    """Sample system prompt."""
    return "You are an automotive software architect."


# -----------------------------------------------------------------------------
# Helper: build a realistic OpenAI-like response object
# -----------------------------------------------------------------------------

def _make_response(text: str, total_tokens: int = 42):
    """Construct a mock response that mimics openai.ChatCompletion."""
    response = MagicMock()
    choice = MagicMock()
    choice.message.content = text
    response.choices = [choice]

    usage = MagicMock()
    usage.total_tokens = total_tokens
    response.usage = usage

    return response


# -----------------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------------

class TestKimiAdapterSuccess:
    """Happy-path tests for KimiAdapter.get_completion."""

    @pytest.mark.asyncio
    async def test_get_completion_returns_text_and_duration(
        self, kimi_config, mock_cache, sample_messages, sample_system_prompt
    ):
        """Verify that a successful API call returns (text, duration_ms)."""
        adapter = KimiAdapter(kimi_config, cache=mock_cache)
        expected_text = "FreeRTOS is a solid choice for BMS due to its deterministic scheduling."

        with patch.dict(os.environ, {"KIMI_API_KEY": "sk-dummy"}):
            with patch("openai.OpenAI") as MockOpenAI:
                mock_client = MagicMock()
                mock_client.chat.completions.create.return_value = _make_response(
                    expected_text, total_tokens=100
                )
                MockOpenAI.return_value = mock_client

                text, duration_ms = await adapter.get_completion(
                    sample_messages, sample_system_prompt
                )

        assert text == expected_text
        assert duration_ms > 0.0
        assert adapter._request_count == 1
        assert adapter._total_tokens == 100

    @pytest.mark.asyncio
    async def test_get_completion_full_messages_format(
        self, kimi_config, mock_cache, sample_messages, sample_system_prompt
    ):
        """Verify that the system prompt is prepended to messages."""
        adapter = KimiAdapter(kimi_config, cache=mock_cache)

        with patch.dict(os.environ, {"KIMI_API_KEY": "sk-dummy"}):
            with patch("openai.OpenAI") as MockOpenAI:
                mock_client = MagicMock()
                mock_client.chat.completions.create.return_value = _make_response("OK")
                MockOpenAI.return_value = mock_client

                await adapter.get_completion(sample_messages, sample_system_prompt)

                call_args = mock_client.chat.completions.create.call_args
                sent_messages = call_args.kwargs["messages"]

                assert sent_messages[0]["role"] == "system"
                assert sent_messages[0]["content"] == sample_system_prompt
                assert sent_messages[1]["role"] == "user"


class TestKimiAdapterCache:
    """ResponseCache interaction tests."""

    @pytest.mark.asyncio
    async def test_cache_hit_returns_zero_duration(
        self, kimi_config, mock_cache, sample_messages, sample_system_prompt
    ):
        """A cache hit must return duration_ms == 0.0 and skip the API call."""
        adapter = KimiAdapter(kimi_config, cache=mock_cache)
        expected_text = "Cached response"

        # Prime the cache
        cache_key = adapter._build_cache_key(sample_messages, sample_system_prompt)
        mock_cache.set(cache_key, kimi_config.get_cache_key(), expected_text)

        with patch("openai.OpenAI") as MockOpenAI:
            text, duration_ms = await adapter.get_completion(
                sample_messages, sample_system_prompt
            )
            MockOpenAI.assert_not_called()  # API must NOT be invoked

        assert text == expected_text
        assert duration_ms == 0.0
        assert adapter._request_count == 0  # No actual request made

    @pytest.mark.asyncio
    async def test_cache_miss_then_hit(
        self, kimi_config, mock_cache, sample_messages, sample_system_prompt
    ):
        """First call misses cache (API invoked), second call hits cache."""
        adapter = KimiAdapter(kimi_config, cache=mock_cache)
        expected_text = "Deterministic answer"

        with patch.dict(os.environ, {"KIMI_API_KEY": "sk-dummy"}):
            with patch("openai.OpenAI") as MockOpenAI:
                mock_client = MagicMock()
                mock_client.chat.completions.create.return_value = _make_response(
                    expected_text, total_tokens=50
                )
                MockOpenAI.return_value = mock_client

                # First call → cache miss → API call
                text1, dur1 = await adapter.get_completion(
                    sample_messages, sample_system_prompt
                )
                assert text1 == expected_text
                assert dur1 > 0.0
                assert adapter._request_count == 1
                assert mock_client.chat.completions.create.call_count == 1

                # Second call → cache hit → NO API call
                text2, dur2 = await adapter.get_completion(
                    sample_messages, sample_system_prompt
                )
                assert text2 == expected_text
                assert dur2 == 0.0
                assert adapter._request_count == 1  # Still 1
                assert mock_client.chat.completions.create.call_count == 1  # Still 1

    @pytest.mark.asyncio
    async def test_cache_does_not_interfere_without_cache_instance(
        self, kimi_config, sample_messages, sample_system_prompt
    ):
        """Adapter created without cache must always call the API."""
        adapter = KimiAdapter(kimi_config, cache=None)

        with patch.dict(os.environ, {"KIMI_API_KEY": "sk-dummy"}):
            with patch("openai.OpenAI") as MockOpenAI:
                mock_client = MagicMock()
                mock_client.chat.completions.create.return_value = _make_response("A")
                MockOpenAI.return_value = mock_client

                await adapter.get_completion(sample_messages, sample_system_prompt)
                await adapter.get_completion(sample_messages, sample_system_prompt)

                assert mock_client.chat.completions.create.call_count == 2


class TestKimiAdapterErrorHandling:
    """Failure-mode tests."""

    @pytest.mark.asyncio
    async def test_api_error_is_logged_and_re_raised(
        self, kimi_config, mock_cache, sample_messages, sample_system_prompt, caplog
    ):
        """Exceptions from the OpenAI client must be logged and re-raised."""
        adapter = KimiAdapter(kimi_config, cache=mock_cache)
        caplog.set_level(logging.ERROR, logger="llm_council.kimi")

        with patch.dict(os.environ, {"KIMI_API_KEY": "sk-dummy"}):
            with patch("openai.OpenAI") as MockOpenAI:
                mock_client = MagicMock()
                mock_client.chat.completions.create.side_effect = RuntimeError(
                    "Connection reset"
                )
                MockOpenAI.return_value = mock_client

                with pytest.raises(RuntimeError, match="Connection reset"):
                    await adapter.get_completion(sample_messages, sample_system_prompt)

        assert "kimi API error: Connection reset" in caplog.text
        assert adapter._request_count == 1  # Request was attempted

    @pytest.mark.asyncio
    async def test_openai_init_error_is_propagated(
        self, kimi_config, sample_messages, sample_system_prompt
    ):
        """If OpenAI client initialization fails, error is raised."""
        adapter = KimiAdapter(kimi_config, cache=None)

        with patch.dict(os.environ, {"KIMI_API_KEY": "sk-dummy"}):
            with patch("openai.OpenAI", side_effect=ValueError("bad key")):
                with pytest.raises(ValueError, match="bad key"):
                    await adapter.get_completion(sample_messages, sample_system_prompt)


class TestKimiAdapterTokenTracking:
    """Token usage and statistics tests."""

    @pytest.mark.asyncio
    async def test_token_count_accumulates_across_calls(
        self, kimi_config, mock_cache, sample_messages, sample_system_prompt
    ):
        """Multiple API calls must accumulate total_tokens."""
        adapter = KimiAdapter(kimi_config, cache=mock_cache)

        with patch.dict(os.environ, {"KIMI_API_KEY": "sk-dummy"}):
            with patch("openai.OpenAI") as MockOpenAI:
                mock_client = MagicMock()
                # Return different token counts on successive calls
                responses = [
                    _make_response("A", total_tokens=10),
                    _make_response("B", total_tokens=20),
                ]
                mock_client.chat.completions.create.side_effect = responses
                MockOpenAI.return_value = mock_client

                await adapter.get_completion(sample_messages, sample_system_prompt)
                await adapter.get_completion(
                    [{"role": "user", "content": "Another question"}],
                    sample_system_prompt,
                )

        assert adapter._total_tokens == 30
        assert adapter._request_count == 2

    @pytest.mark.asyncio
    async def test_stats_returns_correct_dict(
        self, kimi_config, mock_cache, sample_messages, sample_system_prompt
    ):
        """get_stats() must reflect provider, model, request_count, total_tokens."""
        adapter = KimiAdapter(kimi_config, cache=mock_cache)

        with patch.dict(os.environ, {"KIMI_API_KEY": "sk-dummy"}):
            with patch("openai.OpenAI") as MockOpenAI:
                mock_client = MagicMock()
                mock_client.chat.completions.create.return_value = _make_response(
                    "OK", total_tokens=99
                )
                MockOpenAI.return_value = mock_client

                await adapter.get_completion(sample_messages, sample_system_prompt)

        stats = adapter.get_stats()
        assert stats["provider"] == "kimi"
        assert stats["model"] == "kimi-latest"
        assert stats["request_count"] == 1
        assert stats["total_tokens"] == 99

    @pytest.mark.asyncio
    async def test_no_usage_attribute_skips_token_count(
        self, kimi_config, mock_cache, sample_messages, sample_system_prompt
    ):
        """If response lacks 'usage', total_tokens must remain unchanged."""
        adapter = KimiAdapter(kimi_config, cache=mock_cache)

        with patch.dict(os.environ, {"KIMI_API_KEY": "sk-dummy"}):
            with patch("openai.OpenAI") as MockOpenAI:
                mock_client = MagicMock()
                response = _make_response("No usage")
                response.usage = None  # Simulate missing usage
                mock_client.chat.completions.create.return_value = response
                MockOpenAI.return_value = mock_client

                await adapter.get_completion(sample_messages, sample_system_prompt)

        assert adapter._total_tokens == 0


class TestKimiAdapterConfiguration:
    """Config and client initialization tests."""

    @pytest.mark.asyncio
    async def test_client_uses_configured_endpoint(
        self, kimi_config, sample_messages, sample_system_prompt
    ):
        """OpenAI client must be initialized with the endpoint from config."""
        adapter = KimiAdapter(kimi_config, cache=None)

        with patch("openai.OpenAI") as MockOpenAI:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = _make_response("OK")
            MockOpenAI.return_value = mock_client

            with patch.dict(os.environ, {"KIMI_API_KEY": "sk-dummy"}):
                await adapter.get_completion(sample_messages, sample_system_prompt)

            MockOpenAI.assert_called_once_with(
                api_key="sk-dummy",
                base_url="https://api.moonshot.cn/v1",
            )

    @pytest.mark.asyncio
    async def test_missing_api_key_raises_value_error(
        self, sample_messages, sample_system_prompt
    ):
        """If env var is missing, _get_api_key raises ValueError."""
        config = ModelConfig(
            name="kimi-latest",
            provider="kimi",
            api_key_env="MISSING_KEY_VAR",
        )
        adapter = KimiAdapter(config, cache=None)

        with patch("openai.OpenAI"):
            with pytest.raises(ValueError, match="MISSING_KEY_VAR"):
                await adapter.get_completion(sample_messages, sample_system_prompt)
