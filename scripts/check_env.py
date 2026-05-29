"""Check the NanoMQ test environment configured for this project."""

from __future__ import annotations

import sys
from pathlib import Path
from threading import Event

import httpx
import paho.mqtt.client as mqtt

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import settings
from utils.naming import unique_client_id


def main() -> int:
    print(f"API URL: {settings.nanomq_api_url}")
    print(f"MQTT: {settings.nanomq_mqtt_host}:{settings.nanomq_mqtt_port}")
    print(f"Username: {settings.nanomq_username}")
    print(f"Password: {_mask(settings.nanomq_password)}")

    checks = [
        _check_http_api,
        _check_mqtt_connect,
    ]

    ok = True
    for check in checks:
        try:
            check()
        except Exception as exc:  # pragma: no cover - diagnostic script
            ok = False
            print(f"{check.__name__}: failed: {exc}")

    return 0 if ok else 1


def _check_http_api() -> None:
    with httpx.Client(
        base_url=settings.nanomq_api_url,
        auth=(settings.nanomq_username, settings.nanomq_password),
        timeout=settings.request_timeout,
    ) as client:
        brokers = _get_first_data_item(client, "/brokers")
        nodes = _get_first_data_item(client, "/nodes")

    print("Auth: ok")
    print(f"/brokers version: {brokers.get('version')}")
    print(f"/nodes version: {nodes.get('version')}")


def _get_first_data_item(client: httpx.Client, path: str) -> dict:
    response = client.get(path)
    response.raise_for_status()
    body = response.json()
    data = body.get("data")
    if not isinstance(data, list) or not data:
        raise RuntimeError(f"{path} did not return non-empty data list: {body!r}")
    if not isinstance(data[0], dict):
        raise RuntimeError(f"{path} first data item is not an object: {body!r}")
    return data[0]


def _check_mqtt_connect() -> None:
    connected = Event()
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=unique_client_id("env-check"),
        protocol=mqtt.MQTTv311,
    )

    def on_connect(client, userdata, flags, reason_code, properties):
        if not reason_code.is_failure:
            connected.set()

    client.on_connect = on_connect

    try:
        client.connect(settings.nanomq_mqtt_host, settings.nanomq_mqtt_port)
        client.loop_start()
        if not connected.wait(settings.poll_timeout):
            raise TimeoutError("MQTT connect timed out")
        print("MQTT connect: ok")
    finally:
        client.loop_stop()
        client.disconnect()


def _mask(value: str) -> str:
    if not value:
        return "<empty>"
    if len(value) <= 2:
        return "*" * len(value)
    return f"{value[0]}{'*' * (len(value) - 2)}{value[-1]}"


if __name__ == "__main__":
    raise SystemExit(main())
