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
