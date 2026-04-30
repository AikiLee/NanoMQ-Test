"""
NanoMQ /clients API tests.
"""

from tests.test_api.api_assertions import (
    assert_data_list_body,
    assert_success_body,
    assert_unauthorized,
)


class TestClients:
    """
    get测试方案:
    1. test success
    2. test field
    3. test with params: negative
    4. test get clients with nonexistent
    5. test auth
    """

    def test_clients_success(self, nanomq_api_client):
        response = nanomq_api_client.get_clients()

        assert response.status_code == 200

    def test_clients_fields_match(self, nanomq_api_client):
        response = nanomq_api_client.get_clients()
        body = assert_data_list_body(response)

        for client in body["data"]:
            assert {
                "client_id",
                "username",
                "keepalive",
                "conn_state",
                "clean_start",
                "proto_name",
                "proto_ver",
            } <= client.keys()
            assert isinstance(client["client_id"], str)
            assert isinstance(client["username"], str)
            assert isinstance(client["keepalive"], int)
            assert client["conn_state"] in {"connected", "idle", "disconnected"}
            assert isinstance(client["clean_start"], bool)
            assert isinstance(client["proto_name"], str)
            assert isinstance(client["proto_ver"], int)

    def test_clients_with_invalid_params_are_ignored(self, nanomq_api_client):
        response = nanomq_api_client.get(
            "/clients",
            params={"clientid": "not-exist", "unexpected": "value"},
        )
        body = assert_data_list_body(response)

        assert "data" in body

    def test_get_client_with_nonexistent_clientid(self, nanomq_api_client):
        response = nanomq_api_client.get("/clients/not-exist")
        body = assert_success_body(response)

        assert body["data"] == []

    def test_get_clients_without_auth(self, nanomq_api_client_without_auth):
        response = nanomq_api_client_without_auth.get_clients()

        assert_unauthorized(response)
