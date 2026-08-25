# 第四周桌面 GUI 智能体系统测试报告

项目仓库：https://github.com/lostbefore/GUI-agent

## 1 基本信息

| 项目 | 内容 |
|---|---|
| 项目名称 | 基于多模态大模型的桌面 GUI 智能体开发与优化 |
| 周次目标 | 集成前序模块并实现桌面智能体 |
| 系统版本 | v1.0 |
| 测试日期 | 2026-08-05 |
| 操作系统 | Windows 11 10.0.26200 |
| Python | 3.10.20 |
| pytest | 9.1.1 |

## 2 目前的进度

系统已经串联以下模块：

```text
用户目标
   ↓
屏幕截图与分辨率映射
   ↓
OCR 与 UI 区域识别
   ↓
多模态模型任务规划
   ↓
单步动作决策
   ↓
动作安全检查
   ↓
鼠标键盘执行
   ↓
重新截图与结果反馈
   └────────→ 下一轮决策
```

主要能力包括：

- 初始截图参与任务规划
- OCR 文本和 UI 边界框参与动作决策
- 点击 双击 右键打开 输入 按键 快捷键 滚动 拖拽 等待和结束动作
- 截图坐标到屏幕坐标的自动映射
- 每个动作后重新观察屏幕
- 动作参数和执行结果反馈给下一轮决策
- 最大动作数和等待时长限制
- PyAutoGUI FAILSAFE
- 终端命令和项目自调用文本拦截
- 中文文本剪贴板输入
- 执行确认和目标窗口切换倒计时
- 每次运行独立保存截图和 JSON 报告
- 实时进度记录和截图排除悬浮窗
- 五类真实桌面任务验收入口

## 3 测试分层

### 3.1 自动测试

自动测试使用模拟截图 模拟模型和模拟输入后端，不会控制当前桌面，也不会真实打开浏览器或发送消息。

该层验证：

- 模块接口和动作分发正确
- 坐标映射正确
- 感知 规划 决策 执行和反馈能够形成闭环
- 五类基础任务的固定动作序列能够完整运行
- 危险文本能够在执行前被阻止
- 命令行确认和异常输出正确
- 真实验收场景能够正确生成

### 3.2 真实桌面验收

真实验收使用 `gui_agent.runtime.acceptance` 调用屏幕截图和 PyAutoGUI 后端，会实际操作桌面。

该层验证：

- 浏览器是否真实打开
- 搜索结果是否真实出现
- 指定文件是否真实打开
- 测试消息是否真实发送
- 指定测试应用是否真实关闭

## 4 自动测试用例

### 4.1 五类任务动作序列

| 任务 | 固定动作序列 | 自动测试结果 |
|---|---|---|
| 打开浏览器 | `Win+R` `msedge` `Enter` `finish` | 通过 |
| 搜索内容 | 定位地址栏 输入内容 `Enter` `finish` | 通过 |
| 打开文件 | `Win+R` 输入文件路径 `Enter` `finish` | 通过 |
| 发送消息 | 输入测试消息 `Enter` `finish` | 通过 |
| 关闭应用 | `Alt+F4` `finish` | 通过 |

这里的“通过”表示动作编排和执行闭环通过模拟后端验证，不表示真实桌面状态已经改变。

### 4.2 闭环和终止条件

| 测试类别 | 验证内容 | 结果 |
|---|---|---|
| 首次观察 | 截图和 UI 上下文参与规划 | 通过 |
| 连续观察 | 动作后重新截图 | 通过 |
| 历史反馈 | 动作 原因 参数和结果进入下一轮 | 通过 |
| 计划状态 | 按步骤编号更新状态 | 通过 |
| 正常结束 | `finish` 结束运行 | 通过 |
| 执行失败 | 输入后端失败时停止 | 通过 |
| 安全阻止 | 风险动作以 `blocked` 停止 | 通过 |
| 动作上限 | 达到上限时停止 | 通过 |

### 4.3 动作执行

