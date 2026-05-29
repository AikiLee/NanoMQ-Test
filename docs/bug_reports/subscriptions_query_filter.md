# Bug Report: `/subscriptions` Query Filters Are Ignored

## Summary

`GET /api/v4/subscriptions` accepts `clientid`, `topic`, and `qos` query
parameters, but NanoMQ returns subscriptions that do not match those filters.

- NanoMQ version: `0.24.13-2`
- GitHub issue: https://github.com/nanomq/nanomq/issues/2311
- Related but distinct issue: https://github.com/nanomq/nanomq/issues/2279

## Manual Reproduction

Keep one MQTT client subscribed:

```text
clientid = manual-sub-filter-20260528171036
topic    = manual/sub-filter/manual-sub-filter-20260528171036
qos      = 1
```

Query the HTTP API:

```bash
curl --basic -u admin:public \
  "http://localhost:8081/api/v4/subscriptions?clientid=manual-sub-filter-20260528171036&topic=manual/sub-filter/manual-sub-filter-20260528171036&qos=1"
```

## Expected Result

Only the matching subscription should be returned:

```json
{
  "clientid": "manual-sub-filter-20260528171036",
  "topic": "manual/sub-filter/manual-sub-filter-20260528171036",
  "qos": 1
}
```

## Actual Result

Unrelated subscriptions are returned with different `clientid`, `topic`, and
`qos` values:

```json
{
  "code": 0,
  "data": [
    {
      "clientid": "CENSYS",
      "topic": "#",
      "qos": 0
    },
    {
      "clientid": "test",
      "topic": "$SYS/#",
      "qos": 0
    },
    {
      "clientid": "test",
      "topic": "#",
      "qos": 0
    },
    {
      "clientid": "manual-sub-filter-20260528171036",
      "topic": "manual/sub-filter/manual-sub-filter-20260528171036",
      "qos": 1
    }
  ]
}
```

## Automated Reproduction

Run the focused regression test:

```bash
./venv/bin/python -m pytest \
  tests/test_e2e/test_subscriptions_query_filters.py::test_subscriptions_query_parameters_filter_result_set \
  -q -vv
```

The test creates a unique MQTT client, subscribes to a unique topic with QoS 1,
then queries `/subscriptions` with the exact `clientid`, `topic`, and `qos`
filters. It fails when any unrelated subscription remains in the result set.

## Relationship to `#2279`

This issue is similar in failure mode to `#2279`: both are query-parameter
semantic filtering bugs where the API returns `200 OK` and a valid response
shape, but the result set is not constrained by the query parameters.

It is not a duplicate because `#2279` affects `/api/v4/clients?conn_state=...`;
this report affects `/api/v4/subscriptions?clientid=...&topic=...&qos=...`.
