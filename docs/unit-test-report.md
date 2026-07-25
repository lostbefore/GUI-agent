# 桌面 GUI 智能体完整单元测试报告

## 1. 基本信息

| 项目 | 内容 |
|---|---|
| 项目 | 基于多模态大模型的桌面 GUI 智能体开发与优化 |
| 测试范围 | 阶段一桌面感知控制 + 阶段二数据处理与 Agent 框架 |
| 测试日期 | 2026-07-25 |
| 操作系统 | Windows 11（10.0.26200） |
| Conda 环境 | `gui-agent` |
| Python | 3.10.20 |
| pytest | 9.1.1 |
| pytest-cov | 7.1.0 |
| 总用例数 | 57 |
| 通过率 | 100% |
| 总体语句覆盖率 | 89% |

## 2. 测试目标

验证以下核心能力：

1. 多分辨率坐标转换和边界框处理；
2. 鼠标键盘控制及越界保护；
3. 全屏、区域截图、缩放和色彩转换；
4. OCR 结果转换、UI 区域检测、标注绘制和保存；
5. ScreenAgent、WebArena、Mind2Web 数据预处理；
6. 多模态 Agent 任务拆解、计划生成和动作决策；
7. OpenAI-compatible API 请求与本地模型配置；
8. 阶段一、阶段二命令行入口及包级懒加载接口。

## 3. 测试分类

| 测试文件 | 用例数 | 测试内容 | 结果 |
|---|---:|---|---|
| `tests/test_cli.py` | 4 | 阶段一检测与覆盖层 CLI | 通过 |
| `tests/test_control.py` | 10 | 点击、输入、按键、滚动、拖拽、越界保护 | 通过 |
| `tests/test_coordinates.py` | 5 | 坐标映射、边界框、归一化和参数校验 | 通过 |
| `tests/test_package.py` | 2 | 包公共接口懒加载与异常 | 通过 |
| `tests/test_perception.py` | 10 | OCR、UI 检测、分析、绘制和图片保存 | 通过 |
| `tests/test_screen.py` | 7 | 全屏/区域截图、缩放、裁剪和非法参数 | 通过 |
| `tests/test_agent.py` | 6 | JSON 解析、任务计划状态归一、动作决策和动作白名单 | 通过 |
| `tests/test_datasets.py` | 6 | 三套数据集预处理、官方 ScreenAgent 格式和异常 | 通过 |
| `tests/test_models.py` | 4 | 图片编码、API 请求、连接异常和模型配置 | 通过 |
| `tests/test_phase2_cli.py` | 3 | 数据处理 CLI 和 Agent CLI | 通过 |
| **合计** | **57** | 阶段一与阶段二核心代码 | **全部通过** |

## 4. 阶段二重点用例

### 4.1 数据集预处理

| 编号 | 验证内容 | 预期结果 | 结果 |
|---|---|---|---|
| DS-01 | 统一数据结构序列化与必填字段校验 | 合法记录输出 JSON，空指令抛出异常 | 通过 |
| DS-02 | WebArena `config_files` 解析 | 任务意图、站点和任务编号正确转换 | 通过 |
| DS-03 | Mind2Web 动作与候选元素解析 | CLICK、目标节点和 split 正确转换 | 通过 |
| DS-04 | ScreenAgent JSON 和文本 session | 两种 session 均生成统一记录 | 通过 |
| DS-05 | ScreenAgent 官方时间戳格式 | `task_prompt_en`、`saved_image_name` 和多步记录按 session 聚合 | 通过 |
| DS-06 | 不支持的数据集和不存在路径 | 分别抛出 `ValueError`、`FileNotFoundError` | 通过 |

### 4.2 Agent 与规划器

| 编号 | 验证内容 | 预期结果 | 结果 |
|---|---|---|---|
| AG-01 | Markdown 围栏及混合文本中的 JSON | 正确提取 JSON 对象 | 通过 |
| AG-02 | 最大计划步骤限制 | 超出部分被截断，状态默认为 pending | 通过 |
| AG-03 | 空目标与无步骤响应 | 抛出明确的 `ValueError` | 通过 |
| AG-04 | 根据截图生成点击决策 | 返回动作、坐标参数和原因 | 通过 |
| AG-05 | 非法模型动作 | 被动作白名单拒绝 | 通过 |
| AG-06 | 模型错误返回已完成状态 | 计划执行前统一重置为 pending | 通过 |

### 4.3 模型接口与配置

| 编号 | 验证内容 | 预期结果 | 结果 |
|---|---|---|---|
| MD-01 | 本地图片和远程图片 URL | 本地图片转 Data URL，远程 URL 保持不变 | 通过 |
| MD-02 | OpenAI-compatible 多模态请求 | system/user 消息、图片和认证头正确 | 通过 |
| MD-03 | API 无法连接 | 转换为包含原因的 `RuntimeError` | 通过 |
| MD-04 | TOML 配置构造模型后端 | API、本地 Transformers 正确构造，未知后端被拒绝 | 通过 |

### 4.4 命令行入口

| 编号 | 验证内容 | 预期结果 | 结果 |
|---|---|---|---|
| CLI2-01 | `gui-agent-data` | 参数正确传入预处理器并报告记录数 | 通过 |
| CLI2-02 | `gui-agent-run` 仅规划 | 输出 JSON 任务计划 | 通过 |
| CLI2-03 | `gui-agent-run` 带截图 | 输出任务计划及下一步动作 | 通过 |

