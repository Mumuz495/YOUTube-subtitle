# Subtitle Studio Sync Guide

Use Git for the source code, settings template, and tests. Keep private keys and generated study sheets local.

## First Setup On Windows

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
py app.py
```

Open:

```text
http://127.0.0.1:8765/
```

## First Setup On macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
open -e .env
python app.py
```

Open:

```text
http://127.0.0.1:8765/
```

## Daily Workflow

Before you start on either computer:

```bash
git pull
```

After you make changes:

```bash
git status
git add app.py transcript_tool.py static tests requirements.txt README.md SYNC.md
git commit -m "Describe your change"
git push
```

## What Is Not Synced

The `.env` file is ignored because it contains your DeepSeek key.

The `output/` folder is ignored because it contains generated TXT, HTML, DOCX, PDF, and audio files. If you want generated study sheets to sync too, put `output/` in OneDrive, iCloud Drive, or another cloud folder, or tell Git to track only selected final documents.
