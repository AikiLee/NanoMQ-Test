# Single Product Seller State Machine Design

## 1. 目标

本练习模拟一个“只卖一种饮料的极简售货机”。

业务约束：

- 商品价格固定为 `5`
- 初始库存为 `2`
- 初始商家余额为 `0`
- 同一时间只处理一个活动订单
- 下单时预占库存
- 支付、订单、库存不是同一个状态维度

核心建模方式：

```text
OrderStateMachine      管订单生命周期
PaymentStateMachine    管支付生命周期
VendingMachine         管库存、余额、订单对象，并协调业务流程
```

不要把库存、余额、支付、订单阶段组合成一个大状态。

推荐形式：

```text
(state, event, guard(context)) -> next_state + action(context)
```

而不是：

```text
(combined_state, event) -> combined_next_state
```

## 2. Context

### VendingMachine Context

| 字段 | 含义 |
| --- | --- |
| `price` | 商品价格，默认 `5` |
| `stock` | 当前可售库存 |
| `merchant_balance` | 商家余额 |
| `current_order` | 当前活动订单 |
| `trace` | 订单状态转移记录 |

### Order Context

| 字段 | 含义 |
| --- | --- |
| `order_id` | 订单 ID |
| `price` | 订单应付价格 |
| `paid_amount` | 当前订单已支付金额 |
| `pay_time` | 支付成功时间 |

### Payment Context

| 字段 | 含义 |
| --- | --- |
| `payment_id` | 支付单 ID |
| `order_id` | 关联订单 ID |
| `expected_amount` | 应付金额 |
| `paid_amount` | 实付金额 |
| `refunded_amount` | 已退款金额 |
| `paid_at` | 支付成功时间 |
| `refunded_at` | 退款成功时间 |

### Derived State

库存状态不单独做状态机，而是从 `stock` 派生：

```text
inventory_status = AVAILABLE if stock > 0 else SOLD_OUT
```

## 3. OrderStateMachine

### Order States

| 状态 | 含义 |
| --- | --- |
| `NONE` | 当前没有订单 |
| `PENDING_PAYMENT` | 已下单，等待支付 |
| `READY_TO_DISPENSE` | 已支付，等待出货 |
| `PAYMENT_FAILED` | 支付失败，订单终止 |
| `PAYMENT_TIMEOUT` | 支付超时，订单终止 |
| `CANCELLED` | 用户取消，订单终止 |
| `DISPENSING` | 正在出货 |
| `COMPLETED` | 出货成功，订单完成 |
| `DISPENSE_FAILED` | 出货失败，需要退款或人工处理 |

### Idle States

这些状态表示当前没有活动订单，可以开启新订单：

```text
NONE
PAYMENT_FAILED
PAYMENT_TIMEOUT
CANCELLED
COMPLETED
DISPENSE_FAILED
```

### Order Events

| 事件 | 来源 | 含义 |
| --- | --- | --- |
| `PLACE_ORDER` | 用户 | 下单 |
| `PAY_SUCCESS` | 支付结果 | 支付成功 |
| `PAY_FAILED` | 支付结果 | 支付失败 |
| `PAY_TIMEOUT` | 支付结果 | 支付超时 |
| `CANCEL_PAY` | 用户 | 支付前取消 |
| `START_DISPENSE` | 系统 | 开始出货 |
| `DISPENSE_OK` | 设备 | 出货成功 |
| `DISPENSE_FAILED` | 设备 | 出货失败 |
| `RESTOCK` | 管理员 | 补货 |

### Order Transitions

