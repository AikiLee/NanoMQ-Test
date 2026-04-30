import pytest
from utils.poller import wait_until


def test_wait_until_returns_result():
    """
    正常测试
    """
    result = wait_until(
        lambda: {"status": "ok"},
        timeout=1,
        interval=0.1,
        description="status ok",
    )

    assert result["status"] == "ok"


def test_wait_until_timeout_message():
    """
    异常测试
    """
    with pytest.raises(TimeoutError, match="never true"):
        wait_until(
            lambda: False,
            timeout=0.2,
            interval=0.05,
            description="never true",
        )
