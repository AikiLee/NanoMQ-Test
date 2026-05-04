from config.settings import settings


def test_settings_has_default_values():
    assert settings.nanomq_api_url.startswith("http")
    assert settings.nanomq_mqtt_port == 1883
    assert settings.request_timeout > 0
    assert settings.poll_interval > 0
    assert settings.nanomq_mqtt_host != "localhost"
    assert "://" not in settings.nanomq_mqtt_host


def test_settings_has_test_env():
    assert settings.test_env in {"local", "cloud", "ci"}
