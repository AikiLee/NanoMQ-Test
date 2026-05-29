import pytest

from docs.train_plan.task01.single_product_seller import (
    InvalidTransition,
    OrderStateMachine,
    OrderState,
    PaymentState,
    PaymentStateMachine,
    VendingMachine,
)


def test_successful_purchase_reserves_stock_and_adds_merchant_balance():
    machine = VendingMachine(stock=2)

    order = machine.place_order()
    assert machine.order_state == OrderState.PENDING_PAYMENT
    assert machine.stock == 1
    assert machine.current_order == order
    assert machine.inventory_status == "AVAILABLE"

    machine.pay_success(amount=5)
    machine.start_dispense()
    machine.dispense_ok()

    assert machine.order_state == OrderState.COMPLETED
    assert machine.stock == 1
    assert machine.merchant_balance == 5
    assert machine.current_order is None


def test_order_state_machine_tracks_order_lifecycle():
    order_sm = OrderStateMachine()

    order_sm.place_order()
    order_sm.mark_paid()
    order_sm.start_dispense()
    order_sm.complete()

    assert order_sm.state == OrderState.COMPLETED
    assert order_sm.trace == [
        (OrderState.NONE, "PLACE_ORDER", OrderState.PENDING_PAYMENT),
        (OrderState.PENDING_PAYMENT, "MARK_PAID", OrderState.READY_TO_DISPENSE),
        (OrderState.READY_TO_DISPENSE, "START_DISPENSE", OrderState.DISPENSING),
        (OrderState.DISPENSING, "DISPENSE_OK", OrderState.COMPLETED),
    ]


def test_cancel_pay_releases_reserved_stock():
    machine = VendingMachine(stock=2)

    machine.place_order()
    machine.cancel_pay()

    assert machine.order_state == OrderState.CANCELLED
    assert machine.stock == 2
    assert machine.current_order is None


def test_insufficient_payment_fails_order_and_releases_stock():
    machine = VendingMachine(stock=2)

    machine.place_order()
    machine.pay_success(amount=3)

    assert machine.order_state == OrderState.PAYMENT_FAILED
    assert machine.stock == 2
    assert machine.merchant_balance == 0
    assert machine.current_order is None


def test_invalid_transition_fails_fast():
    machine = VendingMachine(stock=2)

    with pytest.raises(InvalidTransition):
        machine.pay_success(amount=5)


def test_restock_is_allowed_while_waiting_for_payment():
    machine = VendingMachine(stock=1)

    machine.place_order()
    machine.restock(amount=2)

    assert machine.order_state == OrderState.PENDING_PAYMENT
    assert machine.stock == 2


def test_machine_can_start_next_order_after_completed_order():
    machine = VendingMachine(stock=2)

    machine.place_order()
    machine.pay_success(amount=5)
    machine.start_dispense()
    machine.dispense_ok()

    next_order = machine.place_order()

    assert machine.order_state == OrderState.PENDING_PAYMENT
    assert machine.stock == 0
    assert machine.current_order == next_order
    assert next_order.order_id == 2


def test_payment_can_move_from_waiting_to_success():
    payment_sm = PaymentStateMachine(expected_amount=5)

    payment = payment_sm.create_payment(order_id=1)
    payment_sm.start_pay()
    payment_sm.pay_success(amount=5)

    assert payment_sm.state == PaymentState.SUCCESS
    assert payment_sm.current_payment == payment
    assert payment.paid_amount == 5
    assert payment.paid_at is not None
    assert payment_sm.trace == [
        (PaymentState.NONE, "CREATE_PAYMENT", PaymentState.WAITING),
        (PaymentState.WAITING, "START_PAY", PaymentState.PROCESSING),
        (PaymentState.PROCESSING, "PAY_SUCCESS", PaymentState.SUCCESS),
    ]


def test_payment_timeout_can_happen_before_processing():
    payment_sm = PaymentStateMachine(expected_amount=5)

    payment_sm.create_payment(order_id=1)
    payment_sm.pay_timeout()

    assert payment_sm.state == PaymentState.TIMEOUT


def test_successful_payment_can_be_refunded():
    payment_sm = PaymentStateMachine(expected_amount=5)

    payment_sm.create_payment(order_id=1)
    payment_sm.start_pay()
    payment_sm.pay_success(amount=5)
    payment_sm.start_refund()
    payment_sm.refund_success()

    assert payment_sm.state == PaymentState.REFUNDED
    assert payment_sm.current_payment.refunded_amount == 5  # type: ignore
    assert payment_sm.current_payment.refunded_at is not None  # type: ignore


def test_duplicate_pay_success_callback_is_idempotent():
    payment_sm = PaymentStateMachine(expected_amount=5)

    payment_sm.create_payment(order_id=1)
    payment_sm.start_pay()
    payment_sm.pay_success(amount=5)
    payment_sm.pay_success(amount=5)

    assert payment_sm.state == PaymentState.SUCCESS
    assert payment_sm.current_payment.paid_amount == 5  # type: ignore
    assert (
        payment_sm.trace.count(
            (PaymentState.PROCESSING, "PAY_SUCCESS", PaymentState.SUCCESS)
        )
        == 1
    )


def test_payment_fails_fast_on_invalid_transition():
    payment_sm = PaymentStateMachine(expected_amount=5)

    with pytest.raises(InvalidTransition):
        payment_sm.pay_success(amount=5)
