# 网站部署指南

Subtitle Studio 不是纯静态网页，它需要 Python 后端来抓字幕、调用 DeepSeek、生成 DOCX/PDF 和 TTS 音频。因此不要只部署到 GitHub Pages 这类静态网站。

推荐用支持 Docker 的平台部署，例如 Render、Fly.io、Railway，或者自己的 VPS。

项目已经包含：

- `Dockerfile`：容器部署入口
- `.dockerignore`：避免把密钥、缓存和导出文件打进镜像
- `render.yaml`：Render Blueprint 配置
- `WEBSITE_ARCHITECTURE.md`：长期架构方案
- `.github/workflows/ci.yml`：GitHub Actions 自动测试
- `scripts/preflight.py`：部署前本地自检

## 分享给朋友前必须设置

公网部署时请务必设置访问密码，避免别人随便消耗你的 DeepSeek API 额度。

需要的环境变量：

```text
DEEPSEEK_API_KEY=你的DeepSeekKey
APP_USERNAME=friend
APP_PASSWORD=设置一个强密码
HOST=0.0.0.0
PUBLIC_DEPLOYMENT=1
RATE_LIMIT_ENABLED=1
OUTPUT_RETENTION_HOURS=24
PORT=8765
```

如果部署平台会自动分配端口，按平台要求设置 `PORT`。

## 方案 A：临时分享，本机开着即可

适合给朋友短时间试用。

可以使用 Cloudflare Tunnel、ngrok、Tailscale Funnel 等工具，把本机 `http://127.0.0.1:8765/` 临时映射成公网网址。

优点：

- 最快
- 不需要买服务器
- 方便测试朋友是否真的需要这个工具

缺点：

- 你的电脑必须一直开着
- 不适合长期稳定使用

## 方案 B：正式网站，推荐

适合长期给朋友使用。

大致流程：

1. 把项目推送到 GitHub / Gitee / GitLab。
2. 推送前先运行部署前自检：

```bash
python scripts/preflight.py
```

3. 推送到 GitHub 后，等待 GitHub Actions CI 通过。
4. 在部署平台新建 Web Service。
5. 连接项目仓库。
6. 选择 Dockerfile 部署。
7. 添加环境变量：

```text
DEEPSEEK_API_KEY=你的DeepSeekKey
APP_USERNAME=friend
APP_PASSWORD=设置一个强密码
HOST=0.0.0.0
PUBLIC_DEPLOYMENT=1
RATE_LIMIT_ENABLED=1
OUTPUT_RETENTION_HOURS=24
```

8. 部署成功后，把平台提供的网址分享给朋友。

### Render 快速部署

1. 把项目推送到 GitHub。
2. 打开 Render，选择 New Blueprint 或 New Web Service。
3. 连接这个仓库。
4. Render 会读取 `render.yaml` 和 `Dockerfile`。
5. 在环境变量里填写：

```text
DEEPSEEK_API_KEY=你的DeepSeekKey
APP_PASSWORD=设置一个强密码
```

6. 部署完成后，用 Render 提供的网址访问。

部署完成后可以运行一次自检：

```bash
python scripts/smoke_deployment.py https://你的服务地址 --username friend --password 你的访问密码
```

它会检查：

- `/healthz` 可访问
- 首页有密码保护
- 正确密码能打开首页
- `.env` 不能通过下载接口读取

## 本地测试 Docker

电脑装好 Docker 后，在项目目录运行：

```bash
docker build -t subtitle-studio .
docker run --rm -p 8765:8765 --env-file .env -e HOST=0.0.0.0 subtitle-studio
```

打开：

```text
http://127.0.0.1:8765/
```

如果 `.env` 里设置了 `APP_PASSWORD`，浏览器会弹出账号密码框。

## 部署前自检

每次准备上线前建议先运行：

```bash
python scripts/preflight.py
```

它会检查：

- 必需文件是否存在
- 源码里是否误写入真实 DeepSeek Key
- `.gitignore` 是否保护 `.env` 和 `output/`
- Python 文件是否能编译
- 单元测试是否通过

## 平台选择建议

Render、Fly.io、Railway 都支持从仓库里的 Dockerfile 构建运行容器。选哪个主要看你更习惯哪个后台、价格和地区速度。

如果你只是给少数朋友使用，优先选：

- 可以直接连 Git 仓库
- 能配置环境变量
- 支持持久运行的 Web Service
- 支持 Dockerfile

## 注意事项

- 不要把 `.env` 上传到 Git。
- 不要把 DeepSeek API Key 写进前端 JS。
- 给朋友使用时建议设置 `APP_PASSWORD`。
- 公网部署时保持 `PUBLIC_DEPLOYMENT=1`，后端会忽略用户传入的自定义服务器输出目录。
- 下载接口只允许下载 `output/` 下的生成文件，避免泄露 `.env` 或项目源码。
- 默认限流配置是每个客户端 10 分钟最多 60 次 POST 请求，可以用 `RATE_LIMIT_MAX_REQUESTS` 和 `RATE_LIMIT_WINDOW_SECONDS` 调整。
- 公网部署默认保留生成文件 24 小时，可以用 `OUTPUT_RETENTION_HOURS` 调整；朋友下载完 PDF/DOCX 后应本地保存。
- 视频、文章和字幕内容涉及版权，请只用于个人学习、跟读训练和研究。
- `output/` 在容器里通常是临时文件，平台重启后可能丢失。朋友下载完 DOCX/PDF 后，本地保存即可。
