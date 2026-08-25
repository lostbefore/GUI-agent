# 第六周鲁棒性测试报告

## 交付结论

系统 v2.0 已完成，对应高级功能与系统鲁棒性优化阶段。自动化测试共 151 项全部通过，代码总覆盖率为 85%，Ruff 静态检查通过。

## 第六周功能实现

| 目标 | 实现 | 主要代码 |
|---|---|---|
| 复杂任务拆解与分步执行 | `TaskPlanner` 支持最多 8 步的原子计划；决策提示引入当前未完成步骤 | `src/gui_agent/agent/planner.py`、`src/gui_agent/agent/core.py` |
| 错误检测与自动重试 | 动作失败后重新截图、重新决策并按策略重试；安全策略拦截不重试 | `src/gui_agent/runtime/robustness.py`、`src/gui_agent/runtime/orchestrator.py` |
| 屏幕感知优化 | OCR 与区域结果按 IoU 去重，保留置信度更高的元素，记录元素数与耗时 | `src/gui_agent/perception.py` |
| 实时监控与日志 | `progress.jsonl` 记录阶段事件，`progress.log` 记录结构化日志，悬浮窗显示步骤和重试次数 | `src/gui_agent/runtime/progress.py`、`src/gui_agent/runtime/monitor.py` |

## 自动化测试

测试命令：

```powershell
$env:PYTHONPATH='src'
python -m pytest -q -p no:cacheprovider --cov=gui_agent --cov-report=term-missing --cov-report=xml:artifacts\week6-coverage.xml
python -m ruff check .
```

测试结果：

- `151 passed in 1.19s`
- 总体代码覆盖率：`85%`
- `src/gui_agent/runtime/orchestrator.py`：`99%`
- `src/gui_agent/perception.py`：`95%`
- `src/gui_agent/runtime/progress.py`：`98%`
- `src/gui_agent/runtime/robustness.py`：`89%`
- `All checks passed!`

## 新增重点测试

| 测试项 | 验证内容 | 结果 |
|---|---|---|
| 重试策略 | 失败动作仅在配置次数内重试，`finish` 不重试 | 通过 |
| 重新感知闭环 | 第一次动作失败后重新截图、重新决策、重试并完成 | 通过 |
| 屏幕变化检测 | 连续截图的平均灰度差分数及阈值判定 | 通过 |
| 感知去重 | 重叠文字和 UI 区域按 IoU 合并 | 通过 |
| 运行记录 | 重试、屏幕检查、感知指标写入 JSONL 和日志 | 通过 |
| 全回归 | 第一至第五周现有测试 | 通过 |

## 产物位置

- 系统 v2.0 配置：`configs/agent-v2.example.toml`
- 鲁棒性测试：`tests/test_robustness.py`
- 覆盖率产物：`artifacts/week6-coverage.xml`
- 本报告：`docs/week6-robustness-test-report.md`