| 事件 | 当前状态 | Guard | 目标状态 | Action |
| --- | --- | --- | --- | --- |
| `PLACE_ORDER` | idle states | `stock > 0` and `current_order is None` | `PENDING_PAYMENT` | `stock -= 1`, `current_order = order` |
| `PLACE_ORDER` | idle states | `stock <= 0` | 原状态不变 | 抛出 `InvalidTransition` |
| `PLACE_ORDER` | 非 idle states | - | 原状态不变 | 抛出 `InvalidTransition` |
| `PAY_SUCCESS` | `PENDING_PAYMENT` | `amount >= price` | `READY_TO_DISPENSE` | `paid_amount = amount`, `pay_time = now` |
| `PAY_SUCCESS` | `PENDING_PAYMENT` | `amount < price` | `PAYMENT_FAILED` | `stock += 1`, `current_order = None` |
| `PAY_FAILED` | `PENDING_PAYMENT` | - | `PAYMENT_FAILED` | `stock += 1`, `current_order = None` |
| `PAY_TIMEOUT` | `PENDING_PAYMENT` | - | `PAYMENT_TIMEOUT` | `stock += 1`, `current_order = None` |
| `CANCEL_PAY` | `PENDING_PAYMENT` | - | `CANCELLED` | `stock += 1`, `current_order = None` |
| `START_DISPENSE` | `READY_TO_DISPENSE` | `paid_amount >= price` | `DISPENSING` | 无 |
| `DISPENSE_OK` | `DISPENSING` | - | `COMPLETED` | `merchant_balance += price`, `current_order = None` |
| `DISPENSE_FAILED` | `DISPENSING` | - | `DISPENSE_FAILED` | `stock += 1`, `current_order = None` |
| `RESTOCK` | any | `amount > 0` | 原状态不变 | `stock += amount` |

### Order Invariants

```text
stock >= 0
merchant_balance >= 0
OrderState == NONE 时 current_order 必须为 None
OrderState in {PENDING_PAYMENT, READY_TO_DISPENSE, DISPENSING} 时 current_order 必须存在
进入 PENDING_PAYMENT 时必须已经预占 1 个库存
PAYMENT_FAILED / PAYMENT_TIMEOUT / CANCELLED 必须释放预占库存
COMPLETED 只能由 DISPENSING + DISPENSE_OK 进入
DISPENSE_OK 才能增加 merchant_balance
```

## 4. PaymentStateMachine

### Payment States

| 状态 | 含义 |
| --- | --- |
| `NONE` | 还没有支付单 |
| `WAITING` | 已创建支付单，等待用户支付 |
| `PROCESSING` | 支付处理中 |
| `SUCCESS` | 支付成功 |
| `FAILED` | 支付失败 |
| `TIMEOUT` | 支付超时 |
| `REFUNDING` | 退款中 |
| `REFUNDED` | 已退款 |
| `REFUND_FAILED` | 退款失败，需要人工处理 |

### Payment Events

| 事件 | 来源 | 含义 |
| --- | --- | --- |
| `CREATE_PAYMENT` | 业务系统 | 创建支付单 |
| `START_PAY` | 用户或系统 | 发起支付 |
| `PAY_SUCCESS` | 第三方支付回调 | 支付成功 |
| `PAY_FAILED` | 第三方支付回调 | 支付失败 |
| `PAY_TIMEOUT` | 定时器或支付系统 | 支付超时 |
| `START_REFUND` | 业务系统 | 发起退款 |
| `REFUND_SUCCESS` | 第三方支付回调 | 退款成功 |
| `REFUND_FAILED` | 第三方支付回调 | 退款失败 |

### Payment Transitions