## 5. 执行结果

```text
.........................................................                [100%]
57 passed in 1.01s
```

| 指标 | 结果 |
|---|---:|
| 收集用例 | 57 |
| 通过 | 57 |
| 失败 | 0 |
| 错误 | 0 |
| 跳过 | 0 |
| 通过率 | 100% |

## 6. 代码覆盖率

| 模块 | 有效语句 | 未覆盖 | 覆盖率 |
|---|---:|---:|---:|
| `gui_agent/__init__.py` | 11 | 0 | 100% |
| `gui_agent/agent/__init__.py` | 3 | 0 | 100% |
| `gui_agent/agent/cli.py` | 21 | 1 | 95% |
| `gui_agent/agent/config.py` | 17 | 0 | 100% |
| `gui_agent/agent/core.py` | 39 | 6 | 85% |
| `gui_agent/agent/json_utils.py` | 22 | 2 | 91% |
| `gui_agent/agent/planner.py` | 31 | 1 | 97% |
| `gui_agent/cli.py` | 29 | 1 | 97% |
| `gui_agent/control.py` | 45 | 0 | 100% |
| `gui_agent/coordinates.py` | 53 | 0 | 100% |
| `gui_agent/datasets/__init__.py` | 3 | 0 | 100% |
| `gui_agent/datasets/cli.py` | 17 | 1 | 94% |
| `gui_agent/datasets/preprocessors.py` | 141 | 9 | 94% |
| `gui_agent/datasets/schema.py` | 31 | 2 | 94% |
| `gui_agent/models/__init__.py` | 4 | 0 | 100% |
| `gui_agent/models/base.py` | 12 | 0 | 100% |
| `gui_agent/models/openai_compatible.py` | 52 | 4 | 92% |
| `gui_agent/models/transformers_local.py` | 58 | 38 | 34% |
| `gui_agent/overlay.py` | 28 | 18 | 36% |
| `gui_agent/perception.py` | 80 | 1 | 99% |
| `gui_agent/screen.py` | 44 | 0 | 100% |
| **总计** | **741** | **84** | **89%** |

本地 Transformers 推理和 PyQt5 绘制事件依赖重量级模型/GPU 及 Qt 事件循环，单元测试主要覆盖其配置和外围接口；真实模型加载与截图推理另以集成验收覆盖，其余核心业务模块均达到较高覆盖率。

## 7. 本地模型集成验收

以下结果不计入 57 个隔离单元测试，但用于确认真实硬件和模型链路：

| 检查项 | 实测结果 |
|---|---|
| GPU | NVIDIA GeForce RTX 5060 Laptop GPU，CUDA 可用 |
| PyTorch | 2.13.0+cu130 |
| Transformers | 5.14.1 |
| bitsandbytes | 0.50.0，CUDA 4-bit 后端可用 |
| 本地模型 | `D:\Qwen-VL`，Qwen2.5-VL-3B-Instruct |
| 量化配置 | NF4 4-bit、BF16 计算、双重量化 |
| 纯文本任务规划 | 成功输出 6 步有效 JSON 计划 |
| ScreenAgent 截图推理 | 成功识别错误代码并输出 `type` 动作 |
| 单次多模态命令耗时 | 约 27 秒（含模型加载、规划和动作决策） |

结论：8GB 显存可以按当前配置本地部署并运行该 3B 视觉语言模型，未发生显存溢出。

## 8. 安装与入口验证

项目已通过 editable 构建及安装：

```text
Successfully built desktop-gui-agent
Successfully installed desktop-gui-agent-0.1.0
```

以下入口均已执行 `--help` 并正常返回：

```text
gui-agent
gui-agent-data
gui-agent-run
```

## 9. 静态检查

```text
ruff check .
All checks passed!

ruff format --check .
35 files already formatted

python -m compileall -q src tests
通过

git diff --check
通过
```

## 10. 测试结论

本轮重新检查后共执行 57 个自动化测试，全部通过，通过率为 100%，总体语句覆盖率为 89%。阶段一桌面感知控制模块和阶段二数据处理、任务规划、模型 API、命令行框架均达到当前设计预期。

复查过程中已修复以下问题：

1. `.gitignore` 误忽略 `src/gui_agent/models` 源码；
2. Python 3.10 缺少内置 `tomllib` 的兼容问题；
3. ScreenAgent 官方 `task_prompt`、`saved_image_name` 和时间戳记录格式未被完整解析的问题；
4. 阶段二新增 CLI 未纳入覆盖率的问题；
5. 本地 Transformers `device_map="auto"` 缺少 `accelerate` 依赖的问题。
6. 8GB 显存本地模型需要 4-bit 量化和视觉像素上限的问题；
7. 模型偶尔把尚未执行的计划步骤标为 `completed`，现已统一归一为 `pending`；
8. Mind2Web 原结果仅包含训练集，现已补齐并验证四个划分共 2350 条记录。

本次完整单元测试结论为通过。

## 11. 复现命令

```powershell
python -m pytest -q `
  --cov=gui_agent `
  --cov-report=term-missing `
  --cov-report=html:artifacts/coverage `
  --cov-report=xml:artifacts/coverage.xml `
  --html=artifacts/unit-test-report.html `
  --self-contained-html `
  --junitxml=artifacts/junit.xml

python -m ruff check .
python -m ruff format --check .
python -m compileall -q src tests
```
