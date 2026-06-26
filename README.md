# Subtitle Studio

一个本地运行的 YouTube 字幕抓取和双语跟读稿生成工具。你可以粘贴单个视频、频道或播放列表链接，抓取字幕，并导出 `txt`、`json` 和适合跟读的双语文本。

## 安装

```powershell
py -m pip install -r requirements.txt
```

如果需要自动翻译成中文，可以在本机设置 DeepSeek API Key：

```powershell
$env:DEEPSEEK_API_KEY="你的 key"
```

也可以在项目根目录创建 `.env`：

```text
DEEPSEEK_API_KEY=你的 key
```

不设置也可以使用，网站会只抓取原文字幕。

## 启动网站

```powershell
py app.py
```

然后打开：

```text
http://127.0.0.1:8765
```

## 命令行用法

```powershell
py fetch_transcript.py "https://www.youtube.com/watch?v=VIDEO_ID" --no-translate
py fetch_transcript.py "https://www.youtube.com/playlist?list=PLAYLIST_ID" --limit 5 --output output
```

## 输出文件

每个视频会生成在 `output/<video_id>/`：

- `transcript.txt`：原文逐行字幕
- `transcript_zh.txt`：中文翻译逐行字幕，有翻译时生成
- `practice_bilingual.txt`：带时间轴的双语跟读稿
- `transcript.json`：结构化字幕数据

请只将抓取的字幕用于个人学习、跟读训练或研究，不要公开转载或商业分发。