| 动作 | 验证内容 | 结果 |
|---|---|---|
| `click` | 坐标映射和单击 | 通过 |
| `double_click` | 坐标映射和双击 | 通过 |
| `context_open` | 右键点击并立即按 Enter | 通过 |
| `type` | ASCII 输入和中文粘贴 | 通过 |
| `press` | 单键和重复按键 | 通过 |
| `hotkey` | 多键快捷键 | 通过 |
| `scroll` | 当前点和指定点滚动 | 通过 |
| `drag` | 起点终点映射和拖拽 | 通过 |
| `wait` | 等待时长限制 | 通过 |
| `finish` | 完成结果返回 | 通过 |

### 4.4 安全测试

| 编号 | 测试内容 | 预期结果 | 结果 |
|---|---|---|---|
| SF-01 | 截图坐标越界 | 拒绝动作 | 通过 |
| SF-02 | 动作参数缺失 | 返回失败 | 通过 |
| SF-03 | 等待超过上限 | 返回失败 | 通过 |
| SF-04 | 不支持的动作 | 返回失败 | 通过 |
| SF-05 | PowerShell 文本 | 安全阻止 | 通过 |
| SF-06 | CMD 文本 | 安全阻止 | 通过 |
| SF-07 | Python 模块命令 | 安全阻止 | 通过 |
| SF-08 | 项目自调用文本 | 安全阻止 | 通过 |
| SF-09 | 输入文本过长 | 安全阻止 | 通过 |
| SF-10 | PyAutoGUI FAILSAFE | 转换为失败结果 | 通过 |
| SF-11 | 未确认真实执行 | 取消运行 | 通过 |
| SF-12 | 发送消息缺少二次确认 | 拒绝执行 | 通过 |
| SF-13 | 左上角占位坐标 | 安全阻止 | 通过 |
| SF-14 | 右键动作混入键盘参数 | 拒绝执行 | 通过 |

## 5 第四周专项结果

测试文件：

```text
tests/test_executor.py
tests/test_runtime.py
tests/test_runtime_cli.py
tests/test_safety.py
tests/test_acceptance.py
tests/test_progress.py
tests/test_monitor.py
```

结果：

```text
76 passed in 0.54s
```

| 指标 | 结果 |
|---|---:|
| 收集用例 | 76 |
| 通过 | 76 |
| 失败 | 0 |
| 错误 | 0 |
| 通过率 | 100% |

## 6 第四周覆盖率

| 模块 | 有效语句 | 未覆盖 | 覆盖率 |
|---|---:|---:|---:|
| `runtime/__init__.py` | 4 | 0 | 100% |
| `runtime/acceptance.py` | 108 | 1 | 99% |
| `runtime/cli.py` | 93 | 3 | 97% |
| `runtime/executor.py` | 92 | 0 | 100% |
| `runtime/monitor.py` | 58 | 3 | 95% |
| `runtime/orchestrator.py` | 195 | 0 | 100% |
| `runtime/progress.py` | 46 | 1 | 98% |
| `runtime/safety.py` | 29 | 0 | 100% |
| **合计** | **625** | **8** | **99%** |

未覆盖语句主要是模块直接启动分支和悬浮窗退出异常分支，不影响主函数和命令行行为测试。

## 7 完整项目回归

```text
142 passed in 0.54s
总体语句覆盖率 93%
Ruff checks passed
```

新增系统没有破坏已有截图 感知 坐标控制 数据集处理 模型接口和基础 Agent 功能。

## 8 系统原型交付清单

项目大纲对第四周的要求是“集成前面的模块，实现智能体”。第四周核心交付物为能够运行的端到端系统原型 v1.0。

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

| 文件 | 作用 |
|---|---|
| `cli.py` | 模型驱动命令行入口 |
| `orchestrator.py` | 截图 规划 决策 执行和反馈闭环 |
| `executor.py` | 原子动作执行和坐标映射 |
| `safety.py` | 危险文本和危险坐标拦截 |
| `progress.py` | 实时进度记录 |
| `monitor.py` | 截图排除的同屏进度悬浮窗 |
| `acceptance.py` | 五类真实桌面任务验收入口 |

