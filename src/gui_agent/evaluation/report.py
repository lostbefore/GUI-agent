from __future__ import annotations

import os
from pathlib import Path

from .benchmark import BenchmarkTask, EvaluationSummary, MetricRow

TITLE = "# \u7b2c\u4e03\u5468\u7cfb\u7edf\u5168\u9762\u8bc4\u4f30\u62a5\u544a"


def _table(rows: list[MetricRow]) -> list[str]:
    lines = [
        "| 分组 | 任务数 | 成功数 | 成功率 | 平均耗时（秒） | 动作错误率 | 平均重试次数 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row.group} | {row.total} | {row.success_count} | "
            f"{row.success_rate:.1%} | {row.average_duration_seconds:.2f} | "
            f"{row.action_error_rate:.1%} | {row.average_retries:.2f} |"
        )
    return lines


def write_report(
    tasks: list[BenchmarkTask],
    summary: EvaluationSummary,
    chart_dir: str | Path,
    path: str | Path,
) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    chart_prefix = Path(os.path.relpath(Path(chart_dir), output.parent)).as_posix()
    overall = summary.overall
    task_lines = [
        f"| {task.task_id} | {task.title} | {task.application} | {task.category} | "
        f"{task.difficulty} | {task.resolution} | {task.expected_actions} |"
        for task in tasks
    ]
    text = "\n".join(
        [
            TITLE,
            "",
            "## 1. \u8bc4\u4f30\u7ed3\u8bba",
            "",
            f"本次评估包含 20 项桌面 GUI 基准任务。在可控执行基准下，任务成功率为 **{overall.success_rate:.1%}**（{overall.success_count}/{overall.total}），平均执行耗时 **{overall.average_duration_seconds:.2f} 秒**，动作错误率为 **{overall.action_error_rate:.1%}**，平均重试次数为 **{overall.average_retries:.2f}**。",
            "",
            "本报告的所有记录均使用 `controlled` 可控执行模式。该模式不会操作真实桌面，用于验证任务编排、重试、日志与统计聚合流程。因此，本结果是可复现的运行时基准，不代表真实外部应用或大模型的泛化性能。",
            "",
            "## 2. \u8bc4\u4f30\u8303\u56f4\u4e0e\u6307\u6807",
            "",
            "- 任务成功率：成功任务数除以总任务数。",
            "- 平均执行耗时：20 条任务记录执行时间的算术平均值。",
            "- 动作错误率：失败动作次数除以总动作次数。",
            "- 平均重试次数：每个任务的自动重试次数的算术平均值。",
            "- 分析维度：应用类型、任务难度与屏幕分辨率。",
            "",
            "## 3. 20 \u9879\u57fa\u51c6\u4efb\u52a1\u96c6",
            "",
            "| ID | 任务 | 应用 | 类别 | 难度 | 分辨率 | 预计动作数 |",
            "|---|---|---|---|---|---|---:|",
            *task_lines,
            "",
            "任务集覆盖浏览器、文件资源管理器、记事本、计算器和 Windows 设置，包含基础、中级与高级任务，并在三种分辨率下进行统计。",
            "",
            "## 4. \u6574\u4f53\u7ed3\u679c",
            "",
            *_table([overall]),
            "",
            "## 5. \u5206\u7ec4\u6027\u80fd\u5206\u6790",
            "",
            "### 5.1 \u6309\u96be\u5ea6",
            "",
            *_table(summary.by_difficulty),
            "",
            "高级任务包含跨应用工作流或依赖界面状态的操作，步骤数更多，可更直接地观察恢复行为。",
            "",
            "### 5.2 \u6309\u5c4f\u5e55\u5206\u8fa8\u7387",
            "",
            *_table(summary.by_resolution),
            "",
            "分辨率分组用于验证三种显示环境下的截图缩放与坐标映射能力。",
            "",
            "### 5.3 \u6309\u5e94\u7528",
            "",
            *_table(summary.by_application),
            "",
            "应用分组便于定位错误集中点，并比较不同交互类型。",
            "",
            "## 6. \u6027\u80fd\u5206\u6790\u56fe\u8868",
            "",
            f"![各难度任务成功率]({chart_prefix}/success-by-difficulty.png)",
            "",
            f"![各分辨率平均耗时]({chart_prefix}/duration-by-resolution.png)",
            "",
            f"![各应用动作错误率]({chart_prefix}/error-rate-by-application.png)",
            "",
            "以上图表由 Matplotlib 根据汇总 JSON 结果自动生成，可通过基准测试命令重新生成。",
            "",
            "## 7. \u4e0e Ui-TARS \u3001Claude Computer Use \u7684\u6280\u672f\u5bf9\u6bd4",
            "",
            "| Dimension | System v2.0 | Ui-TARS | Claude Computer Use | Gap and direction |",
            "|---|---|---|---|---|",
            "| Perception | EasyOCR, OpenCV regions, and local vision-model context | Native screenshot perception and unified GUI actions | Screenshot plus mouse and keyboard tool interface | Expand GUI grounding data and semantic element recognition |",
            "| Planning and recovery | Up to 8 plan steps, re-observation, bounded retries | System-2 reasoning and reflective online traces | Multi-turn decisions using tool results | Add task-level success checks, reflection prompts, and longer-horizon memory |",
            "| Data and training | Public GUI preprocessing and small QLoRA run | Large-scale GUI screenshots and action traces | Platform-scale general model and tool ecosystem | Add cross-application, multi-resolution, execution-feedback data |",
            "| Execution and safety | Local PyAutoGUI, protected zone, terminal-text blocking | Unified cross-platform action space | Client executes requested computer tools | Add sandboxing, permission tiers, and action verification |",
            "| Evaluation | 20-task controlled benchmark with importable records | Public GUI benchmark evaluations | Documented multi-step tool loop | Align future real-desktop experiments with public benchmark protocols |",
            "",
            "Ui-TARS 采用截图作为感知输入，强调统一动作建模、系统推理和反思轨迹训练。Claude Computer Use 使用模型选择计算机工具、客户端执行并回传结果的多轮循环。此处仅对比技术路线，不将不同环境下的公开结果与本次可控基准结果直接比较。",
            "",
            "参考资料：",
            "",
            "- UI-TARS: https://arxiv.org/abs/2501.12326",
            "- Claude Computer Use: https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool",
            "",
            "## 8. \u4ea7\u7269\u4e0e\u590d\u73b0",
            "",
            "```powershell",
            "$env:PYTHONPATH='src'",
            "python -m gui_agent.evaluation.cli run --tasks old/data/week7/benchmark-tasks.json --output-dir artifacts/week7 --report old/week7-system-evaluation-report.md",
            "```",
            "",
            "输出产物：",
            "",
            "- `old/artifacts/week7/benchmark-results.jsonl`: 20 controlled records.",
            "- `old/artifacts/week7/summary.json`: overall and grouped metrics.",
            "- `old/artifacts/week7/charts/`: three performance-analysis charts.",
            "- `old/week7-system-evaluation-report.md`: this report.",
            "",
            "`summarize` 命令可读取同一结果模式的外部记录，因此后续可将真实桌面测试记录纳入统计，无需修改指标或图表代码。",
            "",
            "## 9. \u7ed3\u8bba",
            "",
            "第七周完成了可复现的 20 项任务基准测试、指标聚合、性能可视化与技术差距分析。可控基准验证了任务编排、重试、感知去重、日志记录与报告生成流程。",
            "",
        ]
    )
    output.write_text(text, encoding="utf-8")
    return output
