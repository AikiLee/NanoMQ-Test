# Study 1: 从通用地基开始掌握 NanoMQ 测试项目

## 目标

本阶段不追求覆盖 NanoMQ 的全部能力，而是先把自动化测试项目里最重要的三类“地基代码”练熟：

- `config`: 配置加载、环境切换、默认值、类型转换。
- `utils`: 测试数据加载、唯一命名、异步等待。
- `api_client`: HTTP 客户端封装、认证、日志、重试、诊断信息。

完成后，你应该能独立写出一个最小 NanoMQ API 测试闭环：

```text
读取配置 -> 生成唯一 topic -> 调用 NanoMQ HTTP API -> 断言响应 -> 输出可诊断日志
```

## 练习方式

不要直接照抄主项目代码。每个练习按这个流程走：

1. 先在 `nanoMQ-study/practice/` 下自己写最小版本。
2. 跑通最小 case。
3. 再打开主项目里对应文件对比，比如 `config/settings.py`、`utils/naming.py`、`api_clients/base_client.py`。
4. 记录你漏掉了什么，例如异常处理、路径处理、类型转换、日志、重试。

建议目录：

```text
nanoMQ-study/
├── docs/
│   └── study_1.md
├── practice/
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── data_loader.py
│   │   ├── naming.py
│   │   └── poller.py
│   ├── api_clients/
│   │   ├── __init__.py
│   │   ├── base_client.py
│   │   └── nanomq_api_client.py
│   ├── test_data/
│   │   ├── payloads/
│   │   │   └── telemetry.json
│   │   └── expected/
│   │       └── health_expected.json
│   └── tests/
│       ├── test_settings.py
│       ├── test_utils.py
│       └── test_nanomq_api.py
```

## 练习 1: 写一个最小 Settings

### 目标

写一个 `practice/config/settings.py`，统一管理测试环境配置。

你要掌握的点：

- 为什么测试代码不要硬编码 IP、端口、账号。
- `.env` 和默认值如何协作。
- 字符串配置如何转换成 `int` / `float`。
- 配置对象为什么适合设计成只读。

### 要求

支持这些字段：

```text
NANOMQ_API_URL
NANOMQ_USERNAME
NANOMQ_PASSWORD
NANOMQ_MQTT_HOST
NANOMQ_MQTT_PORT
REQUEST_TIMEOUT
POLL_TIMEOUT
POLL_INTERVAL
```

默认值建议：

```text
NANOMQ_API_URL=http://localhost:8081/api/v4
NANOMQ_USERNAME=admin
NANOMQ_PASSWORD=public
NANOMQ_MQTT_HOST=localhost
NANOMQ_MQTT_PORT=1883
REQUEST_TIMEOUT=10
POLL_TIMEOUT=10
POLL_INTERVAL=0.5
```

### 提示

先不要一上来做多环境切换。第一版只需要能加载 `.env` 和默认值。

推荐使用：

```python
from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv
```

路径处理建议：

```python
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"
```

这里的 `parents[2]` 要自己确认。你可以临时打印 `PROJECT_ROOT`，确认它指向 `nanoMQ-study/`。

### 参考样例

这不是完整答案，但结构可以参考：

```python
from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"

if ENV_FILE.exists():
    load_dotenv(ENV_FILE)


@dataclass(frozen=True)
class Settings:
    nanomq_api_url: str = os.getenv(
        "NANOMQ_API_URL",
        "http://localhost:8081/api/v4",
    )
    nanomq_username: str = os.getenv("NANOMQ_USERNAME", "admin")
    nanomq_password: str = os.getenv("NANOMQ_PASSWORD", "public")
    nanomq_mqtt_host: str = os.getenv("NANOMQ_MQTT_HOST", "localhost")
    nanomq_mqtt_port: int = int(os.getenv("NANOMQ_MQTT_PORT", "1883"))
    request_timeout: int = int(os.getenv("REQUEST_TIMEOUT", "10"))
    poll_timeout: float = float(os.getenv("POLL_TIMEOUT", "10"))
    poll_interval: float = float(os.getenv("POLL_INTERVAL", "0.5"))


settings = Settings()
```

### 验收测试

新建 `practice/tests/test_settings.py`：

```python
from practice.config.settings import settings


def test_settings_has_default_values():
    assert settings.nanomq_api_url.startswith("http")
    assert settings.nanomq_mqtt_port == 1883
    assert settings.request_timeout > 0
    assert settings.poll_interval > 0
```

