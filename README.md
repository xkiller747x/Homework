# 作业批改系统

这是一个使用 Python 编写的自动作业批改示例项目。系统会递归扫描 `file` 文件夹中的作业文件，读取其中的 `.docx` 内容，并逐份调用千问大模型进行评分，最后把结果写入 `result.txt`。

## 运行环境

运行本项目建议准备以下环境：

- Python 3.10 及以上版本
- Windows、macOS 或 Linux 任一常见操作系统
- 可正常访问千问接口的网络环境
- 一个可用的阿里云 DashScope / 通义千问 API Key
- 如果需要批改 `.doc` 文件，建议在 Windows 环境下安装 Microsoft Word

本项目当前只使用 Python 标准库，不依赖额外第三方包，因此通常不需要单独执行 `pip install`。不过需要注意：

- `.docx` 文件可直接读取
- `.doc` 文件当前通过 Windows 下的 Word 自动化方式读取
- 如果没有安装 Microsoft Word，则 `.doc` 文件会读取失败，但 `.docx` 文件仍可正常批改

你可以先用下面命令确认 Python 是否安装成功：

```bash
python --version
```

## 项目结构

```text
Homework/
├─ file/                     # 存放待批改作业，可继续嵌套子文件夹
├─ prompts/
│  └─ grading_prompt.txt     # 单独存放的评分提示词
├─ main.py                   # 主程序入口
├─ model.py                  # 千问模型调用逻辑
├─ utils.py                  # 文件递归搜索与 Word 读取逻辑
└─ README.md
```

## 功能说明

- `main.py`
  - 从环境变量读取 `API_KEY`。
  - 递归读取 `file` 文件夹中的作业。
  - 对每份作业单独调用一次大模型批改。
  - 将结果按 `作业文件名 分数` 的格式写入 `result.txt`。

- `model.py`
  - 负责读取独立的提示词文件。
  - 调用千问接口进行评分。
  - 从模型返回结果中提取 `0-100` 之间的分数。

- `utils.py`
  - 递归搜索 `file` 文件夹下的所有文件。
  - 读取 `.docx` 作业内容。
  - 在 Windows 环境下尝试读取 `.doc` 作业内容。
  - 其他文件会被识别但不会参与批改。

## 使用方法

### 1. 配置 API Key

为了避免把密钥直接写进代码，项目默认从环境变量 `DASHSCOPE_API_KEY` 中读取 API Key。

Windows PowerShell 可临时执行：

```powershell
$env:DASHSCOPE_API_KEY="你的真实 DashScope API Key"
```

如果你希望长期生效，可执行：

```powershell
[System.Environment]::SetEnvironmentVariable("DASHSCOPE_API_KEY", "你的真实 DashScope API Key", "User")
```

macOS / Linux 终端可执行：

```bash
export DASHSCOPE_API_KEY="你的真实 DashScope API Key"
```

你也可以先检查环境变量是否配置成功：

```bash
python -c "import os; print(bool(os.getenv('DASHSCOPE_API_KEY')))"
```

### 2. 准备作业文件

把学生作业放到 `file` 文件夹中，支持继续放在更深层的子文件夹中，例如：

```text
file/
├─ 班级A/
│  ├─ 学生1.docx
│  └─ 学生2.docx
└─ 班级B/
   └─ 第一组/
      └─ 学生3.docx
```

### 3. 运行程序

在项目根目录执行：

```bash
python main.py
```

如果你要测试模型连通性，也可以执行：

```bash
python test.py
```

### 4. 查看结果

程序运行后会在根目录生成或更新 `result.txt`，内容示例：

```text
学生1.docx 92
学生2.docx 85
学生3.docx 78
```

## 提示词说明

提示词被单独存放在 `prompts/grading_prompt.txt` 中，当前先放了一个测试版本，并包含以下关键约束：

- 要求模型只进行评分
- 明确规定“只返回一个 0-100 间的评分”
- 不返回任何解释或多余文本

如果后续想调整评分标准，只需要直接修改该提示词文件即可，`model.py` 会自动读取最新内容。

## 注意事项

- 当前版本支持 `.docx`，并在 Windows + Microsoft Word 环境下支持 `.doc`。
- 如果 `file` 目录下包含其他类型文件，程序会自动跳过，并在终端中提示。
- 如果存在 `.doc` 文件但本机未安装 Microsoft Word，这些文件会读取失败并在终端中提示。
- 如果模型接口调用失败，程序会在终端打印失败原因，已成功的作业结果仍会写入 `result.txt`。
- 为了保证每份作业都独立评分，程序会在循环中逐份调用一次大模型接口。
- 建议不要把真实 API Key 直接写进代码或提交到 Git 仓库。
