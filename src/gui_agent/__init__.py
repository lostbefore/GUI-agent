"""桌面感知与控制"""

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
    # 首次导入缓存
    globals()[name] = value
    return value
