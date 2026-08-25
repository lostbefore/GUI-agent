# 基于多模态大模型的桌面 GUI 智能体开发与优化

## 第 4 周提交内容

项目大纲对第四周的原文要求是“集成前面的模块，实现智能体”。以下内容是根据该要求整理的提交范围。

| 提交内容 | 内容 | 项目内路径 |
|---|---|---|
| 系统原型 v1.0 | 感知、规划、决策、控制、反馈和安全闭环 | [`src/gui_agent/runtime/`](src/gui_agent/runtime/) |
| 基础任务测试报告 | 自动测试结果和真实桌面验收方法 | [`docs/week4-basic-task-report.md`](docs/week4-basic-task-report.md) |
| 真实桌面验收工具 | 5 类基础任务的可控执行入口 | [`src/gui_agent/runtime/acceptance.py`](src/gui_agent/runtime/acceptance.py) |

主要新增文件：

```text
src\gui_agent\runtime\
├── executor.py        # 动作执行与坐标映射
├── orchestrator.py    # 截图决策执行闭环
├── safety.py          # 动作安全策略
├── progress.py        # 实时进度记录
├── monitor.py         # 同屏进度悬浮窗
├── acceptance.py      # 真实桌面验收入口
└── cli.py             # 模型驱动入口

configs\agent-v1.example.toml
tests\test_executor.py
tests\test_runtime.py
tests\test_runtime_cli.py
tests\test_safety.py
tests\test_acceptance.py
tests\test_progress.py
tests\test_monitor.py
docs\week4-basic-task-report.md
```

## 第 3 周交付物



| 正式交付物 | 内容 | 项目内路径 |
|---|---|---|
| 数据集预处理脚本 | ScreenAgent、WebArena、Mind2Web 的读取、统一格式转换和命令行处理代码 | [`src/gui_agent/datasets/`](src/gui_agent/datasets/) |
| 基础 Agent 框架代码 | 多模态 Agent、任务拆解、LangChain 接口、本地模型与 API 调用代码 | [`src/gui_agent/agent/`](src/gui_agent/agent/)、[`src/gui_agent/models/`](src/gui_agent/models/)、[`configs/`](configs/) |

具体文件：

```text
GUI-agent\
├── src\gui_agent\datasets\
│   ├── schema.py                 # 统一 GUI 任务数据格式
│   ├── preprocessors.py          # 三个公开数据集预处理器
│   └── cli.py                    # 数据预处理命令行入口
├── src\gui_agent\agent\
│   ├── core.py                   # 基础多模态 Agent
│   ├── planner.py                # 任务拆解与规划
│   ├── config.py                 # 模型配置加载
│   ├── json_utils.py             # 模型 JSON 输出解析
│   └── cli.py                    # Agent 命令行入口
├── src\gui_agent\models\
│   ├── base.py                   # 统一模型协议
│   ├── transformers_local.py     # 本地多模态模型后端
│   └── openai_compatible.py      # OpenAI-compatible API 后端
└── configs\
    ├── agent-local.example.toml  # 本地 Qwen 配置
    └── agent-api.example.toml    # API 调用配置
```


以下内容体积较大，只保留在本地，不提交到代码仓库：`data/processed/`、三个原始数据集仓库和 Qwen-VL 模型权重。



## 项目进度

| 周次 | 核心工作模块 | PDF 规定交付物 | 当前状态 |
|---|---|---|---|
| 第 1 周 | 行业技术调研与开发环境搭建 | GUI 智能体技术调研报告、开发环境配置文档 | 已完成 |
| 第 2 周 | 桌面感知与控制核心模块开发 | 完整模块代码、单元测试报告 | 已完成 |
| 第 3 周 | 公开 GUI 数据集处理与基础 Agent 框架搭建 | 数据集预处理脚本、基础 Agent 框架代码 | 已完成 |
| 第 4 周 | 端到端 GUI 任务执行系统集成 | 系统原型 v1.0、基础任务测试报告 | 已完成 |
| 第 5 周 | 多模态大模型 LoRA 微调与能力提升 | 微调权重、微调效果对比报告 | 已完成 |
| 第 6 周 | 高级功能与系统鲁棒性优化 | 系统 v2.0、鲁棒性测试报告 | 待开发 |
| 第 7 周 | 系统全面评估与性能分析 | 全面评估报告、性能可视化图表 | 待开发 |
| 第 8 周 | 项目总结与求职作品集整合 | 完整代码仓库、技术报告、演示视频 | 待开发 |

## 第 2 周：桌面感知与控制核心模块


当前实现：

- 全屏和指定区域截图，可按目标尺寸缩放；
- EasyOCR 中英文文字识别，返回文本、置信度和屏幕坐标边界框；
- OpenCV 轮廓检测，识别候选 UI 区域；
- 点击、双击、文本输入、按键、快捷键、滚动和拖拽；
- 归一化坐标、截图坐标和屏幕坐标转换；
- OpenCV 静态标注图和 PyQt5 实时透明覆盖层；
- PyAutoGUI FAILSAFE、坐标检查和操作暂停等安全保护。

