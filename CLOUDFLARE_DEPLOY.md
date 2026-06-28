# Cloudflare 部署指南

Subtitle Studio 可以走 Cloudflare Containers，因为它是一个 Python + Docker 的后端应用，并且需要 Chromium 生成 PDF。

Cloudflare Pages / 普通 Workers 不适合直接承载当前版本，因为它不是纯静态网页，也不是轻量 JS Worker。

## 前提

你需要：

- Cloudflare Workers Paid plan
- Node.js 和 npm
- Docker Desktop 正常运行
- Wrangler 登录 Cloudflare

Cloudflare Containers 官方说明：`wrangler deploy` 会构建 Docker 镜像、推送到 Cloudflare Registry，并部署 Worker 来按需启动容器。

## 安装依赖

```bash
npm install
```

## 登录 Cloudflare

```bash
npx wrangler login
```

## 设置密钥

不要把这些值写进 `wrangler.toml`。

```bash
npx wrangler secret put DEEPSEEK_API_KEY
npx wrangler secret put APP_PASSWORD
```

`APP_USERNAME` 默认是：

```text
friend
```

如果要改用户名，编辑 `wrangler.toml` 的 `[vars] APP_USERNAME`。

## 部署

确保 Docker Desktop 正在运行，然后执行：

```bash
npm run cf:deploy
```

部署后查看容器状态：

```bash
npm run cf:containers
```

第一次部署后，Cloudflare Containers 可能需要几分钟准备容器实例。

## 验证

拿到 Workers URL 后运行：

```bash
python scripts/smoke_deployment.py https://你的-worker.你的子域.workers.dev --username friend --password 访问密码
```

必须全部通过：

```text
[OK] healthz
[OK] password gate
[OK] authorized home
[OK] blocked .env download
```

## 当前限制

- 当前机器没有 Docker，所以我无法在这里实际执行 `wrangler deploy`。
- Cloudflare Containers 需要 Workers Paid plan。
- 容器磁盘是临时的，生成文件默认 24 小时清理；朋友应下载后本地保存。

