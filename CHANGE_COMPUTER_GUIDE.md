# 换电脑使用指南

这份指南用于在 Mac / Windows 之间同步 Subtitle Studio 项目，并在新电脑上快速继续开发和使用。

## 1. 当前电脑：先推送到远程仓库

第一次使用前，需要先在 GitHub / Gitee / GitLab 创建一个空仓库。

然后在当前项目目录运行：

```powershell
git remote add origin https://github.com/你的用户名/subtitle-studio.git
git push -u origin main
```

以后每次改完代码，运行：

```powershell
git status
git add .
git commit -m "更新说明"
git push
```

## 2. 新 Windows 电脑：克隆并启动

```powershell
git clone https://github.com/你的用户名/subtitle-studio.git
cd subtitle-studio

Copy-Item .env.example .env
notepad .env

py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
py app.py
```

打开：

```text
http://127.0.0.1:8765/
```

## 3. 新 Mac 电脑：克隆并启动

```bash
git clone https://github.com/你的用户名/subtitle-studio.git
cd subtitle-studio

cp .env.example .env
open -e .env

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

打开：

```text
http://127.0.0.1:8765/
```

## 4. `.env` 里需要填写什么

把 `.env.example` 复制成 `.env` 后，填写自己的 DeepSeek API Key：

```text
DEEPSEEK_API_KEY=你的DeepSeekKey
PORT=8765
```

注意：`.env` 不会被 Git 同步，这是为了保护 API Key。

## 5. 两台电脑之间日常同步

每次开始开发前，先拉取最新代码：

```bash
git pull
```

改完并测试后，提交并推送：

```bash
git status
git add .
git commit -m "更新说明"
git push
```

另一台电脑继续使用时，再运行：

```bash
git pull
```

## 6. 哪些东西会同步，哪些不会同步

会同步：

- `app.py`
- `transcript_tool.py`
- `static/`
- `tests/`
- `requirements.txt`
- README 和使用说明

不会同步：

- `.env`
- `output/`
- `__pycache__/`
- 本地导出的 PDF / DOCX / 音频
- 本地临时文件

如果希望导出的精读稿、PDF、DOCX 也在两台电脑同步，建议把 `output/` 放到 OneDrive、iCloud Drive、坚果云等云盘目录里。

## 7. 常见问题

### 启动时报 DeepSeek Key 不存在

检查 `.env` 是否存在，并确认里面有：

```text
DEEPSEEK_API_KEY=你的DeepSeekKey
```

### 端口被占用

可以修改 `.env`：

```text
PORT=8766
```

然后重新启动：

```bash
python app.py
```

或 Windows：

```powershell
py app.py
```

### Git 提示有冲突

先不要乱删文件。常用处理流程：

```bash
git status
```

打开提示冲突的文件，保留正确内容，然后：

```bash
git add .
git commit -m "Resolve sync conflict"
git push
```

