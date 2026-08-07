# 第四周交付清单

## 1 大纲要求

项目大纲对第四周的原文要求为：

```text
集成前面的模块，实现智能体
```

项目总体目标要求智能体能够读取屏幕、理解任务、自主规划、执行鼠标键盘操作，并根据屏幕反馈调整。因此第四周的核心验收对象是一个能够运行的端到端系统原型。

## 2 提交内容

### 2.1 系统原型 v1.0

系统原型入口和闭环代码：

```text
src/gui_agent/runtime/
├── __init__.py
├── cli.py
├── orchestrator.py
├── executor.py
├── safety.py
├── progress.py
├── monitor.py
└── acceptance.py
```

各文件作用：

| 文件 | 作用 |
|---|---|
| `cli.py` | 模型驱动命令行入口 |
| `orchestrator.py` | 截图、规划、决策、执行和反馈闭环 |
| `executor.py` | 原子动作执行和坐标映射 |
| `safety.py` | 危险文本和危险坐标拦截 |
| `progress.py` | 实时进度记录 |
| `monitor.py` | 截图排除的同屏进度悬浮窗 |
| `acceptance.py` | 五类真实桌面任务验收入口 |

系统原型调用的前序模块也属于提交代码：

```text
src/gui_agent/screen.py
src/gui_agent/perception.py
src/gui_agent/coordinates.py
src/gui_agent/control.py
src/gui_agent/overlay.py

src/gui_agent/agent/
src/gui_agent/models/
```

运行配置：

```text
configs/agent-v1.example.toml
```

项目入口和依赖：

```text
pyproject.toml
README.md
```

### 2.2 第四周测试报告

```text
docs/week4-basic-task-report.md
```

报告包含：

- 感知、规划、动作和反馈闭环测试
- 动作执行测试
- 安全边界测试
- 五类基础任务测试
- 第四周专项覆盖率
- 完整项目回归结果

### 2.3 真实桌面验收说明

```text
docs/week4-real-desktop-acceptance.md
```

包含打开浏览器、搜索内容、打开文件、发送测试消息和关闭测试应用的操作方法。

### 2.4 自动测试代码

第四周直接相关的测试文件：

```text
tests/test_executor.py
tests/test_runtime.py
tests/test_runtime_cli.py
tests/test_safety.py
tests/test_acceptance.py
tests/test_progress.py
tests/test_monitor.py
```

前序模块回归测试保留在 `tests/`目录中并一起提交。

## 3 当前验证结果

```text
完整测试 142 passed
总体语句覆盖率 93%
第四周专项 76 passed
第四周运行模块覆盖率 99%
Ruff checks passed
```

## 4 GitHub应上传内容

建议上传：

```text
.gitignore
README.md
pyproject.toml
configs/
data/README.md
docs/
src/
tests/
```

不要上传：

```text
artifacts/
data/raw/
data/processed/
tmp/
.coverage
.pytest_cache/
.ruff_cache/
__pycache__/
D:/Qwen-VL/
```

其中 `data/processed/mind2web.jsonl`约9.5GB，模型权重也不应进入代码仓库。

## 5 上传前检查

在 Anaconda Prompt 中运行：

```bat
cd /d C:\Users\m1865\Desktop\GUI-agent
conda activate gui-agent

python -m pytest -q -p no:cacheprovider --basetemp="%TEMP%\gui-agent-release-%RANDOM%"
python -m ruff check .
```

只添加应提交的目录：

```bat
git add .gitignore README.md pyproject.toml configs data\README.md docs src tests
git status --short
```

确认状态中没有数据集、模型权重、运行截图和缓存后，再自行提交和推送。

## 6 交付结论

第四周已经形成系统原型 v1.0。系统能够组合桌面截图、OCR和UI识别、任务规划、多模态动作决策、坐标映射、鼠标键盘执行、屏幕反馈、安全拦截、进度显示和运行记录，满足“集成前面的模块，实现智能体”的要求。
