"""
基于 BaseClient 写 practice/api_clients/nanomq_api_client.py。
你要掌握的点：
● BaseClient 负责通用 HTTP 能力。
● NanoMQApiClient 负责业务 API 语义。
● 测试用例应该读起来像业务行为，而不是裸 HTTP。


get_nodes()
get_brokers()
get_metrics()
get_clients()
get_subscriptions()
get_topic_tree()
publish_message(topic: str, payload: dict)
这里很明显就是复用BaseClient中的提供的功能实现基础功能
"""

import json
from typing import Any

from api_clients.base_client import BaseClient


class NanoMqttApiClient(BaseClient):
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

    def publish_message(self, topic: str, payload: Any):
        publish_payload = (
            json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            if isinstance(payload, dict | list)
            else payload
        )
        body = {"topic": topic, "payload": publish_payload}
        return self.post("/mqtt/publish", json=body)
