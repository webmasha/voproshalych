"""Интеграционные тесты для QA API.

Тестируют основные endpoints QA сервиса:
- Health check endpoint
- QA endpoint с мокированными LLM провайдерами
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from fastapi.testclient import TestClient

from qa.main import app
from qa.llm.providers.base import LLMResponse


@pytest.fixture
def client():
    """Фикстура для тестового клиента.

    Созда TestClient для FastAPI приложения.

    Returns:
        TestClient для выполнения HTTP запросов
    """
    return TestClient(app)


class TestHealthEndpoint:
    """Тесты для health check endpoint.

    Проверяет доступность сервиса и корректность ответов.
    """

    def test_health_check(self, client):
        """Тест health check.

        Проверяет что сервис возвращает статус 200
        и корректную структуру ответа.

        Args:
            client: TestClient для выполнения запросов
        """
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
        """Тест health check без доступных провайдеров.

        Проверяет что корректно обрабатывается ситуация
        когда нет доступных LLM провайдеров.

        Args:
            client: TestClient для выполнения запросов
        """
        with patch("qa.api.routes.health.get_llm_pool") as mock_pool:
            mock_pool_instance = MagicMock()
            mock_pool_instance.get_available_providers.return_value = []
            mock_pool.return_value = mock_pool_instance

            response = client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "degraded"

     def test_readiness_check_ready(self, client):
        """Тест readiness check.

        Проверяет readiness endpoint возвращает корректный статус
        когда есть доступные LLM провайдеры.

        Args:
            client: TestClient для выполнения запросов
        """
        with patch("qa.api.routes.health.get_llm_pool") as mock_pool:
            mock_pool_instance = MagicMock()
            mock_pool_instance.get_available_providers.return_value = ["mistral"]
            mock_pool.return_value = mock_pool_instance

            response = client.get("/health/ready")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"

    def test_readiness_check_not_ready(self, client):
        """Тест readiness check без провайдеров.

        Проверяет readiness endpoint корректно обрабатывает
        ситуацию когда нет доступных LLM провайдеров.

        Args:
            client: TestClient для выполнения запросов
        """
        with patch("qa.api.routes.health.get_llm_pool") as mock_pool:
            mock_pool_instance = MagicMock()
            mock_pool_instance.get_available_providers.return_value = []
            mock_pool.return_value = mock_pool_instance

            response = client.get("/health/ready")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "no_providers"


class TestQAEndpoint:
    """Тесты для QA endpoint.

    Тестируют обработку вопросов пользователей и ответы от LLM
    с мокированными провайдерами.
    """

    def test_ask_question_success(self, client):
        """Тест успешного запроса.

        Проверяет корректность ответа на вопрос
        и что LLM вызывается с правильными параметрами.

        Args:
            client: TestClient для выполнения запросов
        """
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
        """Тест запроса с контекстом.

        Проверяет что контекст корректно передаётся в промпт LLM
        и объединяется с вопросом.

        Args:
            client: TestClient для выполнения запросов
        """
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
            assert "Context:" in call_kwargs["prompt"]
            assert "Вопрос:" in call_kwargs["prompt"]

    def test_ask_question_no_provider(self, client):
        """Тест запроса без доступных провайдеров.

        Проверяет что корректно возвращается ошибка 503
        когда нет доступных LLM провайдеров.

        Args:
            client: TestClient для выполнения запросов
        """
        with patch("qa.api.routes.qa.get_llm_pool") as mock_pool:
            mock_pool_instance = MagicMock()
            mock_pool_instance.select_model.return_value = None
            mock_pool.return_value = mock_pool_instance

            response = client.post("/qa", json={"question": "Привет"})

            assert response.status_code == 503
            assert "No available LLM providers" in response.json()["detail"]

    def test_ask_question_empty_question(self, client):
        """Тест запроса с пустым вопросом.

        Проверяет валидацию запроса на пустой вопрос.

        Args:
            client: TestClient для выполнения запросов
        """
        response = client.post("/qa", json={})

        assert response.status_code == 422

    def test_ask_question_missing_question(self, client):
        """Тест запроса без вопроса.

        Проверяет что endpoint возвращает ошибку при отсутствии
        обязательного поля question.

        Args:
            client: TestClient для выполнения запросов
        """
        response = client.post("/qa", json={})

        assert response.status_code == 422

    def test_ask_question_missing_question(self, client):
        """Тест запроса без вопроса."""
        response = client.post("/qa", json={})

        assert response.status_code == 422