运行：

```bash
pytest practice/tests/test_settings.py -v
```

### 常见坑

- `Path(__file__)` 得到的是当前文件路径，不是项目根目录。
- `.env` 里的值读出来都是字符串，端口和超时时间需要手动转类型。
- 不要在测试文件里到处写 `localhost:8081`，否则后面切云环境会很难维护。

## 练习 2: 增加多环境配置

### 目标

支持通过 `TEST_ENV` 切换环境文件：

```text
practice/config/environments/local.env
practice/config/environments/cloud.env
practice/config/environments/ci.env
```

你要掌握的点：

- 本地、云服务器、CI 的配置不应该混在一起。
- `.env` 可以作为个人覆盖配置。
- 环境文件不存在时，要让错误信息足够清楚。

### 要求

加载优先级建议：

```text
默认值 < config/environments/{TEST_ENV}.env < .env
```

也就是说：

- `local.env` 提供团队默认本地配置。
- `.env` 提供你个人机器上的覆盖配置。
- `TEST_ENV=cloud` 时加载 `cloud.env`。

### 参考样例

```python
TEST_ENV = os.getenv("TEST_ENV", "local")

ENVIRONMENT_FILE = (
    PROJECT_ROOT
    / "practice"
    / "config"
    / "environments"
    / f"{TEST_ENV}.env"
)

if not ENVIRONMENT_FILE.exists():
    raise FileNotFoundError(
        f"Environment file not found: {ENVIRONMENT_FILE}. "
        f"Set TEST_ENV to local, cloud, or ci."
    )

load_dotenv(ENVIRONMENT_FILE, override=False)

if ENV_FILE.exists():
    load_dotenv(ENV_FILE, override=True)
```

### 验收测试

```python
def test_settings_has_test_env():
    assert settings.test_env in {"local", "cloud", "ci"}
```

### 思考题

如果云服务器的 NanoMQ 地址是 `http://10.0.0.5:8081/api/v4`，你应该改测试代码，还是改环境配置？

正确方向：改配置，不改测试代码。

## 练习 3: 写 data_loader

### 目标

写 `practice/utils/data_loader.py`，统一读取 JSON / YAML 测试数据。

你要掌握的点：

- 测试数据和测试逻辑分离。
- 文件路径错误要快速暴露。
- 数据格式错误要报出具体文件。

### 要求

实现：

```python
load_json(path: str | Path) -> dict
load_yaml(path: str | Path) -> dict
```

### 测试数据

新建 `practice/test_data/payloads/telemetry.json`：

```json
{
  "device_id": "device-001",
  "temperature": 31.5,
  "humidity": 60
}
```

### 参考样例

```python
import json
from pathlib import Path
from typing import Any

import yaml


def load_json(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    try:
        with file_path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON file: {file_path}") from exc


def load_yaml(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    with file_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)
    return data or {}
```

### 验收测试

```python
from pathlib import Path

from practice.utils.data_loader import load_json


def test_load_json_payload():
    payload = load_json(
        Path("practice/test_data/payloads/telemetry.json")
    )

    assert payload["device_id"] == "device-001"
    assert payload["temperature"] > 30
```

### 常见坑

- 不要用相对当前运行目录的隐式路径太多，最好用 `Path` 明确拼接。
- `yaml.safe_load()` 读取空文件会返回 `None`，工具函数最好统一返回 `{}`。

## 练习 4: 写 naming 工具

### 目标

写 `practice/utils/naming.py`，生成唯一的 client id 和 topic。

你要掌握的点：

- MQTT 测试里资源名冲突会制造假失败。
- topic 和 client id 都应该在测试运行时动态生成。
- 自动化测试要能并行运行，命名不能只靠固定字符串。

### 要求

实现：

```python
unique_client_id(prefix: str = "study-client") -> str
unique_topic(prefix: str = "study/topic") -> str
```

### 参考样例

```python
from datetime import datetime, timezone
from uuid import uuid4


def _suffix() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    random_part = uuid4().hex[:8]
    return f"{timestamp}-{random_part}"


def unique_client_id(prefix: str = "study-client") -> str:
    return f"{prefix}-{_suffix()}"


def unique_topic(prefix: str = "study/topic") -> str:
    return f"{prefix}/{_suffix()}"
```

### 验收测试

