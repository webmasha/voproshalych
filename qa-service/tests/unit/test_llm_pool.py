"""Unit тесты для LLM Pool."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from qa.llm.pool import LLMPool
from qa.llm.config import LLMConfig
from qa.llm.providers.base import LLMResponse


class TestLLMPool:
    """Тесты для LLMPool."""

    def test_init_with_config(self):
        """Тест инициализации с конфигом."""
        config = LLMConfig(
            mistral_api_key="test-key",
            model_priority=["mistral", "openrouter"],
        )
        pool = LLMPool(config)

        assert pool._config == config
        assert "mistral" in pool._providers

    def test_init_default_providers(self):
        """Тест инициализации с дефолтными провайдерами."""
        pool = LLMPool()

        assert "mistral" in pool._providers
        assert "openrouter" in pool._providers
        assert "gigachat" in pool._providers

    def test_get_available_providers_all_available(self):
        """Тест получения доступных провайдеров (все доступны)."""
        pool = LLMPool()

        with patch.object(
            pool._providers["mistral"], "is_available", return_value=True
        ):
            with patch.object(
                pool._providers["openrouter"], "is_available", return_value=True
            ):
                with patch.object(
                    pool._providers["gigachat"], "is_available", return_value=True
                ):
                    available = pool.get_available_providers()

                    assert "mistral" in available
                    assert "openrouter" in available
                    assert "gigachat" in available

    def test_get_available_providers_none_available(self):
        """Тест получения доступных провайдеров (нет доступных)."""
        pool = LLMPool()

        with patch.object(
            pool._providers["mistral"], "is_available", return_value=False
        ):
            with patch.object(
                pool._providers["openrouter"], "is_available", return_value=False
            ):
                with patch.object(
                    pool._providers["gigachat"], "is_available", return_value=False
                ):
                    available = pool.get_available_providers()

                    assert len(available) == 0

    def test_select_model_first_available(self):
        """Тест выбора первой доступной модели."""
        config = LLMConfig(
            mistral_api_key="test-key",
            model_priority=["mistral", "openrouter", "gigachat"],
        )
        pool = LLMPool(config)

        with patch.object(
            pool._providers["mistral"], "is_available", return_value=True
        ):
            selected = pool.select_model()

            assert selected == "mistral"

    def test_select_model_fallback_to_second(self):
        """Тест fallback на вторую модель."""
        config = LLMConfig(
            mistral_api_key="",  # Недоступен
            openrouter_api_key="test-key",  # Доступен
            gigachat_client_id="",  # Недоступен
            model_priority=["mistral", "openrouter", "gigachat"],
        )
        pool = LLMPool(config)

        with patch.object(
            pool._providers["mistral"], "is_available", return_value=False
        ):
            with patch.object(
                pool._providers["gigachat"], "is_available", return_value=False
            ):
                selected = pool.select_model()

                assert selected == "openrouter"

    def test_select_model_no_available(self):
        """Тест выбора модели, когда нет доступных."""
        config = LLMConfig(
            mistral_api_key="",
            openrouter_api_key="",
            gigachat_client_id="",
            model_priority=["mistral", "openrouter", "gigachat"],
        )
        pool = LLMPool(config)

        selected = pool.select_model()

        assert selected is None

    @pytest.mark.asyncio
    async def test_call_success(self):
        """Тест успешного вызова LLM."""
        config = LLMConfig(mistral_api_key="test-key")
        pool = LLMPool(config)

        mock_response = LLMResponse(
            content="Hello, world!",
            model="test-model",
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        )

        with patch.object(
            pool._providers["mistral"], "is_available", return_value=True
        ):
            with patch.object(
                pool._providers["mistral"], "generate", return_value=mock_response
            ):
                response = await pool.call(prompt="Hello", provider_name="mistral")

                assert response.content == "Hello, world!"
                assert response.model == "test-model"

    @pytest.mark.asyncio
    async def test_call_fallback_on_error(self):
        """Тест fallback при ошибке первого провайдера."""
        config = LLMConfig(
            mistral_api_key="test-key",
            openrouter_api_key="test-key",
        )
        pool = LLMPool(config)

        mock_response = LLMResponse(
            content="Hello from fallback!",
            model="openrouter-model",
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        )

        with patch.object(
            pool._providers["mistral"], "is_available", return_value=True
        ):
            with patch.object(
                pool._providers["openrouter"], "is_available", return_value=True
            ):
                with patch.object(
                    pool._providers["mistral"],
                    "generate",
                    side_effect=Exception("API Error"),
                ):
                    with patch.object(
                        pool._providers["openrouter"],
                        "generate",
                        return_value=mock_response,
                    ):
                        response = await pool.call(prompt="Hello")

                        assert response.content == "Hello from fallback!"
                        assert response.model == "openrouter-model"

    @pytest.mark.asyncio
    async def test_call_all_providers_failed(self):
        """Тест ошибки, когда все провайдеры упали."""
        config = LLMConfig(
            mistral_api_key="test-key",
            openrouter_api_key="test-key",
        )
        pool = LLMPool(config)

        with patch.object(
            pool._providers["mistral"], "is_available", return_value=True
        ):
            with patch.object(
                pool._providers["openrouter"], "is_available", return_value=True
            ):
                with patch.object(
                    pool._providers["mistral"],
                    "generate",
                    side_effect=Exception("API Error"),
                ):
                    with patch.object(
                        pool._providers["openrouter"],
                        "generate",
                        side_effect=Exception("API Error"),
                    ):
                        with pytest.raises(ValueError, match="All providers failed"):
                            await pool.call(prompt="Hello")
