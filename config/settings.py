from dataclasses import dataclass
from pathlib import Path
import os
from urllib.parse import urlparse

from dotenv import load_dotenv

TEST_ENV = os.getenv("TEST_ENV", "local")
PROJECT_ROOT = Path(__file__).parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

ENVIRONMENT_FILE = PROJECT_ROOT / "config" / "environments" / f"{TEST_ENV}.env"

if not ENVIRONMENT_FILE.exists():
    raise FileNotFoundError(
        f"Environment file not found: {ENVIRONMENT_FILE}. "
        f"Set TEST_ENV to local, cloud, or ci."
    )

load_dotenv(ENVIRONMENT_FILE, override=True)

# .env覆盖其他env配置
if ENV_FILE.exists():
    load_dotenv(ENV_FILE, override=True)


def _mqtt_host(value: str) -> str:
    value = value.strip()
    if "://" not in value:
        return value
    return urlparse(value).hostname or value


@dataclass(frozen=True)
class Settings:
    nanomq_api_url: str = os.getenv("NANOMQ_API_URL", "http://localhost:8081/api/v4")
    nanomq_username: str = os.getenv("NANOMQ_USERNAME", "admin")
    nanomq_password: str = os.getenv("NANOMQ_PASSWORD", "public")
    nanomq_mqtt_host: str = _mqtt_host(os.getenv("NANOMQ_MQTT_HOST", "localhost"))
    nanomq_mqtt_port: int = int(os.getenv("NANOMQ_MQTT_PORT", "1883"))
    request_timeout: int = int(os.getenv("REQUEST_TIMEOUT", "15"))
    poll_timeout: int = int(os.getenv("POLL_TIMEOUT", "15"))
    poll_interval: float = float(os.getenv("POLL_INTERVAL", "0.5"))
    test_env: str = TEST_ENV
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
