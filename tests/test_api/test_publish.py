"""
NanoMQ /mqtt/publish API tests.
"""

from tests.test_api.api_assertions import (
    assert_not_found,
    assert_success_body,
    assert_unauthorized,
)
from utils.naming import unique_topic


class TestPublish:
    """
    post测试方案:
    1. test success
    2. test response field
    3. test with body: negative
    4. test publish with nonexistent path
    5. test auth
    """

    def test_publish_success(self, nanomq_api_client):
        response = nanomq_api_client.publish_message(
            topic=unique_topic("study/api/publish"),
            payload="hello from api test",
        )

        assert response.status_code == 200

    def test_publish_response_fields_match(self, nanomq_api_client):
        response = nanomq_api_client.publish_message(
            topic=unique_topic("study/api/publish"),
            payload="hello from api test",
        )
        body = assert_success_body(response)

        assert body == {"code": 0}

    def test_publish_missing_topic_returns_business_error(self, nanomq_api_client):
        response = nanomq_api_client.post(
            "/mqtt/publish",
            json={"payload": "missing topic"},
        )
        body = response.json()

        assert response.status_code == 200
        assert body["code"] == 108

    def test_publish_missing_payload_returns_business_error(self, nanomq_api_client):
        response = nanomq_api_client.post(
            "/mqtt/publish",
            json={"topic": unique_topic("study/api/publish")},
        )
        body = response.json()

        assert response.status_code == 200
        assert body["code"] == 108

    def test_publish_with_nonexistent_path(self, nanomq_api_client):
        response = nanomq_api_client.post(
            "/mqtt/publish/not-exist",
            json={
                "topic": unique_topic("study/api/publish"),
                "payload": "bad path",
            },
        )

        assert_not_found(response)

    def test_publish_without_auth(self, nanomq_api_client_without_auth):
        response = nanomq_api_client_without_auth.post(
            "/mqtt/publish",
            json={
                "topic": unique_topic("study/api/publish"),
                "payload": "no auth",
            },
        )

        assert_unauthorized(response)
