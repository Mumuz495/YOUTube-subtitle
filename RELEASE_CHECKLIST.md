# 正式发布清单

这份清单用于把 Subtitle Studio 正式部署成一个可以分享给朋友的网站。

## 1. 发布前本地检查

```bash
python scripts/preflight.py
```

必须全部通过：

```text
[OK] required files
[OK] secret scan
[OK] gitignore
[OK] python compile
[OK] unit tests
```

## 2. 推送到 GitHub

如果还没有远程仓库，先在 GitHub 创建一个空仓库，然后运行：

```bash
git remote add origin https://github.com/你的用户名/subtitle-studio.git
git push -u origin main
```

Windows 也可以直接用项目脚本：

```powershell
.\scripts\publish_remote.ps1 -RemoteUrl "https://github.com/你的用户名/subtitle-studio.git"
```

这个脚本会先运行 `python scripts/preflight.py`，确认没有明显问题后再推送。

以后更新：

```bash
git pull
python scripts/preflight.py
git add .
git commit -m "更新说明"
git push
```

## 3. 等 GitHub Actions 变绿

推送后打开 GitHub 仓库的 Actions 页面，确认 CI 通过。

CI 会检查：

- Python 编译
- 单元测试
- preflight
- Docker 镜像构建

## 4. 部署到 Render

推荐给第一次正式部署使用。

1. 打开 Render。
2. 选择 New Blueprint 或 New Web Service。
3. 连接 GitHub 仓库。
4. Render 会读取 `render.yaml` 和 `Dockerfile`。
5. 填写环境变量：

```text
DEEPSEEK_API_KEY=你的DeepSeekKey
APP_PASSWORD=强密码
```

部署完成后，Render 会给你一个 HTTPS 网址。

## 5. 或者部署到 Fly.io

项目也提供了 `fly.toml`。

第一次部署：

```bash
fly launch --no-deploy
fly secrets set DEEPSEEK_API_KEY="你的DeepSeekKey" APP_PASSWORD="强密码"
fly deploy
```

注意：Fly.io 的 `app` 名称需要全局唯一。如果 `fly launch` 提示名称冲突，按提示选择一个新的名称，或编辑 `fly.toml` 里的 `app = "subtitle-studio"`。

以后更新：

```bash
fly deploy
```

## 6. 上线后 smoke test

拿到网站地址后运行：

```bash
python scripts/smoke_deployment.py https://你的网站地址 --username friend --password 访问密码
```

必须全部通过：

```text
[OK] healthz
[OK] password gate
[OK] authorized home
[OK] blocked .env download
```

## 7. 分享给朋友

发给朋友：

- 网站 URL
- 用户名：`friend`
- 访问密码

不要发送：

- DeepSeek API Key
- `.env`
- GitHub 私有仓库写权限

## 8. 发现问题时

先看这几个地方：

- 部署平台日志
- GitHub Actions CI
- `python scripts/smoke_deployment.py ...`
- `DEPLOY_WEBSITE.md`
- `WEBSITE_ARCHITECTURE.md`
