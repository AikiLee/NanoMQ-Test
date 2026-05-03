"""
todo
基本逻辑读取配置
读取配置
-> 生成 unique_client_id
-> 生成 unique_topic
-> 启动 MQTT subscriber
-> subscriber 订阅 unique_topic
-> 等待订阅成功
-> 通过 HTTP API POST /mqtt/publish
-> 断言 publish 返回 code=0
-> wait_until 等待 subscriber 收到消息
-> 断言收到的 payload 和发送 payload 一致
-> 可选查询 /clients、/subscriptions、/topic-tree
-> 断开 subscriber

现在这里有问题：
1. 能不能复用之前的api函数和fixture函数：
A：不能，pytest的context.py作用于当前
2. 如何设计测试链路: 读取 payload -> 生成唯一 topic -> HTTP API publish -> 查询 metrics/topic-tree -> 断言请求成功
    - 构造测试数据：unique_topic; payload
    -
"""

from utils.data_loader import load_json
from utils.naming import unique_topic


def test_publish_message_by_http_api(nanomq_api_client):
    topic = unique_topic("study/e2e")
    payload = load_json("test_data/payloads/telemetry_event.json")

    response = nanomq_api_client.publish_message(topic, payload)
    # breakpoint()
    assert response.status_code == 200
    assert response.json()["code"] == 0

    metrics_response = nanomq_api_client.get_metrics()
    # breakpoint()
    assert metrics_response.status_code == 200
