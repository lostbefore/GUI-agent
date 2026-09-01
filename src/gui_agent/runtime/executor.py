from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from gui_agent.agent import AgentDecision
from gui_agent.control import InputController
from gui_agent.coordinates import CoordinateMapper, Point


@dataclass(slots=True)
class ActionResult:
    action: str
    success: bool
    message: str
    parameters: dict[str, Any] = field(default_factory=dict)


class ActionExecutor:
    """动作执行器"""

    def __init__(
        self,
        controller: InputController,
        *,
        sleeper: Callable[[float], None] = time.sleep,
        max_wait: float = 10.0,
    ) -> None:
        if max_wait < 0:
            raise ValueError("max_wait must not be negative")
        self.controller = controller
        self.sleeper = sleeper
        self.max_wait = max_wait

    @staticmethod
    def _point(value: Any, mapper: CoordinateMapper) -> tuple[int, int]:
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) != 2:
            raise ValueError("point must contain x and y")
        # 映射截图坐标
        point = Point(round(float(value[0])), round(float(value[1])))
        if not (0 <= point.x < mapper.image_width and 0 <= point.y < mapper.image_height):
            raise ValueError("point is outside the screenshot")
        mapped = mapper.image_to_screen(point)
        return mapped.x, mapped.y

    @classmethod
    def _xy(cls, parameters: dict[str, Any], mapper: CoordinateMapper) -> tuple[int, int]:
        if "x" not in parameters or "y" not in parameters:
            raise ValueError("action requires x and y")
        return cls._point((parameters["x"], parameters["y"]), mapper)

    @staticmethod
    def _text(parameters: dict[str, Any], key: str) -> str:
        value = parameters.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(f"action requires {key}")
        return value

    def execute(self, decision: AgentDecision, mapper: CoordinateMapper) -> ActionResult:
        parameters = dict(decision.parameters or {})
        action = decision.action
        try:
            if action in {"click", "double_click", "context_open"}:
                x, y = self._xy(parameters, mapper)
                if action == "context_open":
                    if any(key in parameters for key in ("key", "keys", "text")):
                        raise ValueError("context_open does not accept keyboard parameters")
                    self.controller.click(x, y, button="right", clicks=1)
                    self.controller.press("enter", presses=1)
                    return ActionResult(action, True, "右键打开完成", parameters)
                self.controller.click(
                    x,
                    y,
                    button=str(parameters.get("button", "left")),
                    clicks=2 if action == "double_click" else 1,
                )
            elif action == "type":
                text = self._text(parameters, "text")
                self.controller.write(text, interval=float(parameters.get("interval", 0.03)))
            elif action == "press":
                key = str(parameters.get("key") or parameters.get("text") or "")
                if not key:
                    raise ValueError("action requires key")
                self.controller.press(key, presses=int(parameters.get("presses", 1)))
            elif action == "hotkey":
                keys = parameters.get("keys")
                if not isinstance(keys, list) or not keys:
                    raise ValueError("action requires keys")
                self.controller.hotkey(*(str(key) for key in keys))
            elif action == "maximize_window":
                maximized = self.controller.maximize_active_window()
                message = "窗口已最大化" if maximized else "窗口已全屏"
                return ActionResult(action, True, message, parameters)
            elif action == "scroll":
                amount = int(parameters.get("amount", 0))
                if "x" in parameters or "y" in parameters:
                    x, y = self._xy(parameters, mapper)
                    self.controller.scroll(amount, x=x, y=y)
                else:
                    self.controller.scroll(amount)
            elif action == "drag":
                start = self._point(parameters.get("start"), mapper)
                end = self._point(parameters.get("end"), mapper)
                self.controller.drag(
                    start,
                    end,
                    duration=float(parameters.get("duration", 0.5)),
                    button=str(parameters.get("button", "left")),
                )
            elif action == "wait":
                duration = float(parameters.get("duration", 1.0))
                if not 0 <= duration <= self.max_wait:
                    raise ValueError("wait duration is outside the allowed range")
                self.sleeper(duration)
            elif action == "finish":
                return ActionResult(action, True, "任务完成", parameters)
            else:
                raise ValueError(f"unsupported action: {action}")
        except (OSError, RuntimeError, TypeError, ValueError) as error:
            return ActionResult(action, False, str(error), parameters)
        except Exception as error:
            if type(error).__module__.startswith("pyautogui"):
                return ActionResult(action, False, str(error), parameters)
            raise
        return ActionResult(action, True, "执行成功", parameters)
