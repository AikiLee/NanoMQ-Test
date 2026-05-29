"""

state:
DRAFT      草稿，刚创建，还没提交
SUBMITTED  已提交，等待支付
PAID       已支付，流程结束
CANCELLED  已取消，流程结束

event:
SUBMIT     提交订单
PAY        支付订单
CANCEL     取消订单

transition:
当前状态    触发事件    目标状态    合法性
DRAFT      SUBMIT    SUBMITTED     1
SUBMITTED  PAY       PAID          1
SUBMITTED  CANCEL    CANCELLED     1
DRAFT       CANCEL     CANCELLED   1
...其他组合都是非法的



"""

from mini_state_mechine import InvalidTransition, StateMachine


class OrderMachine(StateMachine):

    def __init__(self):
        transitions: dict[tuple[str, str], str] = {
            ("DRAFT", "SUBMIT"): "SUBMITTED",
            ("SUBMITTED", "PAY"): "PAID",
            ("SUBMITTED", "CANCEL"): "CANCELLED",
            ("DRAFT", "CANCEL"): "CANCELLED",
        }
        initial_state = "DRAFT"
        super().__init__(initial_state, transitions)

    def after_dispatched_state(self, event):
        ans: str = super().dispatch(event)

        if type(ans) == tuple:
            print(f"all state are: {self.state}")
        else:
            print(f"order's current state: {self.state}")


order = OrderMachine()

order.after_dispatched_state("SUBMIT")