系统原型调用的前序模块：

```text
src/gui_agent/screen.py
src/gui_agent/perception.py
src/gui_agent/coordinates.py
src/gui_agent/control.py
src/gui_agent/overlay.py
src/gui_agent/agent/
src/gui_agent/models/
```

运行配置、项目入口和依赖：

```text
configs/agent-v1.example.toml
pyproject.toml
README.md
```

## 9 真实桌面验收指南

### 9.1 验收范围

真实验收覆盖以下五类任务：

1. 打开浏览器
2. 搜索指定内容
3. 打开指定文件
4. 向测试会话发送消息
5. 关闭测试应用

自动测试使用模拟后端，不会打开应用。以下命令会调用真实截图和 PyAutoGUI 输入控制。

### 9.2 安全准备

- 保存正在编辑的文件
- 关闭密码和支付页面
- 鼠标左上角保留为空
- 发送消息只使用自己的测试会话
- 关闭应用只使用无未保存内容的窗口
- 不建议添加 `--yes`

发生异常时将鼠标快速移到屏幕左上角，PyAutoGUI FAILSAFE 会停止动作。

### 9.3 通用流程

进入项目环境：

```bat
conda activate gui-agent
cd /d C:\Users\m1865\Desktop\GUI-agent
```

先预览任务：

```bat
python -m gui_agent.runtime.acceptance --task open-browser
```

预览会输出全部固定动作，但不会操作桌面。确认动作正确后添加 `--execute`。输入 `yes` 后有 5 秒时间切换到目标窗口。

### 9.4 打开浏览器

```bat
python -m gui_agent.runtime.acceptance --task open-browser --execute
```

准备状态：显示 Windows 桌面。

通过标准：Microsoft Edge 打开并显示窗口。

### 9.5 搜索指定内容

```bat
python -m gui_agent.runtime.acceptance --task search-content --query "GUI Agent" --execute
```

准备状态：打开浏览器，并在倒计时结束前让浏览器保持前台。

通过标准：浏览器显示 `GUI Agent` 的搜索结果。

### 9.6 打开指定文件

```bat
python -m gui_agent.runtime.acceptance --task open-file --file "C:\Users\m1865\Desktop\GUI-Agent-Test.txt" --execute
```

准备状态：指定文件已经存在，当前文件没有未保存修改。

通过标准：系统使用默认应用打开指定文件。

### 9.7 发送测试消息

```bat
python -m gui_agent.runtime.acceptance --task send-message --message "GUI Agent 测试消息" --confirm-send --execute
```

准备状态：打开自己的测试会话，并让消息输入框获得焦点。

通过标准：消息只出现在指定测试会话中。该任务必须同时提供 `--confirm-send`，避免误发到其他联系人。

### 9.8 关闭测试应用

```bat
python -m gui_agent.runtime.acceptance --task close-app --execute
```

准备状态：打开一个没有未保存内容的记事本窗口，并在倒计时结束前让它保持前台。

通过标准：测试窗口关闭，其他窗口不受影响。

### 9.9 运行记录

每次执行都会创建独立目录：

```text
artifacts/acceptance/任务名-运行时间/
├── step-00.png
├── step-01.png
├── ...
└── report.json
```

截图用于核对执行前后的桌面状态，`report.json` 保存计划、动作、参数、结果和运行状态。

## 10 模型驱动闭环验收

固定动作验收通过后，可以验证多模态模型闭环：

```bat
python -m gui_agent.runtime.cli --config configs\agent-v1.example.toml --goal "使用图形界面打开 Microsoft Edge 不要使用终端命令" --start-delay 8 --show-progress --execute
```

模型运行会执行截图、OCR、规划、原子动作、重新截图和反馈循环。右上角悬浮窗会显示当前阶段，并通过 Windows 接口从截图中排除。若无法启用截图排除，悬浮窗会自动退出。终端命令或项目自调用文本会被安全策略拒绝并记录为 `blocked`。

实时进度保存在：

```text
artifacts/runtime/运行时间/progress.jsonl
```

