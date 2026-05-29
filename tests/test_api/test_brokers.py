"""
NanoMQ /brokers API tests.
"""

import allure

from tests.test_api.api_assertions import (
    assert_data_list_body,
    assert_not_found,
    assert_unauthorized,
)


@allure.epic("NanoMQ")
@allure.feature("HTTP API")
@allure.story("Brokers API")
@allure.severity(allure.severity_level.NORMAL)
@allure.tag("api", "brokers")
class TestBrokers:
    """
    get测试方案:
    1. test success
    2. test field
    3. test with params: negative
    4. test get brokers with nonexistent
    5. test auth
    """

    def test_brokers_success(self, nanomq_api_client):
        response = nanomq_api_client.get_brokers()

        assert response.status_code == 200

    def test_brokers_fields_match(self, nanomq_api_client):
        response = nanomq_api_client.get_brokers()
        body = assert_data_list_body(response)

        assert body["data"]
        broker = body["data"][0]
        assert {"datetime", "node_status", "sysdescr", "uptime", "version"} <= broker.keys()
        assert broker["node_status"] == "Running"
        assert broker["sysdescr"] == "NanoMQ Broker"
        assert isinstance(broker["datetime"], str)
        assert isinstance(broker["uptime"], str)
        assert isinstance(broker["version"], str)
        assert broker["version"]

    def test_brokers_with_invalid_params_are_ignored(self, nanomq_api_client):
        response = nanomq_api_client.get(
            "/brokers",
            params={"broker": "not-exist", "unexpected": "value"},
        )
        body = assert_data_list_body(response)

        assert body["data"]

    def test_get_brokers_with_nonexistent_path(self, nanomq_api_client):
        response = nanomq_api_client.get("/brokers/not-exist")

        assert_not_found(response)

    def test_get_brokers_without_auth(self, nanomq_api_client_without_auth):
        response = nanomq_api_client_without_auth.get_brokers()

        assert_unauthorized(response)