主要代码：

```text
src/gui_agent/
├── screen.py          # 跨平台截图与分辨率适配
├── perception.py      # OCR 和 UI 区域检测
├── coordinates.py     # 坐标映射与边界框
├── overlay.py         # PyQt5 透明覆盖层
├── control.py         # 鼠标键盘控制
└── cli.py             # inspect/overlay 命令行入口
```


## 第 3 周：公开数据集与基础 Agent 框架



### 数据集预处理

项目将三种原始数据格式统一为 JSONL 记录：

```json
{
  "dataset": "mind2web",
  "task_id": "任务编号",
  "split": "train",
  "instruction": "用户任务",
  "steps": [],
  "images": [],
  "metadata": {}
}
```

当前已处理结果：

| 数据集 | 原始数据位置 | 处理结果 | 记录数 |
|---|---|---|---:|
| ScreenAgent | `C:\Users\m1865\Desktop\ScreenAgent` | `data/processed/screenagent.jsonl` | 273 |
| WebArena | `C:\Users\m1865\Desktop\webarena` | `data/processed/webarena.jsonl` | 816 |
| Mind2Web | `C:\Users\m1865\Desktop\Mind2Web` | `data/processed/mind2web.jsonl` | 2350 |

Mind2Web 包含 `train`、`test_task`、`test_website` 和 `test_domain` 四个划分。

预处理入口：

```powershell
python -m gui_agent.datasets.cli screenagent `
  --input C:\Users\m1865\Desktop\ScreenAgent\data `
  --output data\processed\screenagent.jsonl

python -m gui_agent.datasets.cli webarena `
  --input C:\Users\m1865\Desktop\webarena `
  --output data\processed\webarena.jsonl

python -m gui_agent.datasets.cli mind2web `
  --input C:\Users\m1865\Desktop\Mind2Web `
  --output data\processed\mind2web.jsonl
```


### 基础多模态 Agent

当前框架包含：

- `TaskPlanner`：把用户目标拆成不超过 6 个可观察、原子化的 GUI 步骤；
- `DesktopAgent`：组合任务计划与截图，生成下一步动作；
- LangChain `RunnableLambda` 适配接口；
- 严格 JSON 计划和动作解析；
- 动作白名单：`click`、`double_click`、`type`、`press`、`hotkey`、`scroll`、`drag`、`wait`、`finish`；
- 本地 Transformers 多模态模型后端；
- OpenAI-compatible HTTP API 后端。

```text
用户目标 ──> TaskPlanner ──> JSON 任务计划
                              │
屏幕截图 ──> DesktopAgent <───┘
                  │
                  ├──> Transformers 本地模型
                  └──> OpenAI-compatible API
                              │
                              └──> AgentDecision
```

主要代码：

```text
src/gui_agent/
├── datasets/
│   ├── schema.py
│   ├── preprocessors.py
│   └── cli.py
├── agent/
│   ├── planner.py
│   ├── core.py
│   ├── config.py
│   ├── json_utils.py
│   └── cli.py
└── models/
    ├── base.py
    ├── transformers_local.py
    └── openai_compatible.py
```

### 本地 Qwen 部署

当前使用 Qwen2.5-VL-3B-Instruct。配置采用：

- bitsandbytes NF4 4-bit 量化；
- BF16 计算；
- 双重量化；
- 最大视觉输入像素限制；
- `device_map="auto"` 自动设备分配。

## 第 4 周：端到端 GUI 任务执行系统

系统原型将前序模块组合为完整执行流程：

```text
用户指令
   ↓
屏幕截图与 UI 识别
   ↓
任务拆解与动作决策
   ↓
截图坐标映射到屏幕坐标
   ↓
鼠标键盘执行单个动作
   ↓
重新截图并反馈执行结果
   └──────────────→ 下一轮决策
```

当前实现：

- 首次截图参与任务规划；
- OCR 文字和 UI 区域作为模型决策上下文；
- 每次只执行一个原子动作；
- 点击、双击、右键打开、输入、按键、快捷键、滚动、拖拽和等待动作映射；
- 模型截图坐标自动转换为真实屏幕坐标；
- 每次动作后重新截图并反馈成功或失败结果；
- `finish` 动作结束任务；
- 最大动作数限制和 PyAutoGUI FAILSAFE；
- 中文输入自动使用剪贴板粘贴；
- 终端命令和项目自调用文本默认拦截；
- 执行前倒计时允许切换到目标窗口；
- 原始截图和标注截图保存到运行记录目录；
- 每次运行使用独立目录并生成 `report.json`；
- 实时生成 `progress.jsonl`；
- 可选显示截图排除和鼠标穿透的进度悬浮窗；
- 默认预览模式不操作桌面；
- 真实执行需要 `--execute` 并进行确认。

系统入口：

```text
gui-agent-v1             模型驱动闭环
gui-agent-acceptance     真实桌面验收
```

