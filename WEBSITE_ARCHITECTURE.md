# Subtitle Studio 网站架构方案

目标：让朋友可以通过一个网站使用 Subtitle Studio，同时保持代码可维护，不把抓取、翻译、导出、朗读、权限和页面逻辑混成一团。

## 产品形态

### V1：朋友小范围使用

适合先验证真实需求。

- 一个 Docker 化的 Python Web 服务
- 前端仍使用 `static/` 里的原生 HTML/CSS/JS
- 后端保管 `DEEPSEEK_API_KEY`
- 通过 `APP_USERNAME` / `APP_PASSWORD` 做简单访问保护
- 所有导出文件写入 `output/`
- 下载接口只允许读取 `output/`
- 适合部署到 Render、Fly.io、Railway 或 VPS

这个阶段的核心是：先让朋友能用，同时不泄露 API Key，不让公网用户随便读服务器文件。

### V2：稳定多人使用

当朋友真的频繁使用后，再升级：

- 登录系统：用户账号、邮箱登录或邀请码
- 任务队列：抓字幕、翻译、导出 PDF/DOCX 放后台任务执行
- 数据库：保存任务、用户、生词本、文档历史
- 对象存储：PDF/DOCX/音频放 S3、R2、OSS 等对象存储
- 限额系统：每个用户每天可生成多少次，避免 API 费用失控
- 统一日志：记录失败原因、生成耗时、API 用量

不要一开始就做完整 SaaS。先用 V1 验证需求，确认有人持续用，再进入 V2。

## 当前代码边界

当前项目主要文件：

- `app.py`：HTTP 服务、路由、认证、下载保护
- `subtitle_studio/web_config.py`：公网/本地模式、请求大小、输出目录策略
- `subtitle_studio/web_limits.py`：共享密码部署下的轻量 API 限流
- `subtitle_studio/web_paths.py`：静态文件和下载文件的路径安全
- `transcript_tool.py`：字幕抓取、文章抓取、翻译、生词解释、TTS、导出
- `static/`：浏览器界面
- `tests/`：回归测试
- `Dockerfile`：网站部署

现在可以上线，并且 Web 层的配置和路径安全已经从 `app.py` 里拆出来。`transcript_tool.py` 仍然偏大，后续不要继续把所有能力都塞进这一个文件。

## 推荐代码拆分路线

等功能继续变多时，按这个结构拆：

```text
subtitle_studio/
  config.py
  domain/
    models.py
  web/
    server.py
    auth.py
    downloads.py
    routes.py
  services/
    content_service.py
    translation_service.py
    vocab_service.py
    tts_service.py
    export_service.py
    storage_service.py
  providers/
    deepseek.py
    youtube.py
    article_reader.py
    edge_tts_provider.py
  jobs/
    queue.py
    workers.py
static/
tests/
```

拆分原则：

- `web/` 只处理 HTTP、请求校验、响应格式、认证、下载权限
- `services/` 处理业务流程，比如“输入 URL -> 抓取 -> 翻译 -> 保存 -> 返回结果”
- `providers/` 只封装第三方服务，比如 DeepSeek、YouTube、TTS
- `domain/` 放稳定的数据结构，比如字幕片段、生词条目、导出文档模型
- `storage_service.py` 统一管理本地文件或云存储路径
- `jobs/` 只在需要后台队列时再加

## API 边界

当前 V1 API：

- `POST /api/fetch`：抓取视频字幕或文章，并可生成双语内容
- `POST /api/vocab`：解释选中的生词或短语
- `POST /api/tts`：生成单词、段落或全文朗读音频
- `POST /api/export-study-sheet`：导出 HTML / DOCX / PDF 精读稿
- `GET /download?path=...`：下载生成文件

公网部署时，后端应坚持这些规则：

- 不接受前端传来的任意绝对输出路径
- 不允许下载 `output/` 以外的文件
- 不把 DeepSeek API Key 返回给前端
- 错误信息要能帮助用户，但不要暴露服务器内部路径或密钥
- 后端保存文件名时要可预测、可清理，避免无限堆积

## 安全策略

V1 必须有：

- `APP_PASSWORD`：朋友访问网站前需要输入密码
- `DEEPSEEK_API_KEY`：只存在服务器环境变量中
- `PUBLIC_DEPLOYMENT=1`：公网模式下禁止用户自定义服务器输出目录
- 下载目录限制：只允许下载 `output/` 下的生成文件
- `MAX_REQUEST_BYTES`：限制单次请求大小，避免异常大请求拖垮服务
- `RATE_LIMIT_ENABLED`：公网模式默认开启，对 POST API 做轻量限流
- GitHub Actions CI：每次推送后自动跑编译和测试
- `scripts/preflight.py`：部署前本地自检

V2 再考虑：

- 用户登录
- 用户级别配额
- IP 限速
- 操作日志
- 文件自动过期
- API 费用统计

## 部署架构

V1 推荐：

```text
Browser
  -> HTTPS deployment platform
    -> Docker container
      -> Python app.py
      -> output/
      -> DeepSeek API
      -> YouTube / article pages
```

环境变量：

```text
DEEPSEEK_API_KEY=你的DeepSeekKey
APP_USERNAME=friend
APP_PASSWORD=强密码
HOST=0.0.0.0
PUBLIC_DEPLOYMENT=1
```

## 为什么不用纯静态网站

这个工具需要后端，因为它要：

- 访问 YouTube / 文章网页
- 调用 DeepSeek
- 生成 TTS 音频
- 生成 DOCX / PDF
- 保存和下载文件
- 保护 API Key

所以 GitHub Pages、普通静态托管不适合。应该使用能运行后端的容器平台。

## 后续演进建议

### 第一阶段

- 保持单容器部署
- 朋友用统一密码访问
- 手动观察使用频率和 API 费用
- 每次上线前跑 `python scripts/preflight.py`
- GitHub Actions 通过后再部署

### 第二阶段

- 加用户账号或邀请码
- 加每人每日限额
- 加文件清理任务

### 第三阶段

- 把长任务放进队列
- 生成完成后前端轮询任务状态
- 文件上传到对象存储
- 生词本持久化到数据库

### 第四阶段

- 做公开产品页
- 做登录、套餐、额度
- 做用户资料同步
- 做更多视频平台和文章源适配

## 代码质量红线

不要做这些事：

- 在前端保存 API Key
- 在一个函数里同时做抓取、翻译、写文件、拼 HTML、返回 HTTP
- 每加一个平台就在主流程里堆 `if/else`
- 让前端传任意服务器路径
- 让下载接口读取项目任意文件
- 把用户文件、密钥、缓存提交到 Git

应该做这些事：

- 每个第三方平台做成 provider
- 每个业务能力做成 service
- 文件读写统一走 storage
- HTTP 层只做请求和响应
- 每次加安全边界都补测试
