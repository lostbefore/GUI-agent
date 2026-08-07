from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class ProgressRecorder:
    """进度记录器"""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def record(self, stage: str, **details: Any) -> dict[str, Any]:
        event = {
            "time": datetime.now().astimezone().isoformat(timespec="seconds"),
            "stage": stage,
            **details,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        return event


def read_latest_progress(path: str | Path) -> dict[str, Any] | None:
    source = Path(path)
    if not source.is_file():
        return None
    lines = source.read_text(encoding="utf-8").splitlines()
    for line in reversed(lines):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def format_progress(event: dict[str, Any] | None) -> str:
    if not event:
        return "GUI Agent\n正在等待运行"
    stage = str(event.get("stage", ""))
    index = event.get("index")
    action = event.get("action")
    status = event.get("status")
    message = event.get("message")
    labels = {
        "starting": "正在启动",
        "observing": "正在截图和识别",
        "observed": "屏幕识别完成",
        "planning": "正在生成任务计划",
        "planned": "任务计划已生成",
        "deciding": "正在生成下一步动作",
        "decision_ready": "动作决策已生成",
        "action_finished": "桌面动作执行完成",
        "finished": "任务运行结束",
        "error": "任务运行出错",
        "interrupted": "任务已停止",
    }
    parts = ["GUI Agent", labels.get(stage, stage or "运行中")]
    if index is not None:
        parts[-1] += f"  第 {index} 步"
    if action:
        parts.append(f"动作  {action}")
    if status:
        parts.append(f"状态  {status}")
    if message:
        parts.append(str(message))
    return "\n".join(parts)
