from __future__ import annotations

import argparse
import json
import sys
import time
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from gui_agent.agent import AgentDecision, Plan, PlanStep
from gui_agent.control import InputController
from gui_agent.perception import DesktopPerception

from .executor import ActionExecutor
from .orchestrator import GUIAgentRuntime
from .safety import ActionPolicy

TASK_NAMES = (
    "open-browser",
    "search-content",
    "open-file",
    "send-message",
    "close-app",
)


@dataclass(frozen=True, slots=True)
class AcceptanceTask:
    """验收任务"""

    name: str
    title: str
    goal: str
    preparation: str
    decisions: tuple[AgentDecision, ...]


class ScriptedAgent:
    """固定动作代理"""

    def __init__(self, task: AcceptanceTask) -> None:
        self.task = task
        self.decisions = deque(task.decisions)

    def plan(self, goal: str, screenshot=None, screen_context: str = "") -> Plan:
        steps = [PlanStep(1, self.task.title)]
        return Plan(goal, f"执行真实桌面验收 {self.task.title}", steps)

    def decide(
        self,
        goal: str,
        plan: Plan,
        screenshot,
        *,
        screen_context: str = "",
        history=(),
    ) -> AgentDecision:
        if not self.decisions:
            return AgentDecision("finish", "固定动作已完成")
        return self.decisions.popleft()


def _finish() -> AgentDecision:
    return AgentDecision("finish", "验收动作完成")


def build_task(
    name: str,
    *,
    browser: str = "msedge",
    query: str = "GUI Agent",
    file_path: str | Path = "README.md",
    message: str = "GUI Agent 测试消息",
) -> AcceptanceTask:
    if name == "open-browser":
        return AcceptanceTask(
            name,
            "打开浏览器",
            "通过 Windows 图形界面打开浏览器",
            "保存工作并显示 Windows 桌面",
            (
                AgentDecision("hotkey", parameters={"keys": ["win", "r"]}),
                AgentDecision("type", parameters={"text": browser}),
                AgentDecision("press", parameters={"key": "enter", "step_id": 1}),
                AgentDecision("wait", parameters={"duration": 2.0}),
                _finish(),
            ),
        )
    if name == "search-content":
        return AcceptanceTask(
            name,
            "搜索指定内容",
            f"在当前浏览器搜索 {query}",
            "打开浏览器并使窗口保持前台",
            (
                AgentDecision("hotkey", parameters={"keys": ["ctrl", "l"]}),
                AgentDecision("type", parameters={"text": query}),
                AgentDecision("press", parameters={"key": "enter", "step_id": 1}),
                AgentDecision("wait", parameters={"duration": 2.0}),
                _finish(),
            ),
        )
    if name == "open-file":
        path = Path(file_path).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"测试文件不存在: {path}")
        return AcceptanceTask(
            name,
            "打开指定文件",
            f"通过 Windows 图形界面打开 {path}",
            "保存工作并显示 Windows 桌面",
            (
                AgentDecision("hotkey", parameters={"keys": ["win", "r"]}),
                AgentDecision("type", parameters={"text": str(path)}),
                AgentDecision("press", parameters={"key": "enter", "step_id": 1}),
                AgentDecision("wait", parameters={"duration": 2.0}),
                _finish(),
            ),
        )
    if name == "send-message":
        return AcceptanceTask(
            name,
            "发送消息",
            "向当前测试会话发送指定消息",
            "打开自己的测试会话并将输入框置于可输入状态",
            (
                AgentDecision("type", parameters={"text": message}),
                AgentDecision("press", parameters={"key": "enter", "step_id": 1}),
                AgentDecision("wait", parameters={"duration": 1.0}),
                _finish(),
            ),
        )
    if name == "close-app":
        return AcceptanceTask(
            name,
            "关闭应用",
            "关闭当前测试应用",
            "打开无未保存内容的测试应用并使其保持前台",
            (
                AgentDecision("hotkey", parameters={"keys": ["alt", "f4"], "step_id": 1}),
                AgentDecision("wait", parameters={"duration": 1.0}),
                _finish(),
            ),
        )
    raise ValueError(f"不支持的验收任务: {name}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="第四周真实桌面验收")
    parser.add_argument("--task", required=True, choices=TASK_NAMES, help="验收任务")
    parser.add_argument("--execute", action="store_true", help="执行真实动作")
    parser.add_argument("--yes", action="store_true", help="跳过一般确认")
    parser.add_argument("--confirm-send", action="store_true", help="确认发送测试消息")
    parser.add_argument("--start-delay", type=float, default=5.0, help="切换窗口等待秒数")
    parser.add_argument("--artifact-dir", default="artifacts/acceptance", help="记录根目录")
    parser.add_argument("--browser", default="msedge", help="浏览器启动名")
    parser.add_argument("--query", default="GUI Agent", help="搜索内容")
    parser.add_argument("--file", default="README.md", help="测试文件")
    parser.add_argument("--message", default="GUI Agent 测试消息", help="测试消息")
    parser.add_argument("--analyze-screen", action="store_true", help="执行 OCR 和区域识别")
    parser.add_argument("--ocr-gpu", action="store_true", help="启用 OCR GPU")
    return parser


def _task_payload(task: AcceptanceTask) -> dict[str, Any]:
    return {
        "task": task.name,
        "title": task.title,
        "goal": task.goal,
        "preparation": task.preparation,
        "actions": [asdict(decision) for decision in task.decisions],
    }


def _confirm(task: AcceptanceTask, *, yes: bool) -> bool:
    if yes:
        return True
    answer = input(f"即将执行真实任务“{task.title}” 输入 yes 继续：").strip().lower()
    return answer == "yes"


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        task = build_task(
            args.task,
            browser=args.browser,
            query=args.query,
            file_path=args.file,
            message=args.message,
        )
        policy = ActionPolicy()
        for decision in task.decisions:
            policy.validate(decision)
        if not args.execute:
            print(json.dumps({"mode": "preview", **_task_payload(task)}, ensure_ascii=False, indent=2))
            return 0
        if task.name == "send-message" and not args.confirm_send:
            raise ValueError("发送消息必须添加 --confirm-send")
        if not _confirm(task, yes=args.yes):
            print(json.dumps({"status": "cancelled"}, ensure_ascii=False, indent=2))
            return 2
        if args.start_delay < 0:
            raise ValueError("start_delay must not be negative")
        if args.start_delay:
            print(
                f"请在 {args.start_delay:g} 秒内完成准备: {task.preparation}",
                file=sys.stderr,
            )
            time.sleep(args.start_delay)
        stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S-%f")
        run_name = f"{task.name}-{stamp}"
        runtime = GUIAgentRuntime(
            ScriptedAgent(task),
            DesktopPerception(gpu=args.ocr_gpu),
            ActionExecutor(InputController(pause=0.1, failsafe=True)),
            artifact_dir=Path(args.artifact_dir) / run_name,
            max_actions=len(task.decisions),
            analyze_screen=args.analyze_screen,
            action_delay=0.2,
            action_policy=policy,
        )
        report = runtime.run(task.goal, execute=True)
        print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
        return 0 if report.status == "completed" else 1
    except KeyboardInterrupt:
        print(
            json.dumps(
                {"status": "interrupted", "message": "用户已停止运行"},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 130
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        print(
            json.dumps({"status": "error", "error": str(error)}, ensure_ascii=False, indent=2)
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
