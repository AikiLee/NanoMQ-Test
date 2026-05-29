"""
“只卖一种饮料的极简售货机”
商品价格固定：5 元
初始库存：2
初始商家余额：0
同一时间只处理一个订单

用户可以下单
下单后可以支付账单
支付可能成功、失败、超时
用户可以在支付前取消并释放库存
支付成功后进入出货流程
出货成功后订单完成，商家余额增加
出货失败后需要退款，并释放库存或进入人工处理
管理员可以补货

设计原则：
这个案例不再适合把所有变量组合成一个大状态。
订单状态、库存数量、商家余额是不同维度：

1. OrderStateMachine 只管理订单主生命周期
2. stock / merchant_balance / current_order 放在 context 中
3. AVAILABLE / SOLD_OUT 不单独保存为状态，而是由 stock 派生
4. transition 由 state + event + guard(context) 决定
5. 副作用放在 action(context) 中执行

这样可以避免组合状态爆炸，例如：
(PENDING_PAYMENT, stock=2, balance=0)
(PENDING_PAYMENT, stock=1, balance=0)
(DISPENSING, stock=1, balance=5)
这些不应该都变成独立状态。

状态：
OrderStateMachine:
NONE               当前没有订单
PENDING_PAYMENT    已下单，等待支付
READY_TO_DISPENSE  已支付，等待出货
PAYMENT_FAILED     支付失败，订单终止
PAYMENT_TIMEOUT    支付超时，订单终止
CANCELLED          用户取消，订单终止
DISPENSING         正在出货
COMPLETED          出货成功，订单完成
DISPENSE_FAILED    出货失败，需要退款或人工处理

PaymentStateMachine:
NONE        还未创建支付
PAYMENT_CREATED    已经创建支付单
PAYMENT_PROCESSING 正在支付
PAYMENT_SUCCESS    支付成功
PAYMENT_FAILED     支付失败
REFUNDING          退款中
REFUND_SUCCESS     已退款
REFUND_FAILED      退款失败
TIMEPOUT           支付失败

派生状态：
inventory_status = AVAILABLE if stock > 0 else SOLD_OUT

context:
stock             当前可售库存，初始为 2
merchant_balance  商家余额，初始为 0
current_order     当前订单，初始为 None
price             商品价格，固定为 5
paid_amount       当前订单已支付金额
pay_time          支付时间

event:
PLACE_ORDER       用户下单
PAY_SUCCESS       支付成功
PAY_FAILED        支付失败
PAY_TIMEOUT       支付超时
CANCEL_PAY        取消支付
START_DISPENSE    开始出货
DISPENSE_OK       出货成功
DISPENSE_FAILED   出货失败
RESTOCK           管理员补货

用户/系统主动触发：
CREATE_PAYMENT_RECORD
START_PAY
CANCEL_PAYMENT
START_REFUND

第三方支付系统回调：
PAY_SUCCESS
PAY_FAILED
PAY_TIMEOUT
REFUND_SUCCESS
REFUND_FAILED

转移表：



关键选择：
下单时预占库存。
原因是如果等出货时才扣库存，多个待支付订单可能同时占用同一份库存，
支付成功后才发现无货，流程会变复杂。

transition:
业务事件        | 当前订单状态        | guard(context)              | 目标订单状态         | action(context)                         | 合法性
PLACE_ORDER     | 无活动订单状态      | stock > 0                   | PENDING_PAYMENT      | stock -= 1; create_order                | 1
PLACE_ORDER     | 无活动订单状态      | stock == 0                  | 原状态不变           | none; return SOLD_OUT                   | 0
PLACE_ORDER     | 非 NONE             | current_order exists        | 原状态不变           | none; return ORDER_EXISTS               | 0

PAY_SUCCESS     | PENDING_PAYMENT     | paid_amount >= price        | READY_TO_DISPENSE    | record_payment(pay_time)                | 1
PAY_SUCCESS     | PENDING_PAYMENT     | paid_amount < price         | PAYMENT_FAILED       | stock += 1; refund_or_reject_payment    | 1
PAY_SUCCESS     | 非 PENDING_PAYMENT  | -                           | 原状态不变           | none                                    | 0

PAY_FAILED      | PENDING_PAYMENT     | -                           | PAYMENT_FAILED       | stock += 1; clear_order                 | 1
PAY_TIMEOUT     | PENDING_PAYMENT     | -                           | PAYMENT_TIMEOUT      | stock += 1; clear_order                 | 1
CANCEL_PAY      | PENDING_PAYMENT     | -                           | CANCELLED            | stock += 1; clear_order                 | 1

START_DISPENSE  | READY_TO_DISPENSE   | current_order is paid       | DISPENSING           | start_dispense                          | 1
DISPENSE_OK     | DISPENSING          | -                           | COMPLETED            | merchant_balance += price; clear_order  | 1
DISPENSE_FAILED | DISPENSING          | -                           | DISPENSE_FAILED      | refund; stock += 1; clear_order         | 1

RESTOCK         | ANY                 | amount > 0                  | 原订单状态不变       | stock += amount                         | 1

非法转移示例：
NONE 收到 PAY_SUCCESS 是非法的，因为没有待支付订单
PENDING_PAYMENT 收到 START_DISPENSE 是非法的，因为还没有支付成功
COMPLETED 收到 CANCEL_PAY 是非法的，因为订单已经结束
DISPENSING 收到 PAY_FAILED 是非法的，因为支付阶段已经结束

不变量：
stock >= 0
merchant_balance >= 0
订单状态为 NONE 时，current_order 必须为 None
订单状态为 PENDING_PAYMENT / READY_TO_DISPENSE / DISPENSING 时，current_order 必须存在
进入 PENDING_PAYMENT 时必须已经预占 1 个库存
PAYMENT_FAILED / PAYMENT_TIMEOUT / CANCELLED 必须释放预占库存
COMPLETED 只能由 DISPENSING + DISPENSE_OK 进入
DISPENSE_OK 才能增加 merchant_balance

与 order_state.py 的区别：
order_state.py 是单一生命周期状态机，可以直接使用：
(state, event) -> next_state

当前售货机有库存、余额、订单等多个业务变量，更适合使用：
(state, event, guard(context)) -> (next_state, action(context))

状态机负责判断事件在当前阶段是否合法。
context 负责保存业务数据。
guard 负责判断业务条件。
action 负责执行库存、余额、订单等副作用。

"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Callable


class InvalidTransition(Exception):
    pass


class OrderState(str, Enum):
    NONE = "NONE"
    PENDING_PAYMENT = "PENDING_PAYMENT"
    READY_TO_DISPENSE = "READY_TO_DISPENSE"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    PAYMENT_TIMEOUT = "PAYMENT_TIMEOUT"
    CANCELLED = "CANCELLED"
    DISPENSING = "DISPENSING"
    COMPLETED = "COMPLETED"
    DISPENSE_FAILED = "DISPENSE_FAILED"


class PaymentState(str, Enum):
    NONE = "NONE"
    WAITING = "WAITING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    REFUNDING = "REFUNDING"
    REFUNDED = "REFUNDED"
    REFUND_FAILED = "REFUND_FAILED"


class OrderStateMachine:
    """Order lifecycle state machine.

    It only owns order state. It does not reserve stock, store order data,
    process payment, dispense items, or update merchant balance.
    """

    def __init__(self) -> None:
        self.state = OrderState.NONE
        self.trace: list[tuple[OrderState, str, OrderState]] = []

    def place_order(self) -> OrderState:
        if self.state not in IDLE_STATES:
            allowed = ", ".join(state.value for state in IDLE_STATES)
            raise InvalidTransition(
                f"Cannot handle PLACE_ORDER in {self.state.value}; "
                f"allowed states: {allowed}"
            )
        return self._transition("PLACE_ORDER", OrderState.PENDING_PAYMENT)

    def mark_paid(self) -> OrderState:
        self._ensure_state("MARK_PAID", OrderState.PENDING_PAYMENT)
        return self._transition("MARK_PAID", OrderState.READY_TO_DISPENSE)

    def mark_payment_failed(self) -> OrderState:
        self._ensure_state("PAY_FAILED", OrderState.PENDING_PAYMENT)
        return self._transition("PAY_FAILED", OrderState.PAYMENT_FAILED)

    def mark_payment_timeout(self) -> OrderState:
        self._ensure_state("PAY_TIMEOUT", OrderState.PENDING_PAYMENT)
        return self._transition("PAY_TIMEOUT", OrderState.PAYMENT_TIMEOUT)

    def cancel_pay(self) -> OrderState:
        self._ensure_state("CANCEL_PAY", OrderState.PENDING_PAYMENT)
        return self._transition("CANCEL_PAY", OrderState.CANCELLED)

    def start_dispense(self) -> OrderState:
        self._ensure_state("START_DISPENSE", OrderState.READY_TO_DISPENSE)
        return self._transition("START_DISPENSE", OrderState.DISPENSING)

    def complete(self) -> OrderState:
        self._ensure_state("DISPENSE_OK", OrderState.DISPENSING)
        return self._transition("DISPENSE_OK", OrderState.COMPLETED)

    def mark_dispense_failed(self) -> OrderState:
        self._ensure_state("DISPENSE_FAILED", OrderState.DISPENSING)
        return self._transition("DISPENSE_FAILED", OrderState.DISPENSE_FAILED)

    def _transition(self, event: str, next_state: OrderState) -> OrderState:
        old_state = self.state
        self.state = next_state
        self.trace.append((old_state, event, next_state))
        return self.state

    def _ensure_state(self, event: str, *allowed_states: OrderState) -> None:
        if self.state not in allowed_states:
            allowed = ", ".join(state.value for state in allowed_states)
            raise InvalidTransition(
                f"Cannot handle {event} in {self.state.value}; "
                f"allowed states: {allowed}"
            )


IDLE_STATES = {
    OrderState.NONE,
    OrderState.PAYMENT_FAILED,
    OrderState.PAYMENT_TIMEOUT,
    OrderState.CANCELLED,
    OrderState.COMPLETED,
    OrderState.DISPENSE_FAILED,
}


@dataclass
class Order:
    order_id: int
    price: int
    paid_amount: int = 0
    pay_time: datetime | None = None


@dataclass
class Payment:
    payment_id: int
    order_id: int
    expected_amount: int
    paid_amount: int = 0
    refunded_amount: int = 0
    paid_at: datetime | None = None
    refunded_at: datetime | None = None


class PaymentStateMachine:
    """Payment lifecycle state machine.

    It only owns payment state. It does not reserve stock, update order state,
    dispense items, or add merchant balance.
    """

    def __init__(self, expected_amount: int) -> None:
        if expected_amount <= 0:
            raise ValueError("expected_amount must be > 0")

        self.expected_amount = expected_amount
        self.state = PaymentState.NONE
        self.current_payment: Payment | None = None
        self.trace: list[tuple[PaymentState, str, PaymentState]] = []
        self._next_payment_id = 1

    def create_payment(self, order_id: int) -> Payment:
        event = "CREATE_PAYMENT"
        self._ensure_state(event, PaymentState.NONE)
        if order_id <= 0:
            raise ValueError("order_id must be > 0")

        payment = Payment(
            payment_id=self._next_payment_id,
            order_id=order_id,
            expected_amount=self.expected_amount,
        )
        self._next_payment_id += 1

        def action() -> None:
            self.current_payment = payment

        self._transition(event, PaymentState.WAITING, action)
        return payment

    def start_pay(self) -> PaymentState:
        event = "START_PAY"
        self._ensure_state(event, PaymentState.WAITING)
        self._require_current_payment(event)
        return self._transition(event, PaymentState.PROCESSING)

    def pay_success(self, amount: int) -> PaymentState:
        event = "PAY_SUCCESS"
        if self.state == PaymentState.SUCCESS:
            return self.state

        self._ensure_state(event, PaymentState.PROCESSING)
        payment = self._require_current_payment(event)

        if amount < self.expected_amount:

            def failed_action() -> None:
                payment.paid_amount = amount

            return self._transition(event, PaymentState.FAILED, failed_action)

        def success_action() -> None:
            payment.paid_amount = amount
            payment.paid_at = datetime.now()

        return self._transition(event, PaymentState.SUCCESS, success_action)

    def pay_failed(self) -> PaymentState:
        event = "PAY_FAILED"
        self._ensure_state(event, PaymentState.PROCESSING)
        self._require_current_payment(event)
        return self._transition(event, PaymentState.FAILED)

    def pay_timeout(self) -> PaymentState:
        event = "PAY_TIMEOUT"
        self._ensure_state(event, PaymentState.WAITING, PaymentState.PROCESSING)
        self._require_current_payment(event)
        return self._transition(event, PaymentState.TIMEOUT)

    def start_refund(self) -> PaymentState:
        event = "START_REFUND"
        self._ensure_state(event, PaymentState.SUCCESS)
        self._require_current_payment(event)
        return self._transition(event, PaymentState.REFUNDING)

    def refund_success(self) -> PaymentState:
        event = "REFUND_SUCCESS"
        if self.state == PaymentState.REFUNDED:
            return self.state

        self._ensure_state(event, PaymentState.REFUNDING)
        payment = self._require_current_payment(event)

        def action() -> None:
            payment.refunded_amount = payment.paid_amount
            payment.refunded_at = datetime.now()

        return self._transition(event, PaymentState.REFUNDED, action)

    def refund_failed(self) -> PaymentState:
        event = "REFUND_FAILED"
        self._ensure_state(event, PaymentState.REFUNDING)
        self._require_current_payment(event)
        return self._transition(event, PaymentState.REFUND_FAILED)

    def _transition(
        self,
        event: str,
        next_state: PaymentState,
        action: Callable[[], None] | None = None,
    ) -> PaymentState:
        old_state = self.state
        if action is not None:
            action()
        self.state = next_state
        self.trace.append((old_state, event, next_state))
        self._check_invariants()
        return self.state

    def _ensure_state(self, event: str, *allowed_states: PaymentState) -> None:
        if self.state not in allowed_states:
            allowed = ", ".join(state.value for state in allowed_states)
            raise InvalidTransition(
                f"Cannot handle {event} in {self.state.value}; "
                f"allowed states: {allowed}"
            )

    def _require_current_payment(self, event: str) -> Payment:
        if self.current_payment is None:
            raise InvalidTransition(f"Cannot handle {event}: current_payment is None")
        return self.current_payment

    def _check_invariants(self) -> None:
        if self.expected_amount <= 0:
            raise AssertionError("expected_amount must be > 0")
        if self.state == PaymentState.NONE and self.current_payment is not None:
            raise AssertionError("NONE state cannot keep current_payment")
        if self.state != PaymentState.NONE and self.current_payment is None:
            raise AssertionError(f"{self.state.value} requires current_payment")
        if self.current_payment is not None:
            payment = self.current_payment
            if payment.expected_amount != self.expected_amount:
                raise AssertionError("payment expected_amount must match machine")
            if payment.paid_amount < 0:
                raise AssertionError("paid_amount must be >= 0")
            if payment.refunded_amount < 0:
                raise AssertionError("refunded_amount must be >= 0")
        if self.state in {
            PaymentState.SUCCESS,
            PaymentState.REFUNDING,
            PaymentState.REFUNDED,
        }:
            if self.current_payment is None:
                raise AssertionError(f"{self.state.value} requires current_payment")
            if self.current_payment.paid_amount < self.expected_amount:
                raise AssertionError(f"{self.state.value} requires full payment")
        if self.state == PaymentState.REFUNDED:
            if self.current_payment is None:
                raise AssertionError("REFUNDED requires current_payment")
            if self.current_payment.refunded_amount != self.current_payment.paid_amount:
                raise AssertionError("refunded_amount must equal paid_amount")


class VendingMachine:
    """Single-product vending machine implemented with state + context.

    order_state is the main lifecycle state. stock, merchant_balance, and
    current_order are context data used by guards and actions.
    """

    def __init__(self, stock: int = 2, price: int = 5) -> None:
        if stock < 0:
            raise ValueError("stock must be >= 0")
        if price <= 0:
            raise ValueError("price must be > 0")

        self.price = price
        self.stock = stock
        self.merchant_balance = 0
        self.order_sm = OrderStateMachine()
        self.current_order: Order | None = None
        self.trace = self.order_sm.trace
        self._next_order_id = 1

    @property
    def order_state(self) -> OrderState:
        return self.order_sm.state

    @property
    def inventory_status(self) -> str:
        return "AVAILABLE" if self.stock > 0 else "SOLD_OUT"

    def place_order(self) -> Order:
        event = "PLACE_ORDER"
        if self.current_order is not None:
            raise InvalidTransition("Cannot place order: current_order already exists")
        if self.order_sm.state not in IDLE_STATES:
            allowed = ", ".join(state.value for state in IDLE_STATES)
            raise InvalidTransition(
                f"Cannot handle {event} in {self.order_sm.state.value}; "
                f"allowed states: {allowed}"
            )
        if self.stock <= 0:
            raise InvalidTransition("Cannot place order: sold out")

        order = Order(order_id=self._next_order_id, price=self.price)
        self._next_order_id += 1

        def action() -> None:
            self.stock -= 1
            self.current_order = order

        self._apply_order_transition(self.order_sm.place_order, action)
        return order

    def pay_success(self, amount: int) -> OrderState:
        event = "PAY_SUCCESS"
        self._ensure_state(event, OrderState.PENDING_PAYMENT)
        order = self._require_current_order(event)

        if amount < self.price:

            def failed_action() -> None:
                order.paid_amount = amount
                self.stock += 1
                self.current_order = None

            return self._apply_order_transition(
                self.order_sm.mark_payment_failed, failed_action
            )

        def success_action() -> None:
            order.paid_amount = amount
            order.pay_time = datetime.now()

        return self._apply_order_transition(self.order_sm.mark_paid, success_action)

    def pay_failed(self) -> OrderState:
        event = "PAY_FAILED"
        self._ensure_state(event, OrderState.PENDING_PAYMENT)
        self._require_current_order(event)
        return self._apply_order_transition(
            self.order_sm.mark_payment_failed, self._release_order
        )

    def pay_timeout(self) -> OrderState:
        event = "PAY_TIMEOUT"
        self._ensure_state(event, OrderState.PENDING_PAYMENT)
        self._require_current_order(event)
        return self._apply_order_transition(
            self.order_sm.mark_payment_timeout, self._release_order
        )

    def cancel_pay(self) -> OrderState:
        event = "CANCEL_PAY"
        self._ensure_state(event, OrderState.PENDING_PAYMENT)
        self._require_current_order(event)
        return self._apply_order_transition(
            self.order_sm.cancel_pay, self._release_order
        )

    def start_dispense(self) -> OrderState:
        event = "START_DISPENSE"
        self._ensure_state(event, OrderState.READY_TO_DISPENSE)
        order = self._require_current_order(event)
        if order.paid_amount < self.price:
            raise InvalidTransition("Cannot dispense: order is not fully paid")

        return self._apply_order_transition(self.order_sm.start_dispense)

    def dispense_ok(self) -> OrderState:
        event = "DISPENSE_OK"
        self._ensure_state(event, OrderState.DISPENSING)
        self._require_current_order(event)

        def action() -> None:
            self.merchant_balance += self.price
            self.current_order = None

        return self._apply_order_transition(self.order_sm.complete, action)

    def dispense_failed(self) -> OrderState:
        event = "DISPENSE_FAILED"
        self._ensure_state(event, OrderState.DISPENSING)
        self._require_current_order(event)

        def action() -> None:
            self.stock += 1
            self.current_order = None

        return self._apply_order_transition(self.order_sm.mark_dispense_failed, action)

    def restock(self, amount: int) -> int:
        if amount <= 0:
            raise ValueError("amount must be > 0")

        old_state = self.order_sm.state
        self.stock += amount
        self.trace.append((old_state, "RESTOCK", old_state))
        return self.stock

    def _apply_order_transition(
        self,
        transition: Callable[[], OrderState],
        action: Callable[[], None] | None = None,
    ) -> OrderState:
        if action is not None:
            action()
        state = transition()
        self._check_invariants()
        return state

    def _ensure_state(self, event: str, *allowed_states: OrderState) -> None:
        if self.order_sm.state not in allowed_states:
            allowed = ", ".join(state.value for state in allowed_states)
            raise InvalidTransition(
                f"Cannot handle {event} in {self.order_sm.state.value}; "
                f"allowed states: {allowed}"
            )

    def _require_current_order(self, event: str) -> Order:
        if self.current_order is None:
            raise InvalidTransition(f"Cannot handle {event}: current_order is None")
        return self.current_order

    def _release_order(self) -> None:
        self.stock += 1
        self.current_order = None

    def _check_invariants(self) -> None:
        if self.stock < 0:
            raise AssertionError("stock must be >= 0")
        if self.merchant_balance < 0:
            raise AssertionError("merchant_balance must be >= 0")
        if self.order_sm.state == OrderState.NONE and self.current_order is not None:
            raise AssertionError("NONE state cannot keep current_order")
        if (
            self.order_sm.state
            in {
                OrderState.PENDING_PAYMENT,
                OrderState.READY_TO_DISPENSE,
                OrderState.DISPENSING,
            }
            and self.current_order is None
        ):
            raise AssertionError(f"{self.order_sm.state.value} requires current_order")


if __name__ == "__main__":
    machine = VendingMachine()
    machine.place_order()
    machine.pay_success(amount=5)
    machine.start_dispense()
    machine.dispense_ok()
    print(machine.order_state.value)
    print(machine.stock)
    print(machine.merchant_balance)
    print(machine.trace)
