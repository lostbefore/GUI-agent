import pytest

import gui_agent


def test_public_exports_are_loaded_lazily() -> None:
    assert gui_agent.Box.__name__ == "Box"
    assert gui_agent.InputController.__name__ == "InputController"
    assert gui_agent.ScreenFrame.__name__ == "ScreenFrame"
    assert gui_agent.UIElement.__name__ == "UIElement"


def test_unknown_public_attribute_raises() -> None:
    with pytest.raises(AttributeError):
        _ = gui_agent.DoesNotExist
