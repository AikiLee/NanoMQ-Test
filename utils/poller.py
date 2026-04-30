"""
utils/poller.py，用条件等待替代 time.sleep()。
你要掌握的点：
● 异步系统测试不能靠固定等待。
● 等待逻辑应该集中封装，而不是散落在测试里。
● 超时错误要能看懂。
wait_until(predicate, timeout: float, interval: float, description: str)
"""

import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def wait_until(
    predicate: Callable[[], T | None],
    timeout: float,
    interval: float,
    description: str,
) -> T:
    """

    Args:
        predicate (Callable[[], T  |  None]): _description_
        timeout (float): _description_
        interval (float): _description_
        description (str): _description_
    不要用time.time做超时判断，系统时间会影响他，使用time.monotonic
    其实这里也可以总结出time.time就是现实社会的时间，适合：记录日志，生成时间戳
    time.monotonic是单调递增的时钟，适合：计算耗时，timeout，retry，polling（不受系统时间变动影响）
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = predicate()
        if result:
            return result
        time.sleep(interval)
    raise TimeoutError(f"Timed out after {timeout}s while waiting for: {description}")
