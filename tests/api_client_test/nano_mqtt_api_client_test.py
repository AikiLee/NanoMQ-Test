import json

from api_clients.nanomqtt_api_client import NanoMqttApiClient
from config.settings import settings


def test_get_nodes():
    client = NanoMqttApiClient(
        settings.nanomq_api_url,
        timeout=settings.request_timeout,
        auth=(settings.nanomq_username, settings.nanomq_password),
    )

    response = client.get_nodes()

    assert response.status_code == 200

    client.close()


class RecordingNanoMqttApiClient(NanoMqttApiClient):
    def __init__(self):
        self.last_endpoint = None
        self.last_json = None

    def post(self, endpoint: str, **kwargs):
        self.last_endpoint = endpoint
        self.last_json = kwargs["json"]
        return None


def test_publish_message_serializes_dict_payload_as_json_string():
    client = RecordingNanoMqttApiClient()
    payload = {"device": "edge-sensor-001", "temperature": 35.5}

    client.publish_message("study/topic", payload)

    assert client.last_endpoint == "/mqtt/publish"
    assert client.last_json["topic"] == "study/topic"
    assert json.loads(client.last_json["payload"]) == payload
