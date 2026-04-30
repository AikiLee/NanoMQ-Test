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
