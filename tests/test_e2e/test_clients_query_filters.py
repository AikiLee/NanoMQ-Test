"""
Regression coverage for NanoMQ issue #2279.

The bug report was about `/api/v4/clients?conn_state=connected` not changing the
result set. These tests create a real MQTT client first, then verify the HTTP API
state filters against that known client. This keeps the reproduction stable:
if NanoMQ ignores `conn_state`, the same live client appears in the disconnected
query and the test fails deterministically.
"""

from threading import Event

import paho.mqtt.client as mqtt
import pytest

from config.settings import settings
from tests.test_api.api_assertions import assert_data_list_body
from utils.naming import unique_client_id
from utils.poller import wait_until

pytestmark = [pytest.mark.e2e, pytest.mark.clients, pytest.mark.regression]


@pytest.fixture
def connected_mqtt_client_id():
    """Create one known connected client that the /clients API must be able to filter."""
    client_id = unique_client_id("study-clients-filter")
    connected = Event()
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,  # type: ignore
        client_id=client_id,
        protocol=mqtt.MQTTv311,
    )

    def on_connect(client, userdata, flags, reason_code, properties):
        if not reason_code.is_failure:
            connected.set()

    client.on_connect = on_connect

    try:
        client.connect(settings.nanomq_mqtt_host, settings.nanomq_mqtt_port)
        client.loop_start()
        assert connected.wait(settings.poll_timeout), "MQTT client did not connect"
        yield client_id
    finally:
        client.loop_stop()
        client.disconnect()


def test_clients_conn_state_connected_filter_returns_live_client(
    nanomq_api_client, connected_mqtt_client_id
):
    """`conn_state=connected` should include the live client and only connected rows."""
    record = wait_until(
        lambda: _find_client(
            nanomq_api_client,
            client_id=connected_mqtt_client_id,
            conn_state="connected",
        ),
        timeout=settings.poll_timeout,
        interval=settings.poll_interval,
        description=f"client {connected_mqtt_client_id} in connected filter",
    )

    assert record["conn_state"] == "connected"

    connected_clients = _get_clients(nanomq_api_client, conn_state="connected")
    wrong_state_clients = _clients_not_in_state(connected_clients, "connected")
    assert not wrong_state_clients, (
        "`conn_state=connected` returned clients in other states: "
        f"{wrong_state_clients}"
    )


def test_clients_conn_state_disconnected_filter_excludes_live_client(
    nanomq_api_client, connected_mqtt_client_id
):
    """
    `conn_state=disconnected` must not return a client that is still connected.

    This is the strongest guard for #2279: when query params are ignored, the
    disconnected query degenerates into "all clients" and includes our live one.
    """
    wait_until(
        lambda: _find_client(
            nanomq_api_client,
            client_id=connected_mqtt_client_id,
            conn_state="connected",
        ),
        timeout=settings.poll_timeout,
        interval=settings.poll_interval,
        description=f"client {connected_mqtt_client_id} visible before negative filter",
    )

    disconnected_clients = _get_clients(nanomq_api_client, conn_state="disconnected")
    wrong_state_clients = _clients_not_in_state(disconnected_clients, "disconnected")

    assert not wrong_state_clients, (
        "`conn_state=disconnected` returned clients in other states: "
        f"{wrong_state_clients}"
    )
    assert connected_mqtt_client_id not in {
        client["client_id"] for client in disconnected_clients
    }


def _get_clients(nanomq_api_client, *, conn_state: str) -> list[dict]:
    response = nanomq_api_client.get("/clients", params={"conn_state": conn_state})
    body = assert_data_list_body(response)
    return body["data"]


def _find_client(nanomq_api_client, *, client_id: str, conn_state: str) -> dict | None:
    return next(
        (
            client
            for client in _get_clients(nanomq_api_client, conn_state=conn_state)
            if client["client_id"] == client_id
        ),
        None,
    )


def _clients_not_in_state(clients: list[dict], expected_state: str) -> list[dict]:
    return [
        {
            "client_id": client["client_id"],
            "conn_state": client["conn_state"],
        }
        for client in clients
        if client["conn_state"] != expected_state
    ]
