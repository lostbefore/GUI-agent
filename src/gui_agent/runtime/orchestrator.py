from __future__ import annotations

import json
import time
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import cv2

from gui_agent.agent import AgentDecision, DesktopAgent, Plan
from gui_agent.coordinates import Box, CoordinateMapper
from gui_agent.perception import DesktopPerception, UIElement
from gui_agent.screen import ScreenFrame

from .executor import ActionExecutor, ActionResult
from .progress import ProgressRecorder
from .robustness import RetryPolicy, ScreenStateChecker
from .safety import ActionPolicy, UnsafeActionError


@dataclass(slots=True)
class Observation:
    frame: ScreenFrame
    screenshot: str
    annotated: str | None
    elements: list[UIElement]
    context: str


@dataclass(slots=True)
class ExecutionEvent:
    index: int
    screenshot: str
    annotated: str | None
    decision: AgentDecision
    result: ActionResult
    attempt: int = 1


@dataclass(slots=True)
class ExecutionReport:
    goal: str
    mode: str
    status: str
    plan: Plan
    events: list[ExecutionEvent] = field(default_factory=list)
    report_file: str | None = None


class GUIAgentRuntime:
    """Desktop execution loop."""

    def __init__(
        self,
        agent: DesktopAgent,
        perception: DesktopPerception,
        executor: ActionExecutor,
        *,
        artifact_dir: str | Path = "artifacts/runtime",
        max_actions: int = 12,
        capture_scale: float = 1.0,
        max_screen_pixels: int = 1_048_576,
        analyze_screen: bool = True,
        max_elements: int = 80,
        action_delay: float = 0.5,
        max_retries: int = 0,
        retry_delay: float = 1.0,
        state_checker: ScreenStateChecker | None = None,
        action_policy: ActionPolicy | None = None,
        progress: ProgressRecorder | None = None,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if max_actions <= 0:
            raise ValueError("max_actions must be positive")
        if capture_scale <= 0:
            raise ValueError("capture_scale must be positive")
        if max_screen_pixels <= 0:
            raise ValueError("max_screen_pixels must be positive")
        if max_elements < 0:
            raise ValueError("max_elements must not be negative")
        if action_delay < 0:
            raise ValueError("action_delay must not be negative")
        self.agent = agent
        self.perception = perception
        self.executor = executor
        self.artifact_dir = Path(artifact_dir)
        self.max_actions = max_actions
        self.capture_scale = capture_scale
        self.max_screen_pixels = max_screen_pixels
        self.analyze_screen = analyze_screen
        self.max_elements = max_elements
        self.action_delay = action_delay
        self.retry_policy = RetryPolicy(max_retries, retry_delay)
        self.state_checker = state_checker or ScreenStateChecker()
        self.action_policy = action_policy or ActionPolicy()
        self.progress = progress or ProgressRecorder(self.artifact_dir / "progress.jsonl")
        self.sleeper = sleeper

    def _save_report(self, report: ExecutionReport) -> ExecutionReport:
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        path = self.artifact_dir / "report.json"
        report.report_file = str(path)
        path.write_text(json.dumps(asdict(report), ensure_ascii=False, indent=2), encoding="utf-8")
        self.progress.record("finished", status=report.status, report_file=str(path))
        return report

    def _save_model_response(self, name: str, source: Any) -> None:
        response = getattr(source, "last_response", "")
        if not response:
            return
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        (self.artifact_dir / name).write_text(str(response), encoding="utf-8")

    def _fit_frame(self, frame: ScreenFrame) -> ScreenFrame:
        height, width = frame.image.shape[:2]
        # 限制截图尺寸
        pixels = width * height
        if pixels <= self.max_screen_pixels:
            return frame
        ratio = (self.max_screen_pixels / pixels) ** 0.5
        out_width = max(1, round(width * ratio))
        out_height = max(1, round(height * ratio))
        image = cv2.resize(frame.image, (out_width, out_height), interpolation=cv2.INTER_AREA)
        mapper = frame.mapper
        fitted_mapper = CoordinateMapper(
            out_width,
            out_height,
            mapper.screen_width,
            mapper.screen_height,
            mapper.origin_x,
            mapper.origin_y,
        )
        return ScreenFrame(image, fitted_mapper)

    @staticmethod
    def _image_box(box: Box, mapper: CoordinateMapper) -> list[int]:
        return [
            round((box.left - mapper.origin_x) / mapper.scale_x),
            round((box.top - mapper.origin_y) / mapper.scale_y),
            round((box.right - mapper.origin_x) / mapper.scale_x),
            round((box.bottom - mapper.origin_y) / mapper.scale_y),
        ]

    def _screen_context(self, frame: ScreenFrame, elements: Iterable[UIElement]) -> str:
        # 生成界面摘要
        payload = []
        for element in list(elements)[: self.max_elements]:
            payload.append(
                {
                    "kind": element.kind,
                    "text": element.text,
                    "confidence": round(element.confidence, 3),
                    "box": self._image_box(element.box, frame.mapper),
                }
            )
        return json.dumps(payload, ensure_ascii=False)

    def observe(self, index: int, *, attempt: int = 0) -> Observation:
        frame = self._fit_frame(self.perception.capture(scale=self.capture_scale))
        elements = self.perception.analyze(frame) if self.analyze_screen else []
        metrics = getattr(self.perception, "last_metrics", None)
        if isinstance(metrics, dict):
            self.progress.record("perception_finished", index=index, attempt=attempt, **metrics)
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        suffix = "" if not attempt else f"-retry-{attempt}"
        screenshot = self.artifact_dir / f"step-{index:02d}{suffix}.png"
        if not cv2.imwrite(str(screenshot), frame.image):
            raise OSError(f"Could not write screenshot to {screenshot}")
        annotated: Path | None = None
        if elements:
            annotated = self.artifact_dir / f"step-{index:02d}{suffix}-annotated.png"
            self.perception.save_annotated(frame, elements, annotated)
        return Observation(
            frame,
            str(screenshot),
            str(annotated) if annotated else None,
            elements,
            self._screen_context(frame, elements),
        )

    @staticmethod
    def _update_plan(plan: Plan, decision: AgentDecision, result: ActionResult) -> None:
        if not result.success:
            return
        if decision.action == "finish":
            for step in plan.steps:
                if step.status == "pending":
                    step.status = "completed"
            return
        step_id = (decision.parameters or {}).get("step_id")
        if step_id is None:
            return
        for step in plan.steps:
            if step.id == int(step_id):
                step.status = "completed"
                return

    @staticmethod
    def _response_name(index: int, attempt: int) -> str:
        return (
            f"step-{index:02d}-response.txt"
            if attempt == 1
            else f"step-{index:02d}-retry-{attempt - 1}-response.txt"
        )

    def _decide(
        self,
        goal: str,
        plan: Plan,
        observation: Observation,
        history: list[dict[str, Any]],
        index: int,
        attempt: int,
    ) -> AgentDecision:
        self.progress.record("deciding", index=index, attempt=attempt)
        try:
            decision = self.agent.decide(
                goal,
                plan,
                observation.screenshot,
                screen_context=observation.context,
                history=history,
            )
        except Exception:
            self._save_model_response(self._response_name(index, attempt), self.agent)
            self.progress.record(
                "error", index=index, attempt=attempt, message="action decision failed"
            )
            raise
        self._save_model_response(self._response_name(index, attempt), self.agent)
        self.progress.record("decision_ready", index=index, attempt=attempt, action=decision.action)
        return decision

    def _run_action(
        self, decision: AgentDecision, observation: Observation
    ) -> tuple[ActionResult, bool]:
        try:
            self.action_policy.validate(decision)
        except UnsafeActionError as error:
            return ActionResult(
                decision.action,
                False,
                f"\u5b89\u5168\u7b56\u7565\u62d2\u7edd\u52a8\u4f5c: {error}",
                decision.parameters or {},
            ), True
        return self.executor.execute(decision, observation.frame.mapper), False

    @staticmethod
    def _history_event(
        index: int, attempt: int, decision: AgentDecision, result: ActionResult
    ) -> dict[str, Any]:
        return {
            "index": index,
            "attempt": attempt,
            "action": decision.action,
            "reason": decision.reason,
            "parameters": decision.parameters or {},
            "success": result.success,
            "message": result.message,
        }

    def _record_change(
        self, before: Observation, after: Observation, index: int, attempt: int
    ) -> None:
        # 检查界面变化
        change = self.state_checker.compare(before.frame, after.frame)
        self.progress.record(
            "state_checked",
            index=index,
            attempt=attempt,
            changed=change.changed,
            difference=round(change.score, 3),
        )

    def run(self, goal: str, *, execute: bool = False) -> ExecutionReport:
        if not goal.strip():
            raise ValueError("goal must not be empty")
        mode = "execute" if execute else "preview"
        self.progress.record("starting", goal=goal, mode=mode)
        self.progress.record("observing", index=0)
        observation = self.observe(0)
        self.progress.record("observed", index=0, screenshot=observation.screenshot)
        self.progress.record("planning")
        try:
            plan = self.agent.plan(goal, observation.screenshot, observation.context)
        except Exception:
            self._save_model_response("plan-response.txt", getattr(self.agent, "planner", None))
            self.progress.record("error", message="task planning failed")
            raise
        self._save_model_response("plan-response.txt", getattr(self.agent, "planner", None))
        self.progress.record(
            "planned",
            steps=len(plan.steps),
            fallback=bool(getattr(getattr(self.agent, "planner", None), "used_fallback", False)),
        )
        history: list[dict[str, Any]] = []
        events: list[ExecutionEvent] = []

        if not execute:
            decision = self._decide(goal, plan, observation, history, 1, 1)
            try:
                self.action_policy.validate(decision)
            except UnsafeActionError as error:
                result = ActionResult(
                    decision.action,
                    False,
                    f"\u5b89\u5168\u7b56\u7565\u62d2\u7edd\u52a8\u4f5c: {error}",
                    decision.parameters or {},
                )
                status = "blocked"
            else:
                result = ActionResult(
                    decision.action, True, "preview complete", decision.parameters or {}
                )
                status = "preview"
            events.append(
                ExecutionEvent(1, observation.screenshot, observation.annotated, decision, result)
            )
            return self._save_report(ExecutionReport(goal, "preview", status, plan, events))

        status = "limit_reached"
        for index in range(1, self.max_actions + 1):
            if index > 1:
                previous_observation = observation
                self.progress.record("observing", index=index - 1)
                observation = self.observe(index - 1)
                self.progress.record("observed", index=index - 1, screenshot=observation.screenshot)
                self._record_change(previous_observation, observation, index - 1, 0)
            attempt = 1
            while True:
                decision = self._decide(goal, plan, observation, history, index, attempt)
                result, blocked = self._run_action(decision, observation)
                events.append(
                    ExecutionEvent(
                        index,
                        observation.screenshot,
                        observation.annotated,
                        decision,
                        result,
                        attempt,
                    )
                )
                history.append(self._history_event(index, attempt, decision, result))
                self.progress.record(
                    "action_finished",
                    index=index,
                    attempt=attempt,
                    action=decision.action,
                    success=result.success,
                    message=result.message,
                )
                if result.success:
                    self._update_plan(plan, decision, result)
                    break
                if blocked:
                    status = "blocked"
                    break
                if not self.retry_policy.should_retry(decision, result, attempt):
                    status = "failed"
                    break
                self.progress.record(
                    "retrying",
                    index=index,
                    attempt=attempt + 1,
                    previous_action=decision.action,
                    reason=result.message,
                )
                if self.retry_policy.retry_delay:
                    self.sleeper(self.retry_policy.retry_delay)
                previous_observation = observation
                self.progress.record("observing", index=index, attempt=attempt)
                observation = self.observe(index, attempt=attempt)
                self.progress.record(
                    "observed", index=index, attempt=attempt, screenshot=observation.screenshot
                )
                self._record_change(previous_observation, observation, index, attempt)
                attempt += 1
            if not result.success:
                break
            if decision.action == "finish":
                status = "completed"
                break
            if self.action_delay:
                self.sleeper(self.action_delay)
        return self._save_report(ExecutionReport(goal, "execute", status, plan, events))
