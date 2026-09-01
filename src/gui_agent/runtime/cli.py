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

from gui_agent.agent import DesktopAgent, TaskPlanner
from gui_agent.agent.config import build_model, load_config
from gui_agent.control import InputController
from gui_agent.perception import DesktopPerception

from .executor import ActionExecutor
from .orchestrator import GUIAgentRuntime
from .progress import ProgressRecorder
from .robustness import ScreenStateChecker
from .safety import ActionPolicy


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Desktop GUI Agent v2.0")
    parser.add_argument("--config", required=True, help="model and runtime config")
    parser.add_argument("--goal", help="desktop task")
    parser.add_argument("--execute", action="store_true", help="enable mouse and keyboard actions")
    parser.add_argument("--yes", action="store_true", help="skip execution confirmation")
    parser.add_argument("--max-actions", type=int, help="maximum actions")
    parser.add_argument("--planner-max-steps", type=int, help="maximum plan steps")
    parser.add_argument("--max-retries", type=int, help="maximum retries per failed action")
    parser.add_argument("--retry-delay", type=float, help="delay before a retry")
    parser.add_argument("--screen-change-threshold", type=float, help="screen change threshold")
    parser.add_argument("--capture-scale", type=float, help="capture scale")
    parser.add_argument("--max-screen-pixels", type=int, help="maximum screenshot pixels")
    parser.add_argument("--artifact-dir", help="artifact directory")
    parser.add_argument("--run-name", help="run directory name")
    parser.add_argument("--action-delay", type=float, help="delay between successful actions")
    parser.add_argument("--start-delay", type=float, help="seconds before execution")
    parser.add_argument(
        "--skip-analysis", action="store_true", help="disable OCR and region analysis"
    )
    parser.add_argument("--ocr-gpu", action="store_true", help="enable OCR GPU")
    parser.add_argument("--show-progress", action="store_true", help="show progress overlay")
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
    print(
        f"\u8bf7\u5728 {seconds:g} \u79d2\u5185\u5207\u6362\u5230\u76ee\u6807\u7a97\u53e3",
        file=sys.stderr,
    )
    time.sleep(seconds)


def _start_progress_monitor(progress_file: str | Path) -> subprocess.Popen:
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "gui_agent.runtime.monitor",
            "--file",
            str(Path(progress_file).resolve()),
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    goal = args.goal or input("\u8bf7\u8f93\u5165\u684c\u9762\u4efb\u52a1\uff1a").strip()
    if not goal:
        raise ValueError("goal must not be empty")
    if args.execute and not args.yes:
        answer = (
            input(
                "\u5373\u5c06\u64cd\u4f5c\u5f53\u524d\u684c\u9762 \u8f93\u5165 yes \u7ee7\u7eed\uff1a"
            )
            .strip()
            .lower()
        )
        if answer != "yes":
            print(json.dumps({"status": "cancelled"}, ensure_ascii=False, indent=2))
            return 2

    progress: ProgressRecorder | None = None
    try:
        config = load_config(args.config)
        runtime_config = dict(config.get("runtime", {}))
        model = build_model(config)
        planner = TaskPlanner(
            model, max_steps=int(_value(args, runtime_config, "planner_max_steps", 8))
        )
        agent = DesktopAgent(model, planner=planner)
        perception = DesktopPerception(gpu=args.ocr_gpu)
        controller = InputController(
            pause=float(runtime_config.get("input_pause", 0.1)), failsafe=True
        )
        executor = ActionExecutor(controller, max_wait=float(runtime_config.get("max_wait", 10.0)))
        artifact_dir = _artifact_dir(
            _value(args, runtime_config, "artifact_dir", "old/artifacts/runtime"), args.run_name
        )
        progress = ProgressRecorder(artifact_dir / "progress.jsonl")
        runtime = GUIAgentRuntime(
            agent,
            perception,
            executor,
            artifact_dir=artifact_dir,
            max_actions=int(_value(args, runtime_config, "max_actions", 12)),
            capture_scale=float(_value(args, runtime_config, "capture_scale", 1.0)),
            max_screen_pixels=int(_value(args, runtime_config, "max_screen_pixels", 1_048_576)),
            analyze_screen=bool(runtime_config.get("analyze_screen", True))
            and not args.skip_analysis,
            max_elements=int(runtime_config.get("max_elements", 80)),
            action_delay=float(_value(args, runtime_config, "action_delay", 0.5)),
            max_retries=int(_value(args, runtime_config, "max_retries", 2)),
            retry_delay=float(_value(args, runtime_config, "retry_delay", 1.0)),
            state_checker=ScreenStateChecker(
                threshold=float(_value(args, runtime_config, "screen_change_threshold", 3.0))
            ),
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
            progress.record("interrupted", message="\u7528\u6237\u5df2\u505c\u6b62\u8fd0\u884c")
        print(
            json.dumps(
                {
                    "goal": goal,
                    "status": "interrupted",
                    "message": "\u7528\u6237\u5df2\u505c\u6b62\u8fd0\u884c",
                },
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
                {"goal": goal, "status": "error", "error": str(error)}, ensure_ascii=False, indent=2
            )
        )
        return 1
    print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
    return 0 if report.status in {"preview", "completed"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
