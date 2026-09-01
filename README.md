# 基于多模态大模型的桌面 GUI 智能体开发与优化

Windows 多模态桌面 GUI 智能体原型。

## 当前目录

```text
GUI-agent/
├── src/                  核心系统代码
├── configs/              Agent 与 LoRA 示例配置
├── scripts/              一键 Demo 脚本
├── old/                  历史数据、测试、报告、权重和运行产物
├── pyproject.toml        依赖与命令行入口
├── .gitignore            Git 忽略规则
└── README.md             项目说明
```

## 核心能力

- 截图、OCR、UI 边界框、坐标映射和鼠标键盘控制。
- 任务规划、模型决策、动作 JSON 校验、安全策略与执行反馈闭环。
- 本地 Transformers、OpenAI 兼容 API、Qwen2.5-VL LoRA 微调接口。
- 浏览器搜索、候选网页筛选、页面信息采集和可追溯运行记录。


## 环境安装

```powershell
conda activate gui-agent
Set-Location D:\Desktop\GUI-agent
$env:PYTHONPATH = 'src'
python -m pip install -e ".[dev]"
```

如需数据预处理、本地模型或 LoRA 微调：

```powershell
python -m pip install -e ".[agent,datasets,finetune]"
```

本地 Qwen2.5-VL 模型路径由 `configs/agent-v2.example.toml` 和 `configs/finetune-lora.example.toml` 配置；如模型不在 `D:/Qwen2.5-VL-3B-Instruct`，请修改其中的 `path` 或 `model_path`。

## 常用命令

### 感知与标注

```powershell
$env:PYTHONPATH = 'src'
python -m gui_agent.cli inspect --output old\artifacts\screen.png
python -m gui_agent.cli overlay
```

### Agent 运行

预览模式不控制桌面：

```powershell
python -m gui_agent.runtime.cli --config configs\agent-v2.example.toml --goal "打开浏览器"
```

真实执行会控制当前桌面：

```powershell
python -m gui_agent.runtime.cli --config configs\agent-v2.example.toml --goal "打开浏览器" --execute
```

运行记录默认写入 `old\artifacts\runtime-v2\`。

### 第八周浏览器 Demo

默认模式运行归档测试、静态检查和动作预览，不操作桌面：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_demo_test.ps1
```

完整 Demo 会要求输入搜索主题，随后自动启动一次 Edge、搜索、筛选不同来源网页并采集信息：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_demo_test.ps1 -CaptureScreen -ExecuteDesktop -BrowsePages -PageCount 3 -PageDelay 6
```

结果写入 `old\artifacts\demo-tests\时间戳\`。真实执行前请关闭无关窗口；需要停止时，将鼠标移动到屏幕左上角，或在终端按 `Ctrl+C`。

### 评估与微调

```powershell
python -m gui_agent.evaluation.cli run
python -m gui_agent.finetune.cli train --config configs\finetune-lora.example.toml
python -m gui_agent.finetune.cli evaluate --config configs\finetune-lora.example.toml --dataset old\data\finetune\validation.jsonl --output old\artifacts\week5\finetuned.jsonl --adapter old\models\gui-agent-lora\adapter
```

第七周 `18/20` 的结果来自固定输入和模拟后端的可控基准，不代表真实桌面或开放网页环境的泛化成功率。

## 测试

```powershell
$env:PYTHONPATH = 'src'
python -m pytest -q old\tests
python -m ruff check src old\tests
```

最近一次完整自动化回归记录为 `172 passed`，静态检查通过。真实桌面、浏览器弹窗和在线页面仍会受操作系统、网络和页面更新影响。

## 安全说明

- 原始数据、模型权重、截图、日志和报告已归档，不应随意删除。
- API 密钥只通过环境变量配置，不要写入配置文件或提交到 Git。
- 真实执行仅应在无敏感内容的测试环境中进行。
- 系统具有终端文本、坐标保护和动作限制，但不能替代人工确认。
