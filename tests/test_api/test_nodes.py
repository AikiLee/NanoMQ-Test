"""
新建 practice/tests/test_nanomq_api.py。
覆盖：
● GET /nodes
● GET /metrics
"""

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


def _first_node(response):
    body = response.json()
    assert body["code"] == 0
    assert isinstance(body["data"], list)
    assert body["data"]
    return body["data"][0]


class TestNodes:
    """
    get测试方案:
    1. test success
    2. test field
    3. test with params: negative
    4. test get nodes with nonexistent
    5. test auth
    """

    def test_nodes_success(self, nanomq_api_client):
        response = nanomq_api_client.get_nodes()

        assert response.status_code == 200

    def test_nodes_fields_match(self, nanomq_api_client):
        response = nanomq_api_client.get_nodes()
        node = _first_node(response)

        assert response.status_code == 200
        assert {"connections", "node_status", "uptime", "version"} <= node.keys()
        assert isinstance(node["connections"], int)
        assert node["connections"] >= 0
        assert node["node_status"] == "Running"
        assert isinstance(node["uptime"], str)
        assert isinstance(node["version"], str)
        assert node["version"]

    def test_nodes_with_invalid_params_are_ignored(self, nanomq_api_client):
        response = nanomq_api_client.get(
            "/nodes",
            params={"node": "not-exist", "unexpected": "value"},
        )
        node = _first_node(response)

        assert response.status_code == 200
        assert node["node_status"] == "Running"

    def test_get_nodes_with_nonexistent_path(self, nanomq_api_client):
        response = nanomq_api_client.get("/nodes/not-exist")
        body = response.json()

        assert response.status_code == 404
        assert body["code"] == 102

    def test_get_nodes_without_auth(self, nanomq_api_client_without_auth):
        response = nanomq_api_client_without_auth.get_nodes()
        body = response.json()

        assert response.status_code == 401
        assert body["code"] == 104
