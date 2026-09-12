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

部分新账号在创建 Web Service 时会被要求绑定一张信用卡做反滥用验证
（仅 $1 预授权，验证后退回，免费额度内不产生费用）。这一判定挂在账号上，与浏览器无关。

如果不想绑卡，可以改用其他提供免费 HTTPS 托管的平台，或者先用内网穿透在本机把链路跑通，
托管的事之后再处理。另外一个可以省掉麻烦的做法是：把仓库设为 **Public**，
New → Web Service 时选 **Public Git Repository** 并直接粘贴仓库地址，
这样就完全不需要 GitHub 授权（代价是失去推送自动部署）。
本项目上游是 GPL-3.0，公开分发本身符合许可证要求。

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

## 三、接进 AI 客户端

### 3.1 WorkBuddy（本机 mcp.json）

编辑 `~/.workbuddy/mcp.json`（Windows 上是 `C:\Users\<用户名>\.workbuddy\mcp.json`）。
文件不存在就新建；已存在则只往 `mcpServers` 里加一项，不要覆盖其他条目：

```json
{
  "mcpServers": {
    "eink": {
      "type": "http",
      "url": "https://你的地址/mcp",
      "headers": { "X-Eink-Token": "你的EINK_TOKEN" }
    }
  }
}
```

保存后回到 WorkBuddy → 连接器 → **自定义连接器**，找到 `eink` 点「**信任**」启用
（不点信任不生效）。然后新开一个对话说「看一下墨水屏状态」，
若它调用了 `get_eink_status` 并返回屏幕内容，就是通了。

> 用 `headers` 传 token 比塞在 URL 里干净；服务端 `Query` / `X-Eink-Token` / `Bearer` 三种都收。

### 3.2 Claude（自定义连接器）

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

- **`push_to_eink(text, date?)`** — 推送文字。支持富文本标签；`text` 以 `[card]` 开头则
  切换成**卡片版式**（见第七节）。
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

## 七、卡片版式（信笺样式）

普通模式是「一整块文字、整体居中」。想让内容像一张真正的信笺——
**上下各一条红色分隔线、顶部一枚图标、居中衬线正文、页脚左边日期右边签名**——
把内容整段以 `[card]` 开头即可：

```
[card]
@template claude
@footer {today} | Claude

Rain falls:
You carry me home.
I have never been lighter.
```

### 两套模板

| `@template` | 顶部大图标 | 页脚小图标 | 语感 |
|---|---|---|---|
| `claude`（默认） | 红色星芒（Claude 标识） | 小星芒 | 正式、干净 |
| `wolf` | 手绘小狼头线稿 | 爪印 | 轻松、可爱、有涂鸦感 |

AI 推送时**自己挑一个**并写进 `@template`；用户明确说「小狼」「爪印」「可爱一点」时
用 `wolf`，否则默认 `claude`。想换风格也可以直接说，比如
「用**小狼模板**发一句：今晚月色很好」。

### 指令

| 指令 | 说明 |
|---|---|
| `@template` | 卡片模板：`claude`（默认）/ `wolf`。决定顶部大图标和页脚小图标的搭配 |
| `@icon` | **只覆盖顶部图标**：`claude` / `wolf` / `paw` / `star`（几何星芒）/ `heart` / `none`。一般不用写，`@template` 已经决定好了。`sun` 是 `claude` 的旧写法，仍然可用；`@icon wolf` 等同于 `@template wolf` |
| `@footer` | 页脚。用 `\|` 分左右两栏：左边靠左、右边靠右（右侧会自动带模板对应的小图标）；不写 `\|` 则整行靠左。**只写 `@footer` 不给值**时，左栏自动填当天日期 |

- 所有**非 `@` 开头**的行都是正文，**居中、衬线、自动缩放**，装不下会逐号缩小。
- 正文里照常支持 `<r>` `<b>` `<i>` 标签。
- **日期请写 `{today}`**（或 `{date}`），不要写死。它在**渲染时**才替换成当天日期，
  所以卡片放一整天、甚至明天再刷一次，日期都是当天的，不必重新推送。
  手机控制页每分钟对一次表，跨天会自动重绘预览（想让屏幕也换日期，重新说一句「发到墨水屏」即可）。
- `push_to_eink` 的 `date` 参数在卡片模式下不参与渲染。

**顶部图标是官方矢量轮廓**：`claude` 用的是 Anthropic 星芒标识的官方路径数据（viewBox 24×24，
外接框实测正好铺满、中心在 (12,12)），用 `Path2D` 直接填充，不是「12 条线段」的近似画法 ——
官方图形每根射线都是带斜切端头的楔形、角度和长度都不均匀，线段画法在同样尺寸下明显更散。

> 路径数据取自 [simple-icons](https://github.com/simple-icons/simple-icons)（图标本身是
> Anthropic 的商标）。自己玩没问题；要对外分发请注意对方的品牌使用规范。
> 环境不支持 `Path2D` 时会自动回退成几何星芒画法，不会画不出来。

**为什么用矢量绘制而不是图片？** 图片要先抖动成 1-bit，汉字笔画和 1px 细线在 400×300 上
会糊成一团噪点；卡片模式是把文字、线条、图标直接画到位图上，边缘是干净的整像素。
在控制页点「填入卡片示例」可以立刻看到效果。

---

## 八、故障排查

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

## 九、BLE 协议速查

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
