from gui_agent.control import InputController


class FakeBackend:
    PAUSE = None
    FAILSAFE = None

    def __init__(self):
        self.calls = []

    def size(self):
        return (800, 600)

    def click(self, **kwargs):
        self.calls.append(("click", kwargs))

    def moveTo(self, *args, **kwargs):
        self.calls.append(("move", args, kwargs))

    def dragTo(self, *args, **kwargs):
        self.calls.append(("drag", args, kwargs))

    def scroll(self, amount):
        self.calls.append(("scroll", amount))


def test_click_and_drag() -> None:
    backend = FakeBackend()
    controller = InputController(backend=backend)
    controller.click(10, 20)
    controller.drag((10, 20), (100, 200))
    assert backend.calls[0][0] == "click"
    assert backend.calls[-1][0] == "drag"
