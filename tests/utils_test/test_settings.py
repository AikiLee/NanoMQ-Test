import pytest
from dotenv import dotenv_values

from config.settings import PROJECT_ROOT, settings


def test_settings_has_default_values():
    assert settings.nanomq_api_url.startswith("http")
    assert settings.nanomq_mqtt_port == 1883
    assert settings.request_timeout > 0
    assert settings.poll_interval > 0
    assert settings.nanomq_mqtt_host != "localhost"
    assert "://" not in settings.nanomq_mqtt_host


def test_settings_has_test_env():
    assert settings.test_env in {"local", "cloud", "ci"}


def test_dotenv_overrides_environment_file():
    env_file = PROJECT_ROOT / ".env"
    if not env_file.exists():
        pytest.skip(".env is optional")

    dotenv_config = dotenv_values(env_file)
    if "NANOMQ_API_URL" not in dotenv_config:
        pytest.skip(".env does not override NANOMQ_API_URL")

    assert settings.nanomq_api_url == dotenv_config["NANOMQ_API_URL"]
