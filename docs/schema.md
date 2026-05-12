# Schema 测试学习笔记

这份笔记用于学习如何在当前 NanoMQ 测试项目中应用 JSON Schema 做接口契约测试。目标不是一次性学完 JSON Schema 全部能力，而是先掌握“如何用 schema 稳定地校验 API 响应结构”。

## 学习目标

需要掌握 4 件事：

1. 看懂一个 schema 文件在约束什么。
2. 能为一个 API 响应写出基础 schema。
3. 能在 pytest 里用 `jsonschema` 校验响应。
4. 知道哪些字段适合写进 schema，哪些应该留给 Python 断言。

## 基本关键词

先重点理解这些关键词：

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["code", "data"],
  "properties": {
    "code": { "const": 0 },
    "data": { "type": "array" }
  },
  "additionalProperties": true
}
```

含义：

- `$schema`：声明使用哪个 JSON Schema 版本。
- `type`：限制数据类型，比如 `object`、`array`、`string`、`integer`。
- `required`：要求对象必须包含哪些字段。
- `properties`：定义字段各自的规则。
- `items`：定义数组元素的结构。
- `enum`：限制字段只能是几个值之一。
- `const`：限制字段必须等于某个固定值，比如 `code` 必须是 `0`。
- `additionalProperties`：是否允许响应里出现 schema 没写到的额外字段。

当前项目建议先保持：

```json
"additionalProperties": true
```

原因是 NanoMQ 响应可能随版本多一些字段。学习阶段先校验关键字段，不要把 schema 写得太死。

## 响应类型分类

NanoMQ 里不是所有接口都长一样，写 schema 前要先分类型。

第一类：标准 envelope 响应：

```json
{
  "code": 0,
  "data": []
}
```

适合这些接口：

```text
/nodes
/brokers
/clients
/subscriptions
/topic-tree
```

第二类：裸对象响应：

```json
{
  "metrics": [],
  "cpuinfo": "1.2%",
  "memory": "123456",
  "connections": 1
}
```

适合：

```text
/metrics
```

这个接口不能套 `{code, data}`。

第三类：简单操作结果：

```json
{
  "code": 0
}
```

适合：

```text
/mqtt/publish
```

## Pytest 中如何连接 Schema

测试代码应该保持很薄：

```python
def test_brokers_schema(nanomq_api_client):
    response = nanomq_api_client.get_brokers()

    assert response.status_code == 200
    validate_schema(response.json(), "brokers_schema.json")
```

这里 Python 只负责：

- 调接口。
- 判断 HTTP 状态码。
- 调 schema 校验器。

响应结构细节交给 `schemas/brokers_schema.json`。

当前项目的基础结构是：

```text
schemas/
  brokers_schema.json
  clients_schema.json
  metrics_schema.json
  nodes_schema.json
  publish_response_schema.json
  subscriptions_schema.json
  topic_tree_schema.json

utils/
  schema_validator.py

tests/
  test_contracts/
    test_schema_validation.py
```

## 练习顺序

建议按这个顺序练：

1. 读懂 `schemas/brokers_schema.json`
   看它如何描述 `code`、`data`、`datetime`、`node_status`、`sysdescr`、`uptime`、`version`。

2. 自己写一个 `nodes_schema.json`
   要求校验：
   - `code == 0`
   - `data` 是数组
   - 每个 node 至少有 `connections`、`node_status`、`uptime`、`version`

3. 自己写一个 `publish_response_schema.json`
   要求校验：
   - 必须有 `code`
   - `code` 必须等于 `0`

4. 对比 `/metrics`
   重点理解为什么它不用 `code/data`，而是直接校验 `metrics/cpuinfo/memory/connections`。

5. 故意改坏一个 schema
   比如把 `connections` 改成 `"type": "string"`，再跑测试，观察 `jsonschema` 的报错路径。

## 最佳实践

- 先校验稳定字段，不要一上来覆盖所有字段。
- 对动态值只校验类型，不校验具体值，比如连接数、时间、uptime。
- 对业务固定值可以用 `const`，比如成功响应 `code: 0`。
- 对状态枚举可以用 `enum`，比如 `conn_state` 可以是 `connected/idle/disconnected`。
- 对版本差异大的接口，保留 `additionalProperties: true`。
- Schema 负责结构，Python 负责行为。比如 MQTT 是否收到消息，仍然用 Python 写。
- 如果使用 `format`，注意 Python `jsonschema` 默认不强制校验 format，需要额外启用 `FormatChecker`。

## 当前项目推荐路径

你现在最适合这样推进：

```text
第 1 步：读 brokers_schema.json，理解 object + required + properties
第 2 步：读 clients_schema.json，理解 array + items
第 3 步：读 topic_tree_schema.json，理解嵌套 array
第 4 步：读 metrics_schema.json，理解特殊响应结构
第 5 步：自己新增一个错误响应 schema，例如 unauthorized_response_schema.json
第 6 步：把 auth 失败的 401/code=104 也纳入 contract 测试
```

## Schema 和 Python 断言的分工

Schema 适合管“响应长什么样”：

- 字段是否存在。
- 字段类型是否正确。
- 数组和对象层级是否正确。
- 枚举值是否在允许范围内。
- 成功响应是否符合统一结构。

Python 适合管“系统有没有真的完成这件事”：

- HTTP 状态码是否正确。
- 鉴权是否生效。
- HTTP publish 后 MQTT subscriber 是否收到消息。
- 业务流程是否完成闭环。
- 异步状态是否在超时时间内出现。

所以 API 单接口测试可以大量使用 schema；更贴近真实业务流的 E2E 测试仍然应该用 Python 编排流程。

## 参考资料

- JSON Schema 官方关键字索引：<https://json-schema.org/understanding-json-schema/keywords>
- JSON Schema object 说明：<https://json-schema.org/understanding-json-schema/reference/object>
- JSON Schema array/items 说明：<https://json-schema.org/understanding-json-schema/reference/array>
- JSON Schema type 说明：<https://json-schema.org/understanding-json-schema/reference/type>
- Python `jsonschema` 官方校验文档：<https://python-jsonschema.readthedocs.io/en/v4.22.0/validate/>
