"""Desktop perception and control building blocks.

Public objects are imported lazily so lightweight coordinate/control use does not
load OCR and computer-vision runtimes.
"""

from importlib import import_module

__all__ = [
    "Box",
    "CoordinateMapper",
    "DesktopPerception",
    "InputController",
    "Point",
    "ScreenCapture",
    "ScreenFrame",
    "UIElement",
]

_EXPORTS = {
    "Box": (".coordinates", "Box"),
    "CoordinateMapper": (".coordinates", "CoordinateMapper"),
    "Point": (".coordinates", "Point"),
    "InputController": (".control", "InputController"),
    "DesktopPerception": (".perception", "DesktopPerception"),
    "UIElement": (".perception", "UIElement"),
    "ScreenCapture": (".screen", "ScreenCapture"),
    "ScreenFrame": (".screen", "ScreenFrame"),
}


def __getattr__(name: str):
    try:
        module_name, attribute = _EXPORTS[name]
    except KeyError as error:
        raise AttributeError(name) from error
    value = getattr(import_module(module_name, __name__), attribute)
    globals()[name] = value
    return value
