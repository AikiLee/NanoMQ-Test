import json
from queue import Empty, Queue
from threading import Event

import allure
import paho.mqtt.client as mqtt
import pytest

from config.settings import settings
from utils.data_loader import load_json
from utils.naming import unique_client_id, unique_topic
from utils.poller import wait_until


@pytest.mark.e2e
@allure.epic("NanoMQ")
@allure.feature("E2E")
@allure.story("HTTP publish reaches MQTT subscriber")
@allure.severity(allure.severity_level.CRITICAL)
@allure.tag("e2e", "publish", "mqtt")
def test_http_publish_reaches_mqtt_subscriber(nanomq_api_client):
    client_id = unique_client_id("study-e2e-subscriber")
    topic = unique_topic("study/e2e")
    payload = load_json("test_data/payloads/telemetry_event.json")
    received_messages: Queue[str] = Queue()
    connected = Event()
    subscribed = Event()

    subscriber = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=client_id,
        protocol=mqtt.MQTTv311,
    )

    def on_connect(client, userdata, flags, reason_code, properties):
        if not reason_code.is_failure:
            connected.set()

    def on_subscribe(client, userdata, mid, reason_codes, properties):
        subscribed.set()

    def on_message(client, userdata, message):
        received_messages.put(message.payload.decode("utf-8"))

    subscriber.on_connect = on_connect
    subscriber.on_subscribe = on_subscribe
    subscriber.on_message = on_message

    try:
        subscriber.connect(settings.nanomq_mqtt_host, settings.nanomq_mqtt_port)
        subscriber.loop_start()

        assert connected.wait(settings.poll_timeout), "MQTT subscriber did not connect"
        result, _ = subscriber.subscribe(topic, qos=0)
        assert result == mqtt.MQTT_ERR_SUCCESS
        assert subscribed.wait(settings.poll_timeout), "MQTT subscriber did not subscribe"

        response = nanomq_api_client.publish_message(topic, payload)
        assert response.status_code == 200
        assert response.json() == {"code": 0}

        message_payload = wait_until(
            _next_received_message(received_messages),
            timeout=settings.poll_timeout,
            interval=settings.poll_interval,
            description=f"MQTT message on topic {topic}",
        )
        assert json.loads(message_payload) == payload

        metrics_response = nanomq_api_client.get_metrics()
        assert metrics_response.status_code == 200

        subscriptions_response = nanomq_api_client.get_subscriptions()
        assert subscriptions_response.status_code == 200
        subscriptions = subscriptions_response.json()["data"]
        assert any(
            subscription["clientid"] == client_id and subscription["topic"] == topic
            for subscription in subscriptions
        )

        topic_tree_response = nanomq_api_client.get_topic_tree()
        assert topic_tree_response.status_code == 200
    finally:
        subscriber.loop_stop()
        subscriber.disconnect()


def _next_received_message(received_messages: Queue[str]):
    def read_message():
        try:
            return received_messages.get_nowait()
        except Empty:
            return None

    return read_message
