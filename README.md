# 墨水屏推送服务（E-Ink MCP）

把 AI 对话里的一句话，送到一块十几块钱的电子货架标签上。

```
AI 对话 → push_to_eink（MCP）→ 本服务器 → SSE → 手机控制页 → BLE → 墨水屏
```

硬件、固件、BLE 协议与前端渲染来自
[0xblewalker/eink-ble-writer](https://github.com/0xblewalker/eink-ble-writer)（GPL-3.0），
固件来自 [tsl0922/EPD-nRF5](https://github.com/tsl0922/EPD-nRF5)（GPL-3.0）。
本项目在其基础上补齐了**原项目缺失的三块**：MCP 接口、SSE 实时推流、token 鉴权。

---

## 项目结构

```
eink-mcp/
├── server.py                 后端：MCP + SSE + 鉴权 + 静态托管
├── index.html                手机控制页：SSE 监听 + BLE 写入 + 富文本渲染
├── requirements.txt
├── render.yaml               Render 一键部署蓝图
├── upstream/                 上游原始代码（参考用，GPL-3.0）
├── docs/                     两份需求文档的原文提取
└── latest_letter.json        运行时生成的内容存档
```

---

## 一、本地跑通（5 分钟）

```bash
pip install -r requirements.txt
export EINK_TOKEN=my-secret-token      # Windows: set EINK_TOKEN=my-secret-token
uvicorn server:app --host 0.0.0.0 --port 8905
```

打开 <http://127.0.0.1:8905/?token=my-secret-token>，
填入 Token → 连接墨水屏 → 开始监听。

> 没设置 `EINK_TOKEN` 时服务会临时生成一个并打印在日志里，方便调试；
> **公网部署必须显式设置**，否则等于任何人都能往你屏幕上写字。

---

## 二、部署到 Render

### 方式 A：用 render.yaml 蓝图

1. 把本项目推到你的 GitHub 仓库
2. Render → New → **Blueprint** → 选该仓库
3. Render 读取 `render.yaml`，自动创建服务并**生成一个随机 `EINK_TOKEN`**
4. 部署完成后进 **Environment** 页面，把 `EINK_TOKEN` 的值复制出来

> 部分账号走到 Blueprint 会被要求添加信用卡（蓝图能创建付费资源，Render 会先做校验）。
> 只跑一个免费 Web Service 的话，直接走**方式 B**，免费版不需要绑卡。

### 方式 B：手动建 Web Service（不需要绑卡）

Render → New → **Web Service**（不要选 Key Value / Postgres / Blueprint）→ 选仓库，然后按下表填：

| 配置项 | 值 |
|---|---|
| Name | `eink-mcp` |
| Region | Singapore（离国内最近） |
| Branch | `main` |
| Root Directory | 留空 |
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn server:app --host 0.0.0.0 --port $PORT` |
| Instance Type | **Free** |
| Environment Variable | `EINK_TOKEN` = 自己指定的一串随机字符 |
| Health Check Path | 可留空；填则用 `/healthz`（该路径不需 token） |

⚠️ **`EINK_TOKEN` 必须手动填死。** `server.py` 读不到这个变量时会临时随机生成一个，
而免费版每次休眠重启都是新进程——token 一变，Claude 连接器和手机页面会全部失效。

#### 如果创建服务时被要求绑卡

官方文档写「免费版不需要卡」，但实测：**注册时所用节点不干净的新账号会被风控要求绑一张卡**
做反滥用验证（预授权 $1，验证后退回，免费额度内不产生费用）。判定挂在**账号**上——
换浏览器、换 IP 登录同一个账号都不会改变结果。三条出路：

1. **绑卡**：手上有 Visa/MasterCard 双币卡时最省事，5 分钟收工。
2. **用干净节点重新注册一个账号**（是重新注册，不是重新登录）：
   注册全程挂着同一个干净节点、不切回国内；建议用**邮箱 + 密码**注册而不是 GitHub 登录。
   如果新账号连接 GitHub 时提示已占用，去 GitHub → Settings → Applications → Render
   移除旧授权再重连。
3. **改用公开仓库部署，彻底绕开 GitHub 授权**：把仓库设为 Public，
   New → Web Service → 选 **Public Git Repository** → 粘贴仓库地址。
   代价：失去推送自动部署，改代码后要在 Render 里手动 Deploy 一次。
   注意本项目的上游是 GPL-3.0，公开分发不违反许可证。

仓库是私有的：如果选仓库时列表里看不到 `eink-mcp`，去 GitHub → Settings → Applications → Render
把仓库访问范围放开（Render 侧也有 "Configure account" 入口）。

**可以先不绑域名**：`https://eink-mcp-xxxx.onrender.com` 自带 HTTPS，Web Bluetooth 和
Claude 自定义连接器都能直接用。等链路跑通再按下面绑域名。

### 绑定域名

1. Render → 你的服务 → Settings → Custom Domains → 添加域名
2. 到域名注册商处加一条 **CNAME** 记录，指向 Render 给出的地址
3. 等证书签发（几分钟）

### 免费版的两个注意点

- **15 分钟无请求会休眠**，首次唤醒要 30–60 秒。手机页面用 SSE 长连接，
  有监听时不会休眠；长时间没人用，第一次打开等一会儿是正常的。
- **磁盘是临时的**，重新部署后 `latest_letter.json` 会丢。设置好的内容在内存和手机上都有，
  不影响使用。

---

## 三、接进 Claude（自定义连接器）

Claude → Settings → **Connectors** → Add custom connector，填：

```
https://你的域名/mcp?token=你复制的EINK_TOKEN
```

保存后新开一个对话，说：

> 帮我看一下墨水屏状态

如果 Claude 调用了 `get_eink_status` 并返回了屏幕内容，就是通了。
之后直接说「**把这句话发到墨水屏：今天天气不错**」即可。

> token 放在 URL 查询串里是最省事的方式 —— Claude 的远程连接器会把整个 URL 原样带上。
> 如果你更希望用 Header 传，服务端也支持 `Authorization: Bearer <token>` 和 `X-Eink-Token: <token>`。

---

## 四、手机端每次使用的三步

1. 用 **Chrome** 打开 `https://你的域名/?token=你的TOKEN`
   （iOS 的 Safari 不支持 Web Bluetooth，装免费的 **Bluefy** 打开）
2. 点「**连接墨水屏**」，在蓝牙列表里选 `EPD-xxxx`
3. 确认「**开始监听**」已亮起（显示 `SSE ON`）

之后保持这个页面在前台，AI 一推送就会自动刷屏。
页面藏到后台或锁屏时，手机系统可能挂起 JS，蓝牙会断——这是浏览器的限制，不是 bug。

---

## 五、接口清单

所有 `/api`、`/events`、`/mcp`、`/sse` 路径都要求 token（Query / Header 均可）。

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/` | 手机控制页 |
| GET | `/healthz` | 健康检查（免鉴权） |
| POST | `/api/letter` | 推送内容 `{"text": "...", "date": "2026-09-12"}` |
| GET | `/api/latest` | 取当前内容 |
| GET | `/api/version` | 取版本号与更新时间 |
| GET | `/api/history` | 取最近 20 条推送记录 |
| GET | `/events` | SSE 实时推流（控制页用） |
| POST | `/mcp` | MCP（Streamable HTTP） |
| GET | `/sse` | MCP（旧版 HTTP+SSE 传输，兼容老连接器） |

### MCP 工具

- **`push_to_eink(text, date?)`** — 推送文字。内容支持富文本标签。
- **`get_eink_status()`** — 看当前屏幕内容、更新时间、推送历史，以及**有没有手机在线**。

> 没有手机在线时，`push_to_eink` 会明确告诉你「内容已入库但屏幕不会刷新」，
> 而不是假装成功 —— 这是最容易迷惑人的一步。

---

## 六、富文本标签

在推送内容里用 HTML 风格标签控制样式，**可嵌套**：

| 标签 | 效果 | 示例 |
|---|---|---|
| `<r>…</r>` | 红色 | 我<r>一直</r>在 |
| `<b>…</b>` | 加粗 | `<b>早安</b>` |
| `<i>…</i>` | 斜体 | `<i>月色真美</i>` |

`<b><r>重要</r></b>` 会渲染成加粗的红色。
**红色是这块屏幕唯一的彩色，克制使用** —— 偶尔一个词亮起来才有感觉。

标签不闭合也不会崩，只是会一直染到结尾。

---

## 七、故障排查

| 现象 | 原因与处理 |
|---|---|
| 满屏红色噪点 | 红色层没初始化。本项目按位或填充，纯黑白内容自然得到整层 `0xFF`，正常不该出现；若出现请检查是否换过渲染代码 |
| 蓝牙连不上 | 先换电池；确认没有别的手机/电脑连着（BLE 同时只允许一个连接）；取下电池几秒再装回可强制重置 |
| 内容被截断 | 400×300 在 28px 下大约 5–6 行。控制页默认开「自动缩小」，装不下会自动缩到 12px；也可以自己调小字号 |
| Claude 不调用工具 | 确认连接器状态是 connected；把话说死一点——「用 push_to_eink 工具推送」 |
| 推送成功但屏幕没变 | 多半是没有手机在线监听。调 `get_eink_status` 看「在线手机数」 |
| 服务器没响应 | Render 免费版冷启动，等 30–60 秒；超过一分钟去 Render 控制台看服务是否崩了 |
| iOS 打不开蓝牙 | Safari 不支持 Web Bluetooth，换 **Bluefy** |

覆盖 4.2 寸（400×300）之外的屏，在控制页「显示屏」里改宽高再点「应用」即可。

---

## 八、BLE 协议速查

给需要自己写客户端的人：

| 项 | 值 |
|---|---|
| Service UUID | `62750001-d828-918d-fb46-b6c11c675aec` |
| Write Characteristic | `62750002-d828-918d-fb46-b6c11c675aec` |
| Version Characteristic | `62750003-d828-918d-fb46-b6c11c675aec` |
| INIT | `0x01` |
| WRITE_IMAGE | `0x30` |
| REFRESH | `0x05` |

下发流程：`INIT` → 等约 200ms → `WRITE_IMAGE`（黑白层）→ `WRITE_IMAGE`（红色层）→ `REFRESH`

- `WRITE_IMAGE` 报文体：`[0x30][flag][data...]`
- `flag` 高半字节：`0x00` 首块 / `0xF0` 续块；低半字节：`0x0F` 黑白层 / `0x00` 红色层
- 数据 1bpp、8 像素/字节、MSB first
- 黑白层：`1`=白 `0`=黑；红色层：`0`=红 `1`=非红
- 每行 `ceil(width/8)` 字节；400×300 单层 = 15000 字节
- MTU 由设备通过 notification 上报 `mtu=NNN`（典型 242），单块有效载荷 = MTU − 2

---

## 许可

本项目继承上游的 **GPL-3.0**。二次分发必须保留同样的许可并署名原作者：

- 前端与服务器改造基于 [0xblewalker/eink-ble-writer](https://github.com/0xblewalker/eink-ble-writer)
- 固件基于 [tsl0922/EPD-nRF5](https://github.com/tsl0922/EPD-nRF5)
