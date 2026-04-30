"""
写 api_clients/base_client.py，用 httpx 封装最小 HTTP 客户端。
你要掌握的点：
● base_url 如何和 endpoint 拼接。
● timeout 为什么必须统一设置。
● HTTP client 为什么要封装，而不是每个测试里直接 httpx.get()。

BaseClient(base_url: str, timeout: int, auth: tuple[str, str] | None = None)
get(endpoint: str, **kwargs)
post(endpoint: str, **kwargs)
delete(endpoint: str, **kwargs)
close()
"""

import httpx
import time
from utils.logger import get_logger

logger = get_logger(__name__)
RETRYABLE_STATUS_CODES = {502, 503, 504}


class BaseClient:

    def __init__(
        self, base_url: str, timeout: int, auth: tuple[str, str] | None = None
    ):
        """
        需要设置timeout, auth, header{Accept, Content-Type}
        """
        self.base_url = base_url.rstrip("/")
        self.max_get_retries = 3
        self.retry_backoff = 0.3
        self.has_auth = auth is not None
        self.client = httpx.Client(
            timeout=httpx.Timeout(timeout),
            auth=auth,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )

    def _build_url(self, endpoint: str) -> str:
        normalized_endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        return f"{self.base_url}{normalized_endpoint}"

    def _request(self, method: str, endpoint: str, **kwargs) -> httpx.Response:
        """
        对所有类型的请求进行统一的封装：
        1. 增加日志处理
        2. 重试机制
        Args:
            method (str): 指定请求方式
            endpoint (str): 请求路径

        Returns:
            httpx.Response:
        """
        url = self._build_url(endpoint)
        logger.info(f"{method.upper()} {url}")
        last_response: httpx.Response | None = None
        # 仅对get做重试
        attempts = self.max_get_retries if method.upper() == "GET" else 1
        for attempt in range(1, attempts + 1):
            try:
                response = self.client.request(method=method, url=url, **kwargs)
            except httpx.HTTPError as exc:
                raise
            logger.info("Response %s -> %s", url, response.status_code)
            if not self._should_retry(method, response, attempt, attempts):
                return response
            last_response = response
            # 每次重试进行退避
            time.sleep(self.retry_backoff * attempt)
        assert last_response is not None
        return last_response

    def _should_retry(
        self, method: str, response: httpx.Response, attempt: int, attempts: int
    ) -> bool:
        # Only retry idempotent observation calls; retrying publish could duplicate MQTT messages.
        return (
            method.upper() == "GET"
            and response.status_code in RETRYABLE_STATUS_CODES
            and attempt < attempts
        )

    def get(self, endpoint: str, **kwargs):
        return self._request("GET", endpoint, **kwargs)

    def post(self, endpoint: str, **kwargs):
        return self._request("POST", endpoint, **kwargs)

    def delete(self, endpoint: str, **kwargs):
        return self._request("DELETE", endpoint, **kwargs)

    def close(self) -> None:
        self.client.close()
