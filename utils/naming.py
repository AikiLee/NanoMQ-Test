"""
写 practice/utils/naming.py，生成唯一的 client id 和 topic。
你要掌握的点：
● MQTT 测试里资源名冲突会制造假失败。
● topic 和 client id 都应该在测试运行时动态生成。
● 自动化测试要能并行运行，命名不能只靠固定字符串。

unique_client_id(prefix: str = "study-client") -> str
unique_topic(prefix: str = "study/topic") -> str
"""

from datetime import datetime, timezone
from uuid import uuid4


def _suffix() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    random_part = uuid4().hex[:8]
    return f"{timestamp}-{random_part}"


def unique_client_id(prefix: str = "study-client") -> str:
    """
    根据传入prefix构造client-id

    Args:
        prefix (str, optional): _description_. Defaults to "study-client".
    """
    return f"{prefix}-{_suffix()}"


def unique_topic(prefix: str = "study-topic") -> str:
    """
    根据传入参数构建topic

    Args:
        prefix (str, optional): _description_. Defaults to "study-topic".
    """
    return f"{prefix}/{_suffix()}"
