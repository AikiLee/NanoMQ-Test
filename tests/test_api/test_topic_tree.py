"""
NanoMQ /topic-tree API tests.
"""

from tests.test_api.api_assertions import (
    assert_data_list_body,
    assert_not_found,
    assert_unauthorized,
)


class TestTopicTree:
    """
    get测试方案:
    1. test success
    2. test field
    3. test with params: negative
    4. test get topic-tree with nonexistent
    5. test auth
    """

    def test_topic_tree_success(self, nanomq_api_client):
        response = nanomq_api_client.get_topic_tree()

        assert response.status_code == 200

    def test_topic_tree_fields_match(self, nanomq_api_client):
        response = nanomq_api_client.get_topic_tree()
        body = assert_data_list_body(response)

        for level in body["data"]:
            assert isinstance(level, list)
            for node in level:
                assert {"topic", "cld_cnt"} <= node.keys()
                assert isinstance(node["topic"], str)
                assert isinstance(node["cld_cnt"], int)
                if "clientid" in node:
                    assert isinstance(node["clientid"], list)
                    assert all(isinstance(client_id, str) for client_id in node["clientid"])

    def test_topic_tree_with_invalid_params_are_ignored(self, nanomq_api_client):
        response = nanomq_api_client.get(
            "/topic-tree",
            params={"topic": "not/exist", "unexpected": "value"},
        )
        body = assert_data_list_body(response)

        assert "data" in body

    def test_get_topic_tree_with_nonexistent_path(self, nanomq_api_client):
        response = nanomq_api_client.get("/topic-tree/not-exist")

        assert_not_found(response)

    def test_get_topic_tree_without_auth(self, nanomq_api_client_without_auth):
        response = nanomq_api_client_without_auth.get_topic_tree()

        assert_unauthorized(response)
