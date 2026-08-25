# 系统 v2.0 使用说明

## 配置

复制 `configs/agent-v2.example.toml` 为你的运行配置，并根据本地模型路径修改 `[model].path`。

`[runtime]` 的重要字段：

- `planner_max_steps = 8`：复杂任务的最大拆解步数
- `max_retries = 2`：单个失败动作的最大重试次数
- `retry_delay = 1.0`：重试前的等待秒数
- `screen_change_threshold = 3.0`：截图差分触发变化的阈值

## 预览模式

```powershell
$env:PYTHONPATH='src'
python -m gui_agent.runtime.cli --config configs\agent-v2.example.toml --goal "打开浏览器" --show-progress --run-name week6-preview
```

预览模式会截图、规划和决策，不会执行鼠标键盘操作。

## 执行模式

```powershell
$env:PYTHONPATH='src'
python -m gui_agent.runtime.cli --config configs\agent-v2.example.toml --goal "打开记事本" --execute --yes --show-progress --run-name week6-execute
```

运行目录包含 `report.json`、`progress.jsonl`、`progress.log`、每步截图、模型原始输出。失败重试的截图名为 `step-XX-retry-N.png`。