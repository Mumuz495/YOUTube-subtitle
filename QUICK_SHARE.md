# 临时分享给朋友

如果只是想让朋友现在试用，不想先买服务器，可以用 Cloudflare Quick Tunnel。

它会把你本机运行的 Subtitle Studio 临时映射成一个 HTTPS 网址，通常是 `https://xxxx.trycloudflare.com`。你的电脑和脚本必须一直开着，朋友才能访问。

Cloudflare 官方说明：Quick Tunnel 会生成一个随机 `trycloudflare.com` 子域，并把请求代理到本地运行的 Web 服务。

## Windows 一键临时分享

在项目目录运行：

```powershell
.\scripts\start_share_tunnel.ps1
```

脚本会：

1. 让你设置一个临时访问密码。
2. 启动本地 Subtitle Studio。
3. 如果本机没有 `cloudflared`，下载到 `.tools/cloudflared.exe`。
4. 创建一个 Cloudflare Quick Tunnel。
5. 在终端里打印一个 `trycloudflare.com` 网址。

把这个网址、用户名和临时密码发给朋友即可。

默认用户名：

```text
friend
```

自定义端口、用户名和密码：

```powershell
.\scripts\start_share_tunnel.ps1 -Port 8765 -Username friend -Password "临时强密码"
```

如果终端日志里出现 QUIC 连接失败，可以试试 HTTP/2：

```powershell
.\scripts\start_share_tunnel.ps1 -Protocol http2
```

## 注意事项

- 这是临时分享方式，不是长期正式部署。
- 关闭终端或电脑睡眠后，朋友就访问不了了。
- 每次重新运行通常会得到一个新的随机网址。
- 不要把 DeepSeek API Key 发给朋友；它只应该保存在你本机 `.env` 或正式部署平台的环境变量里。
- 脚本会开启公网模式：密码保护、POST 限流、生成文件 24 小时清理都会生效。

## 如果出现 530 或隧道连不上

如果朋友打开网址看到 530，或者终端日志里出现类似：

```text
QUIC connection failed
HTTP/2 connection is blocked or unreachable
TLS handshake with edge error
```

说明你当前网络可能阻止了 Cloudflare Tunnel 需要的出站连接。可以依次尝试：

1. 换一个网络，比如手机热点。
2. 使用 `-Protocol http2` 再启动一次。
3. 检查防火墙是否允许 `cloudflared.exe` 出站。
4. 放弃临时隧道，改用 `DEPLOY_WEBSITE.md` 里的 Render / Fly.io / Railway 正式部署。

我在这台机器上实测时，Cloudflare API 可以访问，但 Tunnel 到边缘节点的 QUIC/HTTP2 连接被阻断，所以生成了 `trycloudflare.com` 地址但公网 smoke 返回 530。这种情况不是 Subtitle Studio 应用本身坏了。

## 什么时候用正式部署

如果朋友会经常使用，请按 [DEPLOY_WEBSITE.md](DEPLOY_WEBSITE.md) 部署到 Render、Fly.io、Railway 或 VPS。

临时分享适合：

- 给朋友演示
- 小范围测试
- 验证这个工具是否真的有人愿意长期用

## 参考

- Cloudflare Quick Tunnels: https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/
- cloudflared 下载说明: https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/downloads/