```python
from practice.utils.naming import unique_client_id, unique_topic


def test_unique_client_id_is_unique():
    assert unique_client_id() != unique_client_id()


def test_unique_topic_keeps_prefix():
    topic = unique_topic("study/nanomq")

    assert topic.startswith("study/nanomq/")
```

### 常见坑

- 不要只用秒级时间戳，快速连续调用可能重复。
- 不要生成包含空格的 topic。
- topic 最好按层级组织，例如 `study/nanomq/{suffix}`。

## 练习 5: 写 poller

### 目标

写 `practice/utils/poller.py`，用条件等待替代 `time.sleep()`。

你要掌握的点：

- 异步系统测试不能靠固定等待。
- 等待逻辑应该集中封装，而不是散落在测试里。
- 超时错误要能看懂。

### 要求

实现：

```python
wait_until(predicate, timeout: float, interval: float, description: str)
```

行为：

- `predicate()` 返回真值时，立即返回这个结果。
- 超过 `timeout` 后抛 `TimeoutError`。
- 每次检查之间等待 `interval`。
- 错误信息包含 `description`。

### 参考样例

```python
import time
from collections.abc import Callable
from typing import TypeVar


T = TypeVar("T")


def wait_until(
    predicate: Callable[[], T | None | bool],
    timeout: float,
    interval: float,
    description: str,
) -> T:
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        result = predicate()
        if result:
            return result
        time.sleep(interval)

    raise TimeoutError(
        f"Timed out after {timeout}s while waiting for: {description}"
    )
```

### 验收测试

```python
import pytest

from practice.utils.poller import wait_until


def test_wait_until_returns_result():
    result = wait_until(
        lambda: {"status": "ok"},
        timeout=1,
        interval=0.1,
        description="status ok",
    )

    assert result["status"] == "ok"


def test_wait_until_timeout_message():
    with pytest.raises(TimeoutError, match="never true"):
        wait_until(
            lambda: False,
            timeout=0.2,
            interval=0.05,
            description="never true",
        )
```

### 常见坑

- 不要用 `time.time()` 做超时判断，系统时间变化会影响它；更适合用 `time.monotonic()`。
- 不要在业务测试里直接写很多 `time.sleep()`。

## 练习 6: 写最小 BaseClient

### 目标

写 `practice/api_clients/base_client.py`，用 `httpx` 封装最小 HTTP 客户端。

你要掌握的点：

- `base_url` 如何和 endpoint 拼接。
- `timeout` 为什么必须统一设置。
- HTTP client 为什么要封装，而不是每个测试里直接 `httpx.get()`。

### 要求

实现：

```python
BaseClient(base_url: str, timeout: int, auth: tuple[str, str] | None = None)
get(endpoint: str, **kwargs)
post(endpoint: str, **kwargs)
delete(endpoint: str, **kwargs)
close()
```

第一版可以先不做 Allure 和重试。

### 参考样例

```python
import httpx


class BaseClient:
    def __init__(
        self,
        base_url: str,
        timeout: int,
        auth: tuple[str, str] | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(
            timeout=httpx.Timeout(timeout),
            auth=auth,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )

    def _build_url(self, endpoint: str) -> str:
        normalized_endpoint = (
            endpoint if endpoint.startswith("/") else f"/{endpoint}"
        )
        return f"{self.base_url}{normalized_endpoint}"

    def get(self, endpoint: str, **kwargs) -> httpx.Response:
        return self.client.get(self._build_url(endpoint), **kwargs)

    def post(self, endpoint: str, **kwargs) -> httpx.Response:
        return self.client.post(self._build_url(endpoint), **kwargs)

    def delete(self, endpoint: str, **kwargs) -> httpx.Response:
        return self.client.delete(self._build_url(endpoint), **kwargs)

    def close(self) -> None:
        self.client.close()
```

### 验收测试

先只测 URL 拼接，不依赖真实 NanoMQ：

```python
from practice.api_clients.base_client import BaseClient


def test_build_url_with_slash():
    client = BaseClient("http://localhost:8081/api/v4", timeout=10)

    assert (
        client._build_url("/nodes")
        == "http://localhost:8081/api/v4/nodes"
    )

    client.close()
```

### 常见坑

- `base_url` 结尾有 `/`，endpoint 开头也有 `/`，容易拼出 `//nodes`。
- 不设置 timeout 的 HTTP 请求可能一直挂住。
- `auth` 不要在每个方法里重复传，放到 client 初始化更合理。

