# NanoMQ Learning Demo

一个面向 NanoMQ 的 `pytest + requests + allure + paho-mqtt` 自动化测试项目。它从 `operations.md` 的手工闭环收敛出第一版自动化范围：Broker API、MQTT 发布订阅、HTTP API 发布 MQTT 消息、客户端/订阅观测、认证和参数负向。

## Core Flow

```text
start NanoMQ
  -> HTTP API health check
  -> MQTT subscriber connects
  -> HTTP API publishes command
  -> MQTT subscriber receives command
  -> HTTP API observes clients/subscriptions/metrics/topic-tree
```

## Structure

```text
nanomq-learning-demo/
├── api_clients/
├── config/
│   └── environments/
├── docs/
├── models/
├── schemas/
├── services/
├── scripts/
├── test_data/
├── tests/
└── utils/
```

## Prerequisites

- Python 3.11+
- Docker
- NanoMQ exposes `1883` and `8081`

## Install

```bash
cd nanomq-learning-demo
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

## Start NanoMQ

```bash
make start
```

Equivalent Docker command is kept in `scripts/start_nanomq.sh`.

## Run Tests

```bash
make smoke
make e2e
make test
```

Direct pytest:

```bash
pytest -v --alluredir=allure-results
pytest -v tests/test_publish --alluredir=allure-results
```

## Test Groups

- `tests/test_health/`: HTTP API root, nodes, brokers, metrics.
- `tests/test_clients/`: MQTT client and subscription visible through API.
- `tests/test_publish/`: HTTP API publish, batch publish, MQTT publish.
- `tests/test_contracts/`: JSON schema checks for core API responses.
- `tests/test_negative/`: missing/wrong auth and invalid publish payloads.
- `tests/test_e2e/`: HTTP API publish to MQTT subscriber plus API observation.

## Configuration

Default env file: `config/environments/local.env`.

Override with `.env`:

```bash
NANOMQ_API_URL=http://localhost:8081/api/v4
NANOMQ_USERNAME=admin
NANOMQ_PASSWORD=public
NANOMQ_MQTT_HOST=localhost
NANOMQ_MQTT_PORT=1883
```

For cloud:

```bash
TEST_ENV=cloud pytest -m smoke
```

Then edit `.env` or `config/environments/cloud.env` with your server IP.

## Scope Control

第一版不做 WebHook、Bridge、Rule Engine、TLS、ACL。原因是这些能力会显著增加配置和排错成本，不适合压缩到一周内。当前版本优先保证最能体现 IoT Broker 价值的闭环可自动化、可演示、可扩展。
