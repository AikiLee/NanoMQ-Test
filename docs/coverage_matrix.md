# NanoMQ Test Coverage Matrix

This matrix describes the current automated coverage by behavior area. It is
meant to make the project easier to review, reproduce, and extend.

| Area | Endpoint/Flow | Test Type | File | Coverage | Current Status | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| API health | `/nodes` | API | `tests/test_api/test_nodes.py` | Success, response fields, invalid params, nonexistent path, missing auth | Automated | Confirms node version and runtime status shape. |
| API health | `/brokers` | API | `tests/test_api/test_brokers.py` | Success, response fields, invalid params, nonexistent path, missing auth | Automated | Confirms broker metadata and version shape. |
| API health | `/metrics` | API | `tests/test_api/test_metrics.py` | Success and metrics response shape | Automated | `/metrics` uses a bare metrics object, not the common `code/data` envelope. |
| Client observation | `/clients` | API | `tests/test_api/test_clients.py` | Success, fields, invalid params, nonexistent client, missing auth | Automated | Structural coverage only; it does not prove query params filter the result set. |
| Client query filtering | `/clients?conn_state=...` | E2E regression | `tests/test_e2e/test_clients_query_filters.py` | Creates a live MQTT client and checks connected/disconnected filters | Known upstream issue | Related to NanoMQ issue `#2279`; kept as behavior-level regression coverage. |
| Subscription observation | `/subscriptions` | API | `tests/test_api/test_subscriptions.py` | Success, fields, invalid params, nonexistent client, missing auth | Automated | Structural coverage only; semantic filtering is covered separately. |
| Subscription query filtering | `/subscriptions?clientid=...&topic=...&qos=...` | E2E regression | `tests/test_e2e/test_subscriptions_query_filters.py` | Creates a live subscription and asserts filtered results contain no unrelated rows | Known upstream issue | Reported as NanoMQ issue `#2311`; expected to fail until upstream fixes filtering. |
| Topic tree | `/topic-tree` | API | `tests/test_api/test_topic_tree.py` | Success, response fields, invalid params, missing auth | Automated | Observes topic tree state exposed by NanoMQ. |
| Publish | `/mqtt/publish` | API | `tests/test_api/test_publish.py` | Successful publish and invalid payload cases | Automated | Missing topic/payload returns NanoMQ business code, not necessarily an HTTP error. |
| Contract schemas | `/nodes`, `/brokers`, `/clients`, `/subscriptions`, `/topic-tree`, `/mqtt/publish`, `/metrics` | Contract | `tests/test_contracts/test_schema_validation.py` | JSON schema validation for core API response families | Automated | Keeps response-shape checks separate from behavior assertions. |
| Minimal business loop | HTTP publish to MQTT subscriber | E2E | `tests/test_e2e/test_minimal_business_loop.py` | MQTT subscriber connects, HTTP API publishes, subscriber receives payload, API observations checked | Automated | Primary end-to-end flow for broker behavior. |
| mTLS materials | Generated CA, server, device, wrong-device certs | Auth/TLS offline | `tests/test_auth/test_nanomq_mtls_materials.py` | Certificate generation and OpenSSL chain validation | Automated | Does not require a running NanoMQ process. |
| mTLS runtime | TLS client connection to NanoMQ | E2E/Auth | `tests/test_e2e/test_nanomq_mtls.py` | Positive and negative TLS connection scenarios | Optional | Requires a local NanoMQ instance started with generated mTLS config. |
| Utilities | naming, poller, settings, data loader | Unit | `tests/utils_test/` | Helper behavior and environment loading | Automated | Supports stable E2E setup and reproducible test data loading. |

## Run Groups

Use `scripts/run_checks.sh` as the stable entry point:

```bash
bash scripts/run_checks.sh api
bash scripts/run_checks.sh contract
bash scripts/run_checks.sh e2e-minimal
bash scripts/run_checks.sh query-filter
bash scripts/run_checks.sh mtls-offline
bash scripts/run_checks.sh all-safe
```

`query-filter` intentionally includes known upstream filtering regressions and
can fail while the upstream NanoMQ issues remain open.

## Allure Reporting

Generate a green quality-gate report:

```bash
bash scripts/run_checks.sh all-safe --alluredir allure-results-safe
```

Generate a known-bug reproduction report:

```bash
bash scripts/run_checks.sh query-filter --alluredir allure-results-known-bugs
```

The Allure reports measure tests by these dimensions:

| Dimension | Meaning |
| --- | --- |
| `epic` | Project under test, currently `NanoMQ`. |
| `feature` | Test area such as `HTTP API`, `Contract`, `E2E`, `Auth`, or `Regression`. |
| `story` | Concrete API behavior or workflow under test. |
| `tag` | Operational grouping such as `api`, `contract`, `e2e`, `known-bug`, `issue-2279`, or `issue-2311`. |
| `severity` | Relative risk. Query-filter regressions are `critical`; structure and offline checks are `normal`. |

When `--alluredir` is provided, `scripts/run_checks.sh` also writes
`environment.properties` with the configured NanoMQ API URL, MQTT host, NanoMQ
version, Python version, and `TEST_ENV`. Passwords are not written to the report.

HTTP API tests attach sanitized request and response evidence to Allure. This
makes failures easier to inspect without exposing auth headers or passwords.