## 练习 7: 给 BaseClient 增加诊断能力

### 目标

把 `BaseClient` 从“能发请求”升级成“适合自动化测试排障”。

你要掌握的点：

- 自动化测试失败时，最重要的是快速知道请求了什么、返回了什么。
- GET 观察类接口可以重试，POST 发布类接口不能随便重试。
- 诊断逻辑应该封装在 client 层，而不是每条测试重复写。

### 要求

增加：

- 请求日志：method、url。
- 响应日志：status_code。
- GET 遇到 `502/503/504` 最多重试 3 次。
- POST 不重试，避免重复发布 MQTT 消息。

### 参考样例

```python
import time


RETRYABLE_STATUS_CODES = {502, 503, 504}


def _should_retry(method: str, status_code: int, attempt: int, attempts: int) -> bool:
    return (
        method.upper() == "GET"
        and status_code in RETRYABLE_STATUS_CODES
        and attempt < attempts
    )
```

请求主流程可以这样组织：

```python
def _request(self, method: str, endpoint: str, **kwargs):
    url = self._build_url(endpoint)
    attempts = 3 if method.upper() == "GET" else 1

    for attempt in range(1, attempts + 1):
        print(f"{method.upper()} {url}")
        response = self.client.request(method, url, **kwargs)
        print(f"Response {response.status_code}")

        if not _should_retry(method, response.status_code, attempt, attempts):
            return response

        time.sleep(0.3 * attempt)
```

### 验收标准

- `GET` 方法会走统一 `_request()`。
- `POST` 方法也会走统一 `_request()`。
- 重试逻辑只对 GET 生效。
- 代码里能清楚解释为什么 POST 不重试。

### 常见坑

- 不要对 publish 接口做自动重试，否则可能导致重复消息。
- 不要在异常里吞掉原始错误；连接失败应该让测试明确失败。

## 练习 8: 写 NanoMQApiClient

### 目标

基于 `BaseClient` 写 `practice/api_clients/nanomq_api_client.py`。

你要掌握的点：

- BaseClient 负责通用 HTTP 能力。
- NanoMQApiClient 负责业务 API 语义。
- 测试用例应该读起来像业务行为，而不是裸 HTTP。

### 要求

实现：

```python
get_nodes()
get_brokers()
get_metrics()
get_clients()
get_subscriptions()
get_topic_tree()
publish_message(topic: str, payload: dict)
```

### 参考样例

```python
from practice.api_clients.base_client import BaseClient


class NanoMQApiClient(BaseClient):
    def get_nodes(self):
        return self.get("/nodes")

    def get_brokers(self):
        return self.get("/brokers")

    def get_metrics(self):
        return self.get("/metrics")

    def get_clients(self):
        return self.get("/clients")

    def get_subscriptions(self):
        return self.get("/subscriptions")

    def get_topic_tree(self):
        return self.get("/topic-tree")

    def publish_message(self, topic: str, payload: dict):
        body = {
            "topic": topic,
            "payload": payload,
        }
        return self.post("/mqtt/publish", json=body)
```

注意：`publish_message()` 的具体 body 结构要以你当前 NanoMQ 版本的 API 文档或手工验证结果为准。如果接口返回不符合预期，不要先改断言，先确认请求格式。

### 验收测试

如果本地 NanoMQ 已启动：

```python
from practice.api_clients.nanomq_api_client import NanoMQApiClient
from practice.config.settings import settings


def test_get_nodes():
    client = NanoMQApiClient(
        settings.nanomq_api_url,
        timeout=settings.request_timeout,
        auth=(settings.nanomq_username, settings.nanomq_password),
    )

    response = client.get_nodes()

    assert response.status_code == 200

    client.close()
```

### 常见坑

- API 路径不要散落在测试里，统一收敛到 `NanoMQApiClient`。
- 如果不同 NanoMQ 版本返回结构有差异，先断言稳定字段，例如状态码和关键字段存在。
- 不要过早写很严格的 JSON Schema，先观察真实响应。

## 练习 9: 写第一个真实 API 测试

### 目标

把 `settings + NanoMQApiClient` 串起来，完成一个健康检查类测试。

### 要求

新建 `practice/tests/test_nanomq_api.py`。

覆盖：

- `GET /nodes`
- `GET /metrics`

### 参考样例

