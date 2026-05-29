#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$ROOT_DIR/venv/bin/python"

if [[ ! -x "$PYTHON" ]]; then
  echo "Project venv not found: $PYTHON" >&2
  echo "Create it and install requirements before running checks." >&2
  exit 2
fi

cd "$ROOT_DIR"

GROUP="${1:-}"
shift || true

ALLURE_DIR=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --alluredir)
      if [[ $# -lt 2 ]]; then
        echo "--alluredir requires a directory path" >&2
        exit 2
      fi
      ALLURE_DIR="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 2
      ;;
  esac
done

PYTEST_ARGS=(-q)
if [[ -n "$ALLURE_DIR" ]]; then
  "$PYTHON" scripts/write_allure_environment.py "$ALLURE_DIR"
  PYTEST_ARGS+=(--alluredir "$ALLURE_DIR")
fi

case "$GROUP" in
  api)
    "$PYTHON" -m pytest tests/test_api "${PYTEST_ARGS[@]}"
    ;;
  contract)
    "$PYTHON" -m pytest tests/test_contracts "${PYTEST_ARGS[@]}"
    ;;
  e2e-minimal)
    "$PYTHON" -m pytest tests/test_e2e/test_minimal_business_loop.py "${PYTEST_ARGS[@]}"
    ;;
  query-filter)
    "$PYTHON" -m pytest \
      tests/test_e2e/test_clients_query_filters.py \
      tests/test_e2e/test_subscriptions_query_filters.py \
      "${PYTEST_ARGS[@]}"
    ;;
  mtls-offline)
    "$PYTHON" -m pytest tests/test_auth/test_nanomq_mtls_materials.py "${PYTEST_ARGS[@]}"
    ;;
  all-safe)
    "$PYTHON" scripts/check_env.py
    "$PYTHON" -m pytest tests/test_api tests/test_contracts "${PYTEST_ARGS[@]}"
    "$PYTHON" -m pytest tests/test_e2e/test_minimal_business_loop.py "${PYTEST_ARGS[@]}"
    "$PYTHON" -m pytest tests/test_auth/test_nanomq_mtls_materials.py "${PYTEST_ARGS[@]}"
    ;;
  *)
    cat <<'USAGE' >&2
Usage: bash scripts/run_checks.sh <group> [--alluredir DIR]

Groups:
  api           Run NanoMQ HTTP API tests.
  contract      Run JSON schema contract tests.
  e2e-minimal   Run the minimal HTTP publish -> MQTT subscriber flow.
  query-filter  Run known upstream query-filter regression checks.
  mtls-offline  Run offline mTLS material and certificate-chain checks.
  all-safe      Run checks expected to pass against a healthy environment.
USAGE
    exit 2
    ;;
esac
