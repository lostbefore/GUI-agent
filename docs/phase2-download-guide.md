# 阶段二下载、放置与运行指南

## 1. 你与代码各自负责什么

### 已由项目代码完成

- ScreenAgent、WebArena、Mind2Web 三种原始格式到统一 JSONL 的预处理器；
- 基础多模态 Agent、JSON 行为协议和任务规划器；
- OpenAI-compatible HTTP API 后端；
- Hugging Face Transformers 本地推理后端；
- LangChain `Runnable` 适配入口；
- 配置样例、命令行工具和自动化测试。

### 当前机器上的完成状态（2026-07-25）

- ScreenAgent 已直接克隆到 `C:\Users\m1865\Desktop\ScreenAgent`；
- WebArena 已直接克隆到 `C:\Users\m1865\Desktop\webarena`；
- Mind2Web 已直接克隆到 `C:\Users\m1865\Desktop\Mind2Web`，训练集和三个测试划分均已解压；
- Qwen2.5-VL-3B-Instruct 已下载到 `D:\Qwen-VL`；
- 继续使用已有 Conda 环境 `gui-agent`，无需再创建虚拟环境；
- 三个数据集均已生成预处理文件；
- Qwen 已在 RTX 5060 Laptop 8GB 上以 4-bit 量化完成纯文本规划和截图动作推理。

## 2. 准备目录与 Python 环境

打开 Anaconda PowerShell Prompt，在项目根目录执行：

```powershell
conda activate gui-agent
Set-Location C:\Users\m1865\Desktop\GUI-agent
python -m pip install -e . --no-deps
```

确认当前解释器确实来自该环境：

```powershell
python -c "import sys; print(sys.executable)"
```

预期输出为：

```text
D:\Anaconda\envs\gui-agent\python.exe
```

如果没有先激活环境，后续命令中的 `python` 可直接替换成完整解释器路径。

## 3. 下载 ScreenAgent

官方仓库：<https://github.com/niuzaisheng/ScreenAgent>

当前采用“仓库保留在桌面、不复制到项目”的方式。确认：

```text
C:\Users\m1865\Desktop\ScreenAgent\data\ScreenAgent\train
C:\Users\m1865\Desktop\ScreenAgent\data\ScreenAgent\test
```

需要重新生成时执行：

```powershell
gui-agent-data screenagent `
  --input C:\Users\m1865\Desktop\ScreenAgent\data `
  --output data/processed/screenagent.jsonl
```

首次验证可只处理 10 条：

```powershell
gui-agent-data screenagent --input C:\Users\m1865\Desktop\ScreenAgent\data `
  --output data/processed/screenagent-sample.jsonl --limit 10
```

ScreenAgent 官方仓库声明代码采用 MIT License、数据集采用 Apache-2.0。

## 4. 下载 WebArena

官方仓库：<https://github.com/web-arena-x/webarena>

仓库保留在桌面。确认以下目录存在：

```text
C:\Users\m1865\Desktop\webarena\config_files
```

处理命令：

```powershell
gui-agent-data webarena `
  --input C:\Users\m1865\Desktop\webarena `
  --output data/processed/webarena.jsonl
```

WebArena 的完整自托管环境包括多个网站和 Docker 镜像，体积和部署成本较高。本阶段交付物只需要任务配置数据，因此暂时不必部署整套环境。

## 5. 下载 Mind2Web

官方仓库：<https://github.com/OSU-NLP-Group/Mind2Web>

Hugging Face 数据集：<https://huggingface.co/datasets/osunlp/Mind2Web>

仓库保留在桌面。当前目录中已有 LFS 数据、`test.zip`、训练集和三个已解压的测试划分。训练集包含：

```text
C:\Users\m1865\Desktop\Mind2Web\data\train\train_*.json
```

Mind2Web 测试集由官方单独提供。打开官方 GitHub README 中的 “Dataset Access”，下载测试压缩包，使用官方给出的密码 `mind2web` 解压，并放成：

```text
C:\Users\m1865\Desktop\Mind2Web\data\test_task\test_task_*.json
C:\Users\m1865\Desktop\Mind2Web\data\test_website\test_website_*.json
C:\Users\m1865\Desktop\Mind2Web\data\test_domain\test_domain_*.json
```

官方要求不要在线重新发布解压后的测试数据。因此这些文件只能保存在本地，也不要提交到 Git。

处理命令：

```powershell
gui-agent-data mind2web `
  --input C:\Users\m1865\Desktop\Mind2Web `
  --output data/processed/mind2web.jsonl
