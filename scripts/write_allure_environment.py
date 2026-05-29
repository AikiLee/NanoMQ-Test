"""Write Allure environment metadata for the configured NanoMQ target."""

from __future__ import annotations

import platform
import sys
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import settings


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if len(argv) != 1:
        print("Usage: python scripts/write_allure_environment.py <allure-results-dir>")
        return 2

    results_dir = Path(argv[0])
    results_dir.mkdir(parents=True, exist_ok=True)

    properties = {
        "NANOMQ_API_URL": settings.nanomq_api_url,
        "NANOMQ_MQTT_HOST": settings.nanomq_mqtt_host,
        "NANOMQ_MQTT_PORT": str(settings.nanomq_mqtt_port),
        "NANOMQ_VERSION": _nanomq_version(),
        "TEST_ENV": settings.test_env,
        "PYTHON": platform.python_version(),
    }

    content = "\n".join(
        f"{key}={_escape_property(value)}" for key, value in properties.items()
    )
    (results_dir / "environment.properties").write_text(
        f"{content}\n", encoding="utf-8"
    )
    return 0


def _nanomq_version() -> str:
    try:
        with httpx.Client(
            base_url=settings.nanomq_api_url,
            auth=(settings.nanomq_username, settings.nanomq_password),
            timeout=settings.request_timeout,
        ) as client:
            response = client.get("/brokers")
            response.raise_for_status()
            data = response.json().get("data", [])
            if data and isinstance(data[0], dict):
                return str(data[0].get("version", "unknown"))
    except Exception as exc:  # pragma: no cover - diagnostic metadata only
        return f"unavailable ({exc})"
    return "unknown"


def _escape_property(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n")


if __name__ == "__main__":
    raise SystemExit(main())
