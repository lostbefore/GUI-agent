from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from gui_agent.agent import DesktopAgent
from gui_agent.agent.config import build_model, load_config
from gui_agent.control import InputController
from gui_agent.perception import DesktopPerception

from .executor import ActionExecutor
from .orchestrator import GUIAgentRuntime
from .progress import ProgressRecorder
from .safety import ActionPolicy


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="桌面 GUI 智能体系统原型 v1.0")
    parser.add_argument("--config", required=True, help="模型与运行配置")
    parser.add_argument("--goal", help="桌面任务指令")
    parser.add_argument("--execute", action="store_true", help="执行鼠标键盘动作")
    parser.add_argument("--yes", action="store_true", help="跳过执行确认")
    parser.add_argument("--max-actions", type=int, help="最大动作数")
    parser.add_argument("--capture-scale", type=float, help="截图缩放比例")
    parser.add_argument("--max-screen-pixels", type=int, help="截图像素上限")
    parser.add_argument("--artifact-dir", help="运行记录目录")
    parser.add_argument("--run-name", help="本次运行目录名")
    parser.add_argument("--action-delay", type=float, help="动作间隔")
    parser.add_argument("--start-delay", type=float, help="执行前等待秒数")
    parser.add_argument("--skip-analysis", action="store_true", help="关闭 OCR 与区域识别")
    parser.add_argument("--ocr-gpu", action="store_true", help="启用 OCR GPU")
    parser.add_argument("--show-progress", action="store_true", help="显示同屏进度悬浮窗")
    return parser


def _value(args: argparse.Namespace, runtime: dict[str, Any], name: str, default: Any) -> Any:
    value = getattr(args, name)
    return runtime.get(name, default) if value is None else value


def _artifact_dir(base: str | Path, run_name: str | None) -> Path:
    name = run_name or datetime.now().astimezone().strftime("%Y%m%d-%H%M%S-%f")
    if Path(name).name != name or name in {".", ".."}:
        raise ValueError("run_name must be a directory name")
    return Path(base) / name


def _wait_for_desktop(seconds: float) -> None:
    if seconds < 0:
        raise ValueError("start_delay must not be negative")
    if not seconds:
        return
    print(f"请在 {seconds:g} 秒内切换到目标窗口", file=sys.stderr)
    time.sleep(seconds)


def _start_progress_monitor(progress_file: str | Path) -> subprocess.Popen:
    command = [
        sys.executable,
        "-m",
        "gui_agent.runtime.monitor",
        "--file",
        str(Path(progress_file).resolve()),
    ]
    return subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    goal = args.goal or input("请输入桌面任务：").strip()
    if not goal:
        raise ValueError("goal must not be empty")
    if args.execute and not args.yes:
        answer = input("即将操作当前桌面 输入 yes 继续：").strip().lower()
        if answer != "yes":
            print(json.dumps({"status": "cancelled"}, ensure_ascii=False, indent=2))
            return 2

    progress: ProgressRecorder | None = None
    try:
        config = load_config(args.config)
        runtime_config = dict(config.get("runtime", {}))
        agent = DesktopAgent(build_model(config))
        perception = DesktopPerception(gpu=args.ocr_gpu)
        controller = InputController(
            pause=float(runtime_config.get("input_pause", 0.1)),
            failsafe=True,
        )
        executor = ActionExecutor(
            controller,
            max_wait=float(runtime_config.get("max_wait", 10.0)),
        )
        artifact_dir = _artifact_dir(
            _value(args, runtime_config, "artifact_dir", "artifacts/runtime"),
            args.run_name,
        )
        progress = ProgressRecorder(artifact_dir / "progress.jsonl")
        runtime = GUIAgentRuntime(
            agent,
            perception,
            executor,
            artifact_dir=artifact_dir,
            max_actions=int(_value(args, runtime_config, "max_actions", 12)),
            capture_scale=float(_value(args, runtime_config, "capture_scale", 1.0)),
            max_screen_pixels=int(
                _value(args, runtime_config, "max_screen_pixels", 1_048_576)
            ),
            analyze_screen=(
                bool(runtime_config.get("analyze_screen", True)) and not args.skip_analysis
            ),
            max_elements=int(runtime_config.get("max_elements", 80)),
            action_delay=float(_value(args, runtime_config, "action_delay", 0.5)),
            action_policy=ActionPolicy(
                block_terminal_text=bool(runtime_config.get("block_terminal_text", True)),
                max_text_length=int(runtime_config.get("max_text_length", 2000)),
            ),
            progress=progress,
        )
        if args.show_progress:
            _start_progress_monitor(progress.path)
        if args.execute:
            _wait_for_desktop(float(_value(args, runtime_config, "start_delay", 5.0)))
        report = runtime.run(goal, execute=args.execute)
    except KeyboardInterrupt:
        if progress is not None:
            progress.record("interrupted", message="用户已停止运行")
        print(
            json.dumps(
                {"goal": goal, "status": "interrupted", "message": "用户已停止运行"},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 130
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        if progress is not None:
            progress.record("error", message=str(error))
        print(
            json.dumps(
                {"goal": goal, "status": "error", "error": str(error)},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1
    print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
    return 0 if report.status in {"preview", "completed"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
