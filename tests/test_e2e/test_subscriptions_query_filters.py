"""Behavior checks for documented /subscriptions query parameters."""

from threading import Event

import allure
import paho.mqtt.client as mqtt
import pytest

from config.settings import settings
from tests.test_api.api_assertions import assert_data_list_body
from utils.naming import unique_client_id, unique_topic
from utils.poller import wait_until

pytestmark = [pytest.mark.e2e, pytest.mark.clients, pytest.mark.regression]


@pytest.fixture
def active_subscription():
    client_id = unique_client_id("study-subscription-filter")
    topic = unique_topic("study/subscription-filter")
    connected = Event()
    subscribed = Event()
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=client_id,
        protocol=mqtt.MQTTv311,
    )

    def on_connect(client, userdata, flags, reason_code, properties):
        if not reason_code.is_failure:
            connected.set()

    def on_subscribe(client, userdata, mid, reason_codes, properties):
        subscribed.set()

    client.on_connect = on_connect
    client.on_subscribe = on_subscribe

    try:
        client.connect(settings.nanomq_mqtt_host, settings.nanomq_mqtt_port)
        client.loop_start()
        assert connected.wait(settings.poll_timeout), "MQTT client did not connect"
        result, _ = client.subscribe(topic, qos=1)
        assert result == mqtt.MQTT_ERR_SUCCESS
        assert subscribed.wait(settings.poll_timeout), "MQTT client did not subscribe"
        yield {"clientid": client_id, "topic": topic, "qos": 1}
    finally:
        client.loop_stop()
        client.disconnect()


@allure.epic("NanoMQ")
@allure.feature("Regression")
@allure.story("Subscriptions clientid/topic/qos filter")
@allure.severity(allure.severity_level.CRITICAL)
@allure.tag("regression", "known-bug", "issue-2311", "subscriptions")
def test_subscriptions_query_parameters_filter_result_set(
    nanomq_api_client, active_subscription
):
    record = wait_until(
        lambda: _find_subscription(nanomq_api_client, active_subscription),
        timeout=settings.poll_timeout,
        interval=settings.poll_interval,
        description=f"subscription {active_subscription}",
    )
    assert record == active_subscription

    filtered = _get_filtered_subscriptions(nanomq_api_client, active_subscription)

    assert active_subscription in filtered
    assert _subscriptions_not_matching(filtered, active_subscription) == []


def _get_filtered_subscriptions(nanomq_api_client, active_subscription: dict):
    response = nanomq_api_client.get(
        "/subscriptions",
        params={
            "clientid": active_subscription["clientid"],
            "topic": active_subscription["topic"],
            "qos": active_subscription["qos"],
        },
    )
    return assert_data_list_body(response)["data"]


def _find_subscription(nanomq_api_client, active_subscription: dict):
    return next(
        (
            subscription
            for subscription in _get_filtered_subscriptions(
                nanomq_api_client, active_subscription
            )
            if subscription == active_subscription
        ),
        None,
    )


def _subscriptions_not_matching(subscriptions: list[dict], expected: dict):
    return [
        subscription
        for subscription in subscriptions
        if subscription.get("clientid") != expected["clientid"]
        or subscription.get("topic") != expected["topic"]
        or subscription.get("qos") != expected["qos"]
    ]
