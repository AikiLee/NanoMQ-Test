"""
NanoMQ /subscriptions API tests.
"""

import allure

from tests.test_api.api_assertions import (
    assert_data_list_body,
    assert_success_body,
    assert_unauthorized,
)


@allure.epic("NanoMQ")
@allure.feature("HTTP API")
@allure.story("Subscriptions API")
@allure.severity(allure.severity_level.NORMAL)
@allure.tag("api", "subscriptions")
class TestSubscriptions:
    """
    get测试方案:
    1. test success
    2. test field
    3. test with params: negative
    4. test get subscriptions with nonexistent
    5. test auth
    """

    def test_subscriptions_success(self, nanomq_api_client):
        response = nanomq_api_client.get_subscriptions()

        assert response.status_code == 200

    def test_subscriptions_fields_match(self, nanomq_api_client):
        response = nanomq_api_client.get_subscriptions()
        body = assert_data_list_body(response)

        for subscription in body["data"]:
            assert {"clientid", "topic", "qos"} <= subscription.keys()
            assert isinstance(subscription["clientid"], str)
            assert isinstance(subscription["topic"], str)
            assert subscription["topic"]
            assert subscription["qos"] in {0, 1, 2}

    def test_subscriptions_with_invalid_params_are_ignored(self, nanomq_api_client):
        response = nanomq_api_client.get(
            "/subscriptions",
            params={
                "clientid": "not-exist",
                "topic": "not/exist",
                "unexpected": "value",
            },
        )
        body = assert_data_list_body(response)

        assert "data" in body

    def test_get_subscriptions_with_nonexistent_clientid(self, nanomq_api_client):
        response = nanomq_api_client.get("/subscriptions/not-exist")
        body = assert_success_body(response)

        assert body["data"] == []

    def test_get_subscriptions_without_auth(self, nanomq_api_client_without_auth):
        response = nanomq_api_client_without_auth.get_subscriptions()

        assert_unauthorized(response)