配置文件：[`configs/agent-v1.example.toml`](configs/agent-v1.example.toml)。



## 安装环境

- Python 3.10+
- PyTorch 2.2+
- NVIDIA GPU 8GB 或以上显存
- Git、Git LFS



## 使用方法

### 屏幕识别与标注

```powershell
python -m gui_agent.cli inspect --output artifacts\screen.png
```

### 实时边界框覆盖层

```powershell
python -m gui_agent.cli overlay
```

### 本地模型任务规划

```powershell
python -m gui_agent.agent.cli `
  --config configs\agent-local.example.toml `
  --goal "打开记事本并输入 hello"
```

### 根据截图生成下一步动作

```powershell
python -m gui_agent.agent.cli `
  --config configs\agent-local.example.toml `
  --goal "Find the wrong line of code and fix it" `
  --screenshot "C:\Users\m1865\Desktop\ScreenAgent\data\ScreenAgent\test\08a2def941d942ffb542ba0ba3d8aa99\images\2024-01-13_21-34-31-146954.jpg"
```

### v1.0 预览模式

预览模式会截图、识别、规划并生成第一步动作，但不会操作鼠标键盘：

```powershell
python -m gui_agent.runtime.cli `
  --config configs\agent-v1.example.toml `
  --goal "打开浏览器"
```

### v1.0 执行模式

执行模式会在确认后操作当前桌面：

```powershell
python -m gui_agent.runtime.cli `
  --config configs\agent-v1.example.toml `
  --goal "打开浏览器并搜索 GUI Agent" `
  --start-delay 8 `
  --show-progress `
  --execute
```

确认提示出现后输入 `yes`，然后在倒计时结束前切换到目标桌面。`--show-progress` 会在右上角显示当前阶段，悬浮窗鼠标穿透且使用 Windows 截图排除能力，不会进入模型截图；若截图排除不可用，悬浮窗会自动退出。模型若生成 PowerShell、CMD、Python 或项目自调用文本，运行会以 `blocked` 状态停止。

### 真实桌面基础任务验收

验收入口默认只显示完整动作序列，不会操作桌面：

```powershell
python -m gui_agent.runtime.acceptance --task open-browser
```

确认预览后执行真实动作：

```powershell
python -m gui_agent.runtime.acceptance --task open-browser --execute
```

其余任务：

```powershell
python -m gui_agent.runtime.acceptance --task search-content --query "GUI Agent" --execute
python -m gui_agent.runtime.acceptance --task open-file --file "README.md" --execute
python -m gui_agent.runtime.acceptance --task send-message --message "GUI Agent 测试消息" --confirm-send --execute
python -m gui_agent.runtime.acceptance --task close-app --execute
```

每项任务都有 5 秒准备时间。搜索前需让浏览器保持前台，发送前需打开自己的测试会话，关闭前需打开无未保存内容的测试应用。完整验收步骤见 [`docs/week4-basic-task-report.md`](docs/week4-basic-task-report.md)。

运行记录保存在：

```text
artifacts/runtime/运行时间/
├── step-00.png
├── step-00-annotated.png
├── step-01.png
├── progress.jsonl
└── report.json
```


## 测试与验收


```powershell
conda activate gui-agent
Set-Location C:\Users\m1865\Desktop\GUI-agent

$pytestTemp = Join-Path $PWD "artifacts\pytest-tmp"
New-Item -ItemType Directory -Force $pytestTemp

python -m pytest -q `
  --basetemp="$pytestTemp\run" `
  --cov=gui_agent `
  --cov-report=term-missing

python -m ruff check .
python -m ruff format --check .
```

当前自动测试结果：

```text
142 passed
总体语句覆盖率 93%
Ruff checks passed
```

自动测试使用模拟输入后端，不会打开真实应用。第 4 周测试结果和真实桌面验收方法见 [`docs/week4-basic-task-report.md`](docs/week4-basic-task-report.md)。

## 第六周：高级功能与系统鲁棒性优化

已交付系统 v2.0 和鲁棒性测试报告。

| 交付物 | 路径 |
|---|---|
| 系统 v2.0 配置 | [`configs/agent-v2.example.toml`](configs/agent-v2.example.toml) |
| 鲁棒性测试报告 | [`docs/week6-robustness-test-report.md`](docs/week6-robustness-test-report.md) |
| v2 使用说明 | [`docs/week6-usage-guide.md`](docs/week6-usage-guide.md) |
| 重试与感知测试 | [`tests/test_robustness.py`](tests/test_robustness.py) |

实现内容：复杂任务分步规划、失败后重新感知与重试、屏幕变化检测、OCR/UI 结果去重、结构化运行日志。

## Week 7 evaluation

- 20-task benchmark: data/week7/benchmark-tasks.json`n- Evaluation CLI: src/gui_agent/evaluation/cli.py`n- System evaluation report: week7-system-evaluation-report.md`n- Performance charts: rtifacts/week7/charts/`n