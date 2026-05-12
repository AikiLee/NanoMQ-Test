import pytest

from utils.naming import unique_topic
from utils.schema_validator import validate_schema


@pytest.mark.contract
class TestSchemaValidation:
    def test_nodes_schema(self, nanomq_api_client):
        response = nanomq_api_client.get_nodes()

        assert response.status_code == 200
        validate_schema(response.json(), "nodes_schema.json")

    def test_brokers_schema(self, nanomq_api_client):
        response = nanomq_api_client.get_brokers()

        assert response.status_code == 200
        validate_schema(response.json(), "brokers_schema.json")

    def test_clients_schema(self, nanomq_api_client):
        response = nanomq_api_client.get_clients()

        assert response.status_code == 200
        validate_schema(response.json(), "clients_schema.json")

    def test_subscriptions_schema(self, nanomq_api_client):
        response = nanomq_api_client.get_subscriptions()

        assert response.status_code == 200
        validate_schema(response.json(), "subscriptions_schema.json")

    def test_topic_tree_schema(self, nanomq_api_client):
        response = nanomq_api_client.get_topic_tree()

        assert response.status_code == 200
        validate_schema(response.json(), "topic_tree_schema.json")

    def test_metrics_schema(self, nanomq_api_client):
        response = nanomq_api_client.get_metrics()

        assert response.status_code == 200
        validate_schema(response.json(), "metrics_schema.json")

    def test_publish_response_schema(self, nanomq_api_client):
        response = nanomq_api_client.publish_message(
            topic=unique_topic("study/contract/publish"),
            payload="hello from contract test",
        )

        assert response.status_code == 200
        validate_schema(response.json(), "publish_response_schema.json")
