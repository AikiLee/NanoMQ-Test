"""
NanoMQ /metrics API tests.
"""

import allure
import pytest

from api_clients.nanomqtt_api_client import NanoMqttApiClient
from config.settings import settings


@pytest.fixture
def nanomq_api_client():
    client = NanoMqttApiClient(
        settings.nanomq_api_url,
        settings.request_timeout,
        auth=(settings.nanomq_username, settings.nanomq_password),
    )
    yield client
    client.close()


@pytest.fixture
def nanomq_api_client_without_auth():
    client = NanoMqttApiClient(settings.nanomq_api_url, settings.request_timeout)
    yield client
    client.close()


def _metrics_body(response):
    body = response.json()
    assert isinstance(body, dict)
    return body


@allure.epic("NanoMQ")
@allure.feature("HTTP API")
@allure.story("Metrics API")
@allure.severity(allure.severity_level.NORMAL)
@allure.tag("api", "metrics")
class TestMetrics:
    """
    get测试方案:
    1. test success
    2. test field
    3. test with params: negative
    4. test get metrics with nonexistent
    5. test auth
    """

    def test_metrics_success(self, nanomq_api_client):
        response = nanomq_api_client.get_metrics()

        assert response.status_code == 200

    def test_metrics_fields_match(self, nanomq_api_client):
        response = nanomq_api_client.get_metrics()
        body = _metrics_body(response)

        assert response.status_code == 200
        assert {"metrics", "cpuinfo", "memory", "connections"} <= body.keys()
        assert isinstance(body["metrics"], list)
        assert isinstance(body["cpuinfo"], str)
        assert body["cpuinfo"].endswith("%")
        assert isinstance(body["memory"], str)
        assert body["memory"].isdigit()
        assert isinstance(body["connections"], int)
        assert body["connections"] >= 0

    def test_metrics_with_invalid_params_are_ignored(self, nanomq_api_client):
        response = nanomq_api_client.get(
            "/metrics",
            params={"metric": "not-exist", "unexpected": "value"},
        )
        body = _metrics_body(response)

        assert response.status_code == 200
        assert {"metrics", "cpuinfo", "memory", "connections"} <= body.keys()

    def test_get_metrics_with_nonexistent_path(self, nanomq_api_client):
        response = nanomq_api_client.get("/metrics/not-exist")
        body = response.json()

        assert response.status_code == 404
        assert body["code"] == 102

    def test_get_metrics_without_auth(self, nanomq_api_client_without_auth):
        response = nanomq_api_client_without_auth.get_metrics()
        body = response.json()

        assert response.status_code == 401
        assert body["code"] == 104
