# 基于多模态大模型的桌面 GUI 智能体开发与优化

桌面 GUI 智能体原型，覆盖屏幕感知、OCR 与 UI 定位、鼠标键盘控制、公开数据集预处理、多模态任务规划、模型调用、LoRA 微调、执行闭环、鲁棒性优化与系统评估。

## 项目结构

    src/gui_agent/
    ├── screen.py          截图与分辨率适配
    ├── perception.py      OCR 与界面识别
    ├── control.py         鼠标键盘控制
    ├── coordinates.py     坐标映射
    ├── datasets/          数据集预处理
    ├── agent/             任务规划与决策
    ├── models/            本地与 API 模型
    ├── finetune/          LoRA 微调
    ├── runtime/           执行闭环与安全策略
    └── evaluation/        任务评估与图表

    configs/               示例配置
    data/week7/            20 项评估任务
    tests/                 自动化测试
    docs/                  阶段说明与报告

## 阶段交付物

| 周次 | 交付物 | 路径 |
|---|---|---|
| 第 2 周 | 感知与控制代码、单元测试 | src/gui_agent/、tests/ |
| 第 3 周 | 数据预处理、基础 Agent | src/gui_agent/datasets/、src/gui_agent/agent/、src/gui_agent/models/ |
| 第 4 周 | 系统原型、基础任务报告 | src/gui_agent/runtime/、docs/week4-basic-task-report.md |
| 第 5 周 | LoRA 微调、对比报告 | src/gui_agent/finetune/、week5-finetune-analysis-report.md |
| 第 6 周 | 系统 v2.0、鲁棒性报告 | configs/agent-v2.example.toml、week6-robustness-test-report.md |
| 第 7 周 | 全面评估、性能图表 | src/gui_agent/evaluation/、week7-system-evaluation-report.md、artifacts/week7/charts/ |
| 第 8 周 | 工程整理与作品集整合 | 进行中 |

## 安装

    conda activate gui-agent
    Set-Location D:DesktopGUI-agent
    $env:PYTHONPATH='src'
    python -m pip install -e ".[dev]"

按需安装模型、数据集和微调依赖：

    python -m pip install -e ".[agent,datasets,finetune]"

## 常用命令

屏幕感知：

    python -m gui_agent.cli inspect --output artifactsscreen.png
    python -m gui_agent.cli overlay

数据集预处理：

    python -m gui_agent.datasets.cli screenagent --input <数据目录> --output dataprocessedscreenagent.jsonl
    python -m gui_agent.datasets.cli webarena --input <数据目录> --output dataprocessedwebarena.jsonl
    python -m gui_agent.datasets.cli mind2web --input <数据目录> --output dataprocessedmind2web.jsonl

智能体预览模式不会控制桌面：

    python -m gui_agent.runtime.cli --config configsagent-v2.example.toml --goal "打开浏览器"

真实执行会控制当前桌面，需显式确认：

    python -m gui_agent.runtime.cli --config configsagent-v2.example.toml --goal "打开浏览器" --execute

系统评估：

    python -m gui_agent.evaluation.cli run --tasks dataweek7enchmark-tasks.json --output-dir artifactsweek7 --report week7-system-evaluation-report.md

第七周的 90.0% 成功率来自 controlled 可控基准模式，不代表真实桌面或模型泛化性能。

## 测试

    $env:PYTHONPATH='src'
    python -m pytest -q
    python -m ruff check src tests

## 本地数据与模型

原始数据、处理结果、模型权重和运行产物被 .gitignore 排除，不应提交到代码仓库。API 密钥仅使用环境变量配置。