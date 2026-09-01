import pytest

from gui_agent.control import InputController
from gui_agent.coordinates import Box


class FakeBackend:
    PAUSE = None
    FAILSAFE = None

    def __init__(self):
        self.calls = []

    def size(self):
        return (800, 600)

    def keyDown(self, key):
        self.calls.append(("keyDown", key))

    def keyUp(self, key):
        self.calls.append(("keyUp", key))

    def click(self, **kwargs):
        self.calls.append(("click", kwargs))

    def moveTo(self, *args, **kwargs):
        self.calls.append(("move", args, kwargs))

    def dragTo(self, *args, **kwargs):
        self.calls.append(("drag", args, kwargs))

    def scroll(self, amount):
        self.calls.append(("scroll", amount))

    def write(self, *args, **kwargs):
        self.calls.append(("write", args, kwargs))

    def press(self, *args, **kwargs):
        self.calls.append(("press", args, kwargs))

    def hotkey(self, *args):
        self.calls.append(("hotkey", args))


class FakeClipboard:
    def __init__(self):
        self.text = ""

    def copy(self, text):
        self.text = text


def test_click_and_drag() -> None:
    backend = FakeBackend()
    controller = InputController(backend=backend)
    controller.click(10, 20)
    controller.drag((10, 20), (100, 200))
    assert backend.calls[0][0] == "click"
    assert backend.calls[-1][0] == "drag"


def test_controller_configures_backend_and_click_box() -> None:
    backend = FakeBackend()
    controller = InputController(backend=backend, pause=0.25, failsafe=False)
    controller.click_box(Box(10, 20, 30, 40), button="right")
    assert backend.PAUSE == 0.25
    assert backend.FAILSAFE is False
    assert backend.calls[-1] == (
        "click",
        {"x": 20, "y": 30, "button": "right", "clicks": 1},
    )


def test_keyboard_and_move_operations() -> None:
    backend = FakeBackend()
    controller = InputController(backend=backend)
    controller.move(50, 60, duration=0.4)
    controller.write("hello", interval=0.1)
    controller.press("enter", presses=2)
    controller.hotkey("ctrl", "a")
    assert [call[0] for call in backend.calls] == ["move", "write", "press", "hotkey"]


def test_unicode_input_uses_clipboard() -> None:
    backend = FakeBackend()
    clipboard = FakeClipboard()
    controller = InputController(backend=backend, clipboard=clipboard)
    controller.write("中文测试")
    assert clipboard.text == "中文测试"
    assert backend.calls == [("hotkey", ("ctrl", "v"))]


def test_unicode_input_reports_clipboard_failure() -> None:
    class BrokenClipboard:
        @staticmethod
        def copy(text):
            raise OSError("clipboard unavailable")

    controller = InputController(backend=FakeBackend(), clipboard=BrokenClipboard())
    with pytest.raises(RuntimeError, match="剪贴板"):
        controller.write("中文")


def test_scroll_with_and_without_position() -> None:
    backend = FakeBackend()
    controller = InputController(backend=backend)
    controller.scroll(-3)
    controller.scroll(2, x=100, y=200)
    assert backend.calls == [
        ("scroll", -3),
        ("move", (100, 200), {}),
        ("scroll", 2),
    ]


def test_scroll_requires_both_coordinates() -> None:
    controller = InputController(backend=FakeBackend())
    with pytest.raises(ValueError, match="provided together"):
        controller.scroll(1, x=10)


@pytest.mark.parametrize("point", [(-1, 0), (0, -1), (800, 10), (10, 600)])
def test_out_of_bounds_operations_are_rejected(point) -> None:
    controller = InputController(backend=FakeBackend())
    with pytest.raises(ValueError, match="outside"):
        controller.click(*point)


def test_default_backend_is_loaded_lazily(monkeypatch) -> None:
    import pyautogui

    monkeypatch.setattr(pyautogui, "PAUSE", 0)
    monkeypatch.setattr(pyautogui, "FAILSAFE", False)
    controller = InputController(pause=0.2, failsafe=True)
    assert controller.backend is pyautogui
    assert pyautogui.PAUSE == 0.2
    assert pyautogui.FAILSAFE is True


def test_open_box_in_new_tab_uses_foreground_tab_modifier() -> None:
    backend = FakeBackend()
    controller = InputController(backend=backend)
    controller.open_box_in_new_tab(Box(10, 20, 30, 40))
    assert backend.calls == [
        ("keyDown", "ctrl"),
        ("keyDown", "shift"),
        ("click", {"x": 20, "y": 30, "button": "left", "clicks": 1}),
        ("keyUp", "shift"),
        ("keyUp", "ctrl"),
    ]


def test_maximize_active_window_only_when_needed() -> None:
    class Window:
        def __init__(self, left, top, width, height, title="New tab - Microsoft Edge"):
            self.left = left
            self.top = top
            self.width = width
            self.height = height
            self.title = title
            self.isMaximized = False
            self.maximized = 0

        def maximize(self):
            self.maximized += 1

    class Provider:
        def __init__(self, window):
            self.window = window

        def getActiveWindow(self):
            return self.window

    backend = FakeBackend()
    full = Window(0, 0, 800, 600)
    controller = InputController(backend=backend, window_provider=Provider(full))
    assert controller.maximize_active_window() is False
    assert full.maximized == 0

    partial = Window(100, 100, 600, 400)
    controller = InputController(backend=backend, window_provider=Provider(partial))
    assert controller.maximize_active_window() is True
    assert partial.maximized == 1