```

本阶段只做任务/动作序列预处理时，不必下载体积更大的 `raw_dump`。只有在后续需要原始网页截图、DOM snapshot、HAR 或 Playwright trace 时，才需要按 Mind2Web 官方说明下载 raw dump。

## 6. 检查预处理结果

当前已生成：

```text
data/processed/screenagent.jsonl
data/processed/webarena.jsonl
data/processed/webarena-sample.jsonl
data/processed/mind2web.jsonl
```

查看前两行：

```powershell
Get-Content data/processed/mind2web.jsonl -TotalCount 2
```

统一记录格式：

```json
{
  "dataset": "mind2web",
  "task_id": "...",
  "split": "train",
  "instruction": "...",
  "steps": [
    {"action": "click", "target": "42", "value": "", "image": null, "metadata": {}}
  ],
  "images": [],
  "metadata": {"website": "..."}
}
```

## 7. 选择多模态模型

只需选择一种方案即可。建议先使用 Qwen2.5-VL-3B 验证流程。

### 方案 A：本地 Qwen2.5-VL-3B（当前已采用）

官方模型：<https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct>

模型目录为 `D:\Qwen-VL`。`configs/agent-local.example.toml` 已配置为 4-bit
NF4 量化、BF16 计算及最大 1024×1024 视觉像素量，适配 8GB 显存。

### 方案 B：本地 GLM-4V-9B

官方模型：<https://huggingface.co/zai-org/glm-4v-9b>

```powershell
hf download zai-org/glm-4v-9b --local-dir models/glm-4v-9b
```

GLM-4V 官方加载方式需要 `trust_remote_code=True`，模型也比 3B 模型占用更多显存。建议优先将它部署为 OpenAI-compatible 服务，再使用项目的 API 后端；如直接加载，需要根据官方模型卡使用其自定义 `AutoModel.chat` 接口。

### 方案 C：本地 Llama 3.2 Vision 11B

官方模型：<https://huggingface.co/meta-llama/Llama-3.2-11B-Vision-Instruct>

该模型需要在 Hugging Face 页面登录并接受 Meta Llama 3.2 许可，然后执行：

```powershell
hf auth login
hf download meta-llama/Llama-3.2-11B-Vision-Instruct `
  --local-dir models/Llama-3.2-11B-Vision-Instruct
```

其模型卡说明视觉输入主要支持英文，且 11B 模型对显存要求明显高于 Qwen 3B。

### 方案 D：调用已有 API（不下载模型）

如果已有 vLLM、SGLang、LMDeploy 或云端 OpenAI-compatible 地址，只需编辑：

```text
configs/agent-api.example.toml
```

关键字段：

```toml
[model]
backend = "openai_compatible"
name = "服务端模型名称"
base_url = "http://127.0.0.1:8000/v1"
api_key_env = "GUI_AGENT_API_KEY"
```

如服务需要密钥：

```powershell
$env:GUI_AGENT_API_KEY = "你的密钥"
```

不要把真实密钥写入 TOML、源码或 Git。

## 8. 运行基础 Agent

先激活环境并进入项目：

```powershell
conda activate gui-agent
Set-Location C:\Users\m1865\Desktop\GUI-agent
```

仅生成任务计划：

```powershell
python -m gui_agent.agent.cli `
  --config configs\agent-local.example.toml `
  --goal "打开记事本并输入 hello"
```

同时让模型根据截图选择下一步动作：

```powershell
python -m gui_agent.agent.cli `
  --config configs\agent-local.example.toml `
  --goal "Find the wrong line of code and fix it" `
  --screenshot "C:\Users\m1865\Desktop\ScreenAgent\data\ScreenAgent\test\08a2def941d942ffb542ba0ba3d8aa99\images\2024-01-13_21-34-31-146954.jpg"
```

实测该截图会输出一个 `type` 动作，并识别出需要输入的修正代码。当前基础 Agent
只输出动作决策，不会自动执行鼠标键盘操作，这是阶段二的安全边界。

```json
{
  "action": "click",
  "reason": "搜索框位于页面顶部",
  "parameters": {"x": 620, "y": 180}
}
```

允许的动作包括 `click`、`double_click`、`type`、`press`、`hotkey`、`scroll`、`drag`、`wait` 和 `finish`。

## 9. LangChain 接口

```python
from gui_agent.agent import DesktopAgent
from gui_agent.agent.config import build_model, load_config

model = build_model(load_config("configs/agent-local.example.toml"))
agent = DesktopAgent(model)
runnable = agent.as_langchain_runnable()
plan = runnable.invoke({"goal": "打开设置并查看显示分辨率"})
print(plan)
```

## 10. 当前验收结果

- [x] ScreenAgent 桌面仓库存在，预处理结果约 1.5 MB；
- [x] WebArena 桌面仓库存在，完整预处理结果约 525 KB；
- [x] Mind2Web 桌面仓库存在，2350 条全量预处理结果约 9.52 GB；
- [x] `D:\Qwen-VL` 的两份模型权重完整存在；
- [x] RTX 5060 Laptop 8GB 可用，PyTorch 已识别 CUDA；
- [x] Qwen 4-bit 本地任务规划成功；
- [x] Qwen 4-bit 截图理解和动作 JSON 输出成功；
- [x] 自动化测试与 Ruff 静态检查通过；
- [x] 原始数据、预处理数据和模型目录均被 `.gitignore` 排除。

阶段二交付物已具备。下一开发阶段可将 `AgentDecision` 映射到阶段一的
`InputController`，加入执行前确认、坐标映射、失败重试和最大步数限制，形成受控的
“截图 → 规划 → 决策 → 执行 → 再截图”闭环。
