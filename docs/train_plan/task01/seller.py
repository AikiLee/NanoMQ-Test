"""Compatibility entry point for the single-product seller exercise.

The full implementation lives in ``single_product_seller.py``. This file keeps
the shorter ``seller`` module name usable without duplicating the state-machine
code in two places.
"""

from docs.train_plan.task01.single_product_seller import (
    InvalidTransition,
    Order,
    OrderState,
    OrderStateMachine,
    Payment,
)

__all__ = [
    "InvalidTransition",
    "Order",
    "OrderState",
    "OrderStateMachine",
    "Payment",
]


class PaymentStateMachine:
    """
    组件: PaymentStateMachine
    输入: amount=5
    当前状态: PROCESSING
    事件: PAY_SUCCESS
    guard: amount >= expected_amount
    目标状态: SUCCESS
    action: paid_amount=5, paid_at=now
    不变量: SUCCESS 时 paid_amount >= expected_amount
    最小测试: PROCESSING 收到 PAY_SUCCESS 后 state == SUCCESS
    """