```python
import pytest

from practice.api_clients.nanomq_api_client import NanoMQApiClient
from practice.config.settings import settings


@pytest.fixture
def nanomq_api_client():
    client = NanoMQApiClient(
        settings.nanomq_api_url,
        timeout=settings.request_timeout,
        auth=(settings.nanomq_username, settings.nanomq_password),
    )
    yield client
    client.close()


def test_get_nodes(nanomq_api_client):
    response = nanomq_api_client.get_nodes()

    assert response.status_code == 200


def test_get_metrics(nanomq_api_client):
    response = nanomq_api_client.get_metrics()

    assert response.status_code == 200
    assert response.text
```

### 验收命令

```bash
pytest practice/tests/test_nanomq_api.py -v
```

### 如果失败，按这个顺序排查

1. NanoMQ 是否启动。
2. `NANOMQ_API_URL` 是否正确。
3. 账号密码是否正确。
4. API 端口是否暴露。
5. 当前 NanoMQ 版本是否支持这个 endpoint。

## 练习 10: 最小业务闭环

### 目标

完成一个最小业务链路：

```text
读取 payload -> 生成唯一 topic -> HTTP API publish -> 查询 metrics/topic-tree -> 断言请求成功
```

这个练习还不要求 MQTT subscriber 收消息，先只练 `config + utils + api_client` 的串联。

### 流程

```python
def test_publish_message_by_http_api(nanomq_api_client):
    topic = unique_topic("study/nanomq")
    payload = load_json("practice/test_data/payloads/telemetry.json")

    response = nanomq_api_client.publish_message(topic, payload)

    assert response.status_code in {200, 202, 204}
```

### 提示

不同 NanoMQ 版本的 HTTP publish API 可能有差异，所以这里先不要把状态码写死成一个值。等你手工确认当前版本稳定返回后，再收紧断言。

### 进阶验收

如果 `topic-tree` 能观察到 topic：

```python
tree_response = nanomq_api_client.get_topic_tree()

assert tree_response.status_code == 200
assert "study" in tree_response.text
```

如果观察不到，也不一定代表 publish 失败。topic-tree 可能依赖订阅状态或 broker 内部统计方式。这个阶段先记录现象，不要强行写死。

## 练习 11: 对比主项目实现

### 目标

完成前 10 个练习后，再去对比主项目成熟实现。

建议重点看：

```text
../config/settings.py
../utils/data_loader.py
../utils/naming.py
../utils/poller.py
../api_clients/base_client.py
../api_clients/nanomq_api_client.py
```

### 对比问题

逐项回答：

- 我的 `settings.py` 有没有支持多环境？
- 我的路径处理是否可靠？
- 我的 `BaseClient` 是否统一处理 timeout？
- 我的 `BaseClient` 是否支持 Basic Auth？
- 我的请求失败时，能不能快速看到请求 URL 和响应？
- 我的 GET 重试是否可能误伤 POST publish？
- 我的测试数据是否和测试逻辑分离？
- 我的 topic/client_id 是否能避免并行冲突？

### 输出要求

在 `nanoMQ-study/docs/study_1_review.md` 里写一页复盘：

```text
我自己实现的版本：
- 优点：
- 缺点：
- 和主项目差异：
- 下一步要补的能力：
```

## 推荐节奏

如果每天练 1 到 1.5 小时，建议这样安排：

```text
Day 1: settings + 多环境配置
Day 2: data_loader + naming
Day 3: poller + 单元测试
Day 4: BaseClient 最小版本
Day 5: BaseClient 诊断能力 + NanoMQApiClient
Day 6: 真实 NanoMQ API 测试
Day 7: 最小业务闭环 + 复盘
```

## 本阶段完成标准

你不需要把代码写得和主项目一样完整，但至少要做到：

- 能解释配置加载顺序。
- 能解释为什么测试里不能硬编码环境地址。
- 能写出 JSON/YAML loader。
- 能生成唯一 topic/client id。
- 能写出 `wait_until()` 并说明它比 `sleep()` 好在哪里。
- 能用 `httpx.Client` 封装一个最小 `BaseClient`。
- 能说明 GET 为什么可以有限重试，POST publish 为什么不应该自动重试。
- 能用 `NanoMQApiClient` 跑通至少一个真实 API。

如果这些都能做到，你对这个项目就不是“看懂结构”，而是已经掌握了第一层可迁移的工程能力。
