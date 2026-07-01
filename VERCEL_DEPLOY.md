# Vercel 部署指南

Subtitle Studio 可以用 Vercel Container Images 部署。Vercel 会识别根目录的 `Dockerfile.vercel`，构建 OCI 镜像，并把全部请求路由到容器里的 Python 服务。

## 适用范围

这个路线适合先给朋友小范围试用。它仍然是容器函数，不是长期常驻 VPS：

- 空闲后实例会缩容，下一次访问可能有冷启动。
- 生成 DOCX/PDF、TTS、抓字幕都会消耗 Vercel 函数资源。
- DeepSeek API 费用仍然由你自己的 Key 承担。
- 生成文件保存在容器临时磁盘里，建议朋友生成后及时下载。

## 必需环境变量

在 Vercel 项目设置里添加：

```text
DEEPSEEK_API_KEY=你的 DeepSeek Key
APP_USERNAME=friend
APP_PASSWORD=设置一个访问密码
PUBLIC_DEPLOYMENT=1
ALLOW_CUSTOM_OUTPUT_DIR=0
RATE_LIMIT_ENABLED=1
OUTPUT_RETENTION_HOURS=24
MAX_REQUEST_BYTES=8388608
```

不要把真实 Key 写进 Git。

## 命令行部署

第一次部署：

```bash
npm install
npx vercel login
npx vercel --prod
```

如果 CLI 已经登录，直接运行：

```bash
npm run vercel:deploy
```

部署成功后，Vercel 会返回类似：

```text
https://youtube-subtitle.vercel.app
```

## 本地验证容器

```bash
docker build -f Dockerfile.vercel -t subtitle-studio-vercel .
docker run --rm -p 8765:80 --env-file .env -e APP_USERNAME=friend -e APP_PASSWORD=本地密码 subtitle-studio-vercel
```

打开：

```text
http://127.0.0.1:8765/
```

## 注意

Vercel Container Images 是 Vercel Functions 的一部分，遵循 Vercel Functions 的限制和计费模型。如果后续使用人数多，建议升级 Pro 或迁移到长期容器平台。
