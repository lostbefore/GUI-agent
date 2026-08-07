"""桌面执行系统"""

from .executor import ActionExecutor, ActionResult
from .orchestrator import ExecutionEvent, ExecutionReport, GUIAgentRuntime, Observation
from .safety import ActionPolicy, UnsafeActionError

__all__ = [
    "ActionExecutor",
    "ActionPolicy",
    "ActionResult",
    "ExecutionEvent",
    "ExecutionReport",
    "GUIAgentRuntime",
    "Observation",
    "UnsafeActionError",
]
