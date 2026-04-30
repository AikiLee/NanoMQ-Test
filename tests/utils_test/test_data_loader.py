from pathlib import Path

from utils.data_loader import load_json


def test_load_json_payload():
    payload = load_json("test_data/payloads/telemetry_event.json")

    assert payload["device"] == "edge-sensor-001"
    assert payload["temperature"] > 30


def test_load_json_load_with_Path():
    payload = load_json(Path("test_data/payloads/telemetry_event.json"))
    assert payload["device"] == "edge-sensor-001"
    assert payload["temperature"] > 30
