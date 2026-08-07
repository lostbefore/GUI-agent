"""桌面智能体组件"""

from importlib import import_module

__all__ = [
    "ActionExecutor",
    "ActionPolicy",
    "Box",
    "CoordinateMapper",
    "DesktopPerception",
    "ExecutionReport",
    "GUIAgentRuntime",
    "InputController",
    "Point",
    "ScreenCapture",
    "ScreenFrame",
    "UIElement",
]

_EXPORTS = {
    "ActionExecutor": (".runtime", "ActionExecutor"),
    "ActionPolicy": (".runtime", "ActionPolicy"),
    "Box": (".coordinates", "Box"),
    "CoordinateMapper": (".coordinates", "CoordinateMapper"),
    "Point": (".coordinates", "Point"),
    "InputController": (".control", "InputController"),
    "DesktopPerception": (".perception", "DesktopPerception"),
    "UIElement": (".perception", "UIElement"),
    "ScreenCapture": (".screen", "ScreenCapture"),
    "ScreenFrame": (".screen", "ScreenFrame"),
    "ExecutionReport": (".runtime", "ExecutionReport"),
    "GUIAgentRuntime": (".runtime", "GUIAgentRuntime"),
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
