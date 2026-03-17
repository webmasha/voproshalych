"""Интеграционные тесты для QA API."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from fastapi.testclient import TestClient

from qa.main import app
from qa.llm.providers.base import LLMResponse


@pytest.fixture
def client():
    """Фикстура для тестового клиента."""
    return TestClient(app)


class TestHealthEndpoint:
    """Тесты для health endpoint."""

    def test_health_check(self, client):
        """Тест health check."""
        with patch("qa.api.routes.health.get_llm_pool") as mock_pool:
            mock_pool_instance = MagicMock()
            mock_pool_instance.get_available_providers.return_value = ["mistral"]
            mock_pool.return_value = mock_pool_instance

            response = client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert "version" in data

    def test_health_check_no_providers(self, client):
        """Тест health check без доступных провайдеров."""
        with patch("qa.api.routes.health.get_llm_pool") as mock_pool:
            mock_pool_instance = MagicMock()
            mock_pool_instance.get_available_providers.return_value = []
            mock_pool.return_value = mock_pool_instance

            response = client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "degraded"

    def test_readiness_check_ready(self, client):
        """Тест readiness check."""
        with patch("qa.api.routes.health.get_llm_pool") as mock_pool:
            mock_pool_instance = MagicMock()
            mock_pool_instance.get_available_providers.return_value = ["mistral"]
            mock_pool.return_value = mock_pool_instance

            response = client.get("/health/ready")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"

    def test_readiness_check_not_ready(self, client):
        """Тест readiness check без провайдеров."""
        with patch("qa.api.routes.health.get_llm_pool") as mock_pool:
            mock_pool_instance = MagicMock()
            mock_pool_instance.get_available_providers.return_value = []
            mock_pool.return_value = mock_pool_instance

            response = client.get("/health/ready")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "no_providers"


class TestQAEndpoint:
    """Тесты для QA endpoint."""

    def test_ask_question_success(self, client):
        """Тест успешного запроса."""
        mock_response = LLMResponse(
            content="Это тестовый ответ от LLM",
            model="open-mistral-nemo",
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        )

        with patch("qa.api.routes.qa.get_llm_pool") as mock_pool:
            mock_pool_instance = MagicMock()
            mock_pool_instance.select_model.return_value = "mistral"
            mock_pool_instance.call = AsyncMock(return_value=mock_response)
            mock_pool.return_value = mock_pool_instance

            response = client.post("/qa", json={"question": "Привет, как дела?"})

            assert response.status_code == 200
            data = response.json()
            assert "answer" in data
            assert data["model"] == "open-mistral-nemo"

    def test_ask_question_with_context(self, client):
        """Тест запроса с контекстом."""
        mock_response = LLMResponse(
            content="Ответ на основе контекста",
            model="open-mistral-nemo",
            usage={"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30},
        )

        with patch("qa.api.routes.qa.get_llm_pool") as mock_pool:
            mock_pool_instance = MagicMock()
            mock_pool_instance.select_model.return_value = "mistral"
            mock_pool_instance.call = AsyncMock(return_value=mock_response)
            mock_pool.return_value = mock_pool_instance

            response = client.post(
                "/qa",
                json={
                    "question": "Что ты знаешь об этом?",
                    "context": "Это про ТюмГУ",
                },
            )

            assert response.status_code == 200

            # Проверяем, что call был вызван с объединенным промптом
            mock_pool_instance.call.assert_called_once()
            call_kwargs = mock_pool_instance.call.call_args.kwargs
            assert "Контекст:" in call_kwargs["prompt"]
            assert "Вопрос:" in call_kwargs["prompt"]

    def test_ask_question_no_provider(self, client):
        """Тест запроса без доступных провайдеров."""
        with patch("qa.api.routes.qa.get_llm_pool") as mock_pool:
            mock_pool_instance = MagicMock()
            mock_pool_instance.select_model.return_value = None
            mock_pool.return_value = mock_pool_instance

            response = client.post("/qa", json={"question": "Привет"})

            assert response.status_code == 503
            assert "No available LLM providers" in response.json()["detail"]

    def test_ask_question_empty_question(self, client):
        """Тест запроса с пустым вопросом."""
        response = client.post("/qa", json={"question": ""})

        assert response.status_code == 422

    def test_ask_question_missing_question(self, client):
        """Тест запроса без вопроса."""
        response = client.post("/qa", json={})

        assert response.status_code == 422
