class InvalidTransition(Exception):
    pass


class StateMachine:
    def __init__(self, initial_state, transitions) -> None:
        self.state = initial_state
        self.transitions = transitions
        self.trace = []

    def dispatch(self, event) -> str:
        key = (self.state, event)

        if key not in self.transitions:
            raise InvalidTransition(f"Cannot handle {event} in {self.state}")

        old_state = self.state
        new_state = self.transitions[key]

        self.state = new_state
        self.trace.append((old_state, event, new_state))

        return self.state

    def after_dispatched_state(self, event):
        ans = self.dispatch(event)
        if type(ans) == tuple:
            print(f"all state are: {self.state}")
        else:
            print(f"door's current state: {self.state}")


if __name__ == "__main__":
    transitions: dict[tuple[str, str], str] = {
        ("CLOSED", "OPEN_DOOR"): "OPEN",
        ("OPEN", "CLOSE_DOOR"): "CLOSED",
    }

    door = StateMachine("OPEN", transitions)
    door.after_dispatched_state("CLOSE_DOOR")
