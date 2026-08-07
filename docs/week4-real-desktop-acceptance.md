# 第四周真实桌面验收指南

## 1 验收范围

本指南验证以下五类真实桌面任务：

1. 打开浏览器
2. 搜索指定内容
3. 打开指定文件
4. 向测试会话发送消息
5. 关闭测试应用

自动单元测试使用模拟后端，不会打开应用。这里的验收命令会调用真实截图和 PyAutoGUI 输入控制。

## 2 安全准备

- 保存正在编辑的文件
- 关闭密码和支付页面
- 鼠标左上角保留为空
- 发送消息只使用自己的测试会话
- 关闭应用只使用无未保存内容的窗口
- 不建议添加 `--yes`

发生异常时把鼠标快速移到屏幕左上角，PyAutoGUI FAILSAFE 会停止动作。

## 3 通用流程

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

## 4 五项任务

### 4.1 打开浏览器

```bat
python -m gui_agent.runtime.acceptance --task open-browser --execute
```

准备状态：显示 Windows 桌面。

通过标准：Microsoft Edge 打开并显示窗口。

### 4.2 搜索指定内容

```bat
python -m gui_agent.runtime.acceptance --task search-content --query "GUI Agent" --execute
```

准备状态：打开浏览器，并在倒计时结束前让浏览器保持前台。

通过标准：浏览器显示 `GUI Agent` 的搜索结果。

### 4.3 打开指定文件

```bat
python -m gui_agent.runtime.acceptance --task open-file --file "C:\Users\m1865\Desktop\GUI-Agent-Test.txt" --execute
```

准备状态：指定文件已经存在，当前文件没有未保存修改。

通过标准：系统使用默认应用打开指定文件。

### 4.4 发送测试消息

```bat
python -m gui_agent.runtime.acceptance --task send-message --message "GUI Agent 测试消息" --confirm-send --execute
```

准备状态：打开自己的测试会话，并让消息输入框获得焦点。

通过标准：消息只出现在指定测试会话中。

该任务必须同时提供 `--confirm-send`，避免误发到其他联系人。

### 4.5 关闭测试应用

```bat
python -m gui_agent.runtime.acceptance --task close-app --execute
```

准备状态：打开一个没有未保存内容的记事本窗口，并在倒计时结束前让它保持前台。

通过标准：测试窗口关闭，其他窗口不受影响。

## 5 运行记录

每次执行都会创建独立目录：

```text
artifacts/acceptance/任务名-运行时间/
├── step-00.png
├── step-01.png
├── ...
└── report.json
```

截图用于核对执行前后的桌面状态，`report.json` 保存计划、动作、参数、结果和运行状态。

## 6 模型闭环验收

固定动作验收通过后，可以验证多模态模型闭环：

```bat
python -m gui_agent.runtime.cli --config configs\agent-v1.example.toml --goal "使用图形界面打开 Microsoft Edge 不要使用终端命令" --start-delay 8 --show-progress --execute
```

模型运行会执行截图、OCR、规划、原子动作、重新截图和反馈循环。右上角悬浮窗会显示当前处于截图识别、任务规划、动作决策、桌面执行或结束阶段。悬浮窗设置为鼠标穿透，并通过 Windows 接口从截图中排除；如果系统无法启用截图排除，悬浮窗会自动退出。终端命令或项目自调用文本会被安全策略拒绝，并在报告中记录为 `blocked`。

实时进度同时保存在：

```text
artifacts/runtime/运行时间/progress.jsonl
```