| 事件 | 当前状态 | Guard | 目标状态 | Action |
| --- | --- | --- | --- | --- |
| `CREATE_PAYMENT` | `NONE` | `order_id > 0` | `WAITING` | `current_payment = payment` |
| `START_PAY` | `WAITING` | `current_payment exists` | `PROCESSING` | 无 |
| `PAY_SUCCESS` | `PROCESSING` | `amount >= expected_amount` | `SUCCESS` | `paid_amount = amount`, `paid_at = now` |
| `PAY_SUCCESS` | `PROCESSING` | `amount < expected_amount` | `FAILED` | `paid_amount = amount` |
| `PAY_SUCCESS` | `SUCCESS` | duplicate callback | `SUCCESS` | 幂等，不追加 trace |
| `PAY_FAILED` | `PROCESSING` | - | `FAILED` | 无 |
| `PAY_TIMEOUT` | `WAITING` or `PROCESSING` | - | `TIMEOUT` | 无 |
| `START_REFUND` | `SUCCESS` | `current_payment exists` | `REFUNDING` | 无 |
| `REFUND_SUCCESS` | `REFUNDING` | - | `REFUNDED` | `refunded_amount = paid_amount`, `refunded_at = now` |
| `REFUND_SUCCESS` | `REFUNDED` | duplicate callback | `REFUNDED` | 幂等，不追加 trace |
| `REFUND_FAILED` | `REFUNDING` | - | `REFUND_FAILED` | 无 |

### Payment Invariants

```text
expected_amount > 0
PaymentState == NONE 时 current_payment 必须为 None
PaymentState != NONE 时 current_payment 必须存在
paid_amount >= 0
refunded_amount >= 0
SUCCESS / REFUNDING / REFUNDED 必须满足 paid_amount >= expected_amount
REFUNDED 时 refunded_amount 必须等于 paid_amount
```

## 5. 两个状态机如何协作

单个状态机只负责自己的合法转移。

```text
OrderStateMachine:
只保证订单状态合法

PaymentStateMachine:
只保证支付状态合法

VendingMachine / Service:
保证订单状态和支付状态组合起来是业务正确的
```

### 推荐协作方式

不要让 `PaymentStateMachine` 直接修改 `OrderStateMachine`。

推荐：

```text
1. VendingMachine 调用 PaymentStateMachine
2. PaymentStateMachine 完成自己的状态转移
3. VendingMachine 根据 PaymentState 的结果决定是否推进 OrderState
```

示例：

```text
on_pay_success(amount):
  PaymentStateMachine: PROCESSING -> SUCCESS
  if payment_state == SUCCESS:
    OrderStateMachine: PENDING_PAYMENT -> READY_TO_DISPENSE
```

### Cross-Machine Invariants

```text
OrderState == READY_TO_DISPENSE 时 PaymentState 必须是 SUCCESS
OrderState == DISPENSING 时 PaymentState 必须是 SUCCESS
OrderState == COMPLETED 时 PaymentState 必须是 SUCCESS
PaymentState == REFUNDED 时 OrderState 不能是 COMPLETED
PaymentState == PROCESSING 时 OrderState 不能进入 DISPENSING
OrderState == CANCELLED 且 PaymentState == SUCCESS 时，必须发起 START_REFUND
```

## 6. 当前实现状态

当前代码已经实现：

- `OrderState`
- `PaymentState`
- `Order`
- `Payment`
- `VendingMachine`
- `PaymentStateMachine`
- 独立订单流程测试
- 独立支付流程测试

当前代码还没有完成：

- 把 `PaymentStateMachine` 编排进 `VendingMachine`
- 把支付成功结果驱动订单进入 `READY_TO_DISPENSE`
- 把取消订单后的退款流程和订单状态联动
- 把 cross-machine invariants 写进协调层

## 7. 最小验证点

订单状态机验证：

```text
正常购买：PLACE_ORDER -> PAY_SUCCESS -> START_DISPENSE -> DISPENSE_OK
取消支付：PLACE_ORDER -> CANCEL_PAY
不足额支付：PLACE_ORDER -> PAY_SUCCESS(amount < price)
非法转移：NONE 收到 PAY_SUCCESS
```

支付状态机验证：

```text
正常支付：CREATE_PAYMENT -> START_PAY -> PAY_SUCCESS
支付超时：CREATE_PAYMENT -> PAY_TIMEOUT
退款：CREATE_PAYMENT -> START_PAY -> PAY_SUCCESS -> START_REFUND -> REFUND_SUCCESS
幂等：SUCCESS 再收到 PAY_SUCCESS 不重复追加 trace
非法转移：NONE 收到 PAY_SUCCESS
```
