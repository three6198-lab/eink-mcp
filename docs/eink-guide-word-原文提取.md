### ZIP ENTRIES: [Content_Types].xml, _rels/.rels, docProps/app.xml, docProps/core.xml, docProps/custom.xml, word/comments.xml, word/document.xml, word/_rels/document.xml.rels, word/endnotes.xml, word/fontTable.xml, word/footer1.xml, word/_rels/footer1.xml.rels, word/footer2.xml, word/_rels/footer2.xml.rels, word/footer3.xml, word/_rels/footer3.xml.rels, word/footnotes.xml, word/media/image1.png, word/numbering.xml, word/settings.xml, word/styles.xml

让 Claude 写字到墨水屏 — 完整连接指南
Get Claude to Write on an E-Ink Display — A Complete Setup Guide
No API, no coding required — just type in Claude’s chat and it shows up on your e-ink display.
———
本教程的硬件方案、固件、BLE 协议及前端工具均基于 0xblewalker 的开源项目 eink-ble-writer（GPL-3.0）。原项目提供了出色的单文件蓝牙写入工具，但在“如何将 Claude 对话与墨水屏连通”这一环节缺少详细说明。本文补充的正是这部分——包括最初反复被建议用 API 调用和终端命令，最终才找到对话框直接推送这条路。
Hardware, firmware, BLE protocol, and the frontend tool in this tutorial are based on 0xblewalker’s open-source project eink-ble-writer (GPL-3.0). The original project provides an excellent single-file Bluetooth writing tool, but doesn’t cover how to connect Claude’s conversation to the display. That’s what this guide fills in — including all the dead ends I hit, like being told to use API calls and terminal commands, before finally getting direct chat-to-display working.
———
[Heading1] 一、你需要准备什么 / What You Need
硬件 / Hardware
一块搭载 Nordic 芯片的电子货架标签（ESL），推荐 nRF52811 三色屏（黑/白/红）。闲鱼、淘宝、eBay 搜“电子货架标签”或“ESL e-ink”，价格大约 10–50 元。供电是 CR2450 纽扣电池，不刷新时零功耗，一颗电池能用几个月。
You need an electronic shelf label (ESL) with a Nordic chip — nRF52811 with a three-color display (black/white/red) is recommended. Search “electronic shelf label” or “ESL e-ink” on second-hand platforms. They cost around $2–10. Powered by a CR2450 coin cell battery with zero standby power draw — one battery lasts months.
软件和账号 / Software & Accounts
一个域名（任何注册商都行）；Render 账号（免费版即可部署服务器）；Claude Pro 订阅（需要自定义连接器功能）；手机上的 Chrome 浏览器（iOS 用 Bluefy，Safari 不支持 Web Bluetooth）。
A domain name (any registrar works); a Render account (free tier is fine); a Claude Pro subscription (needed for custom connectors); Chrome on your phone (Bluefy on iOS — Safari doesn’t support Web Bluetooth).
[Heading1] 二、固件 / Firmware
显示屏必须运行 EPD-nRF5 开源固件。如果你买到的是预刷好固件的屏，跳过这一章。设备蓝牙名称会显示为 EPD-xxxx，能被扫描到就说明固件没问题。
The display must be running the EPD-nRF5 open-source firmware. If your display came pre-flashed, skip this chapter. The Bluetooth name will show up as EPD-xxxx — if you can see it in a scan, you’re good.
如果没有预刷，需要 J-Link 或 DAPLink 编程器通过 SWD 接口烧录。具体步骤参考原项目仓库。
If not pre-flashed, you’ll need a J-Link or DAPLink programmer to flash via SWD. Refer to the original firmware repo for instructions.
[Heading1] 三、部署服务器 / Deploy the Server
这是整条链路的中枢。Claude 把内容发到你的服务器，手机从服务器实时接收，再通过蓝牙推到屏幕上。
This is the backbone of the entire chain. Claude sends content to your server, your phone receives it in real-time, then pushes it to the display via Bluetooth.
为什么需要服务器？/ Why do you need a server?
这里要说一段弯路。我一开始的想法很简单——让 Claude 直接把内容发到墨水屏。我跟 Claude 说了很多次，但它一直建议我用 API 调用、写 Python 脚本、在终端里跑 curl。我试过用 artifact 生成页面直接蓝牙连接，也试过让 Claude 输出代码让我本地跑。全都走不通。
A detour worth mentioning. My original idea was simple — have Claude send content directly to the display. I explained this to Claude many times, but it kept suggesting API calls, Python scripts, running curl in the terminal. I tried having Claude generate an artifact page with direct Bluetooth, tried having it output code to run locally. None of it worked.
问题的本质是：Claude 的对话界面没办法直接操作蓝牙，也没办法直接访问你的局域网设备。它需要一个中间人——一个公网上的服务器。Claude 把内容推到服务器，你的手机从服务器拉取内容，再由手机蓝牙发到屏幕。想通了这一点，后面就顺了。
The fundamental issue: Claude’s chat interface can’t directly operate Bluetooth or reach devices on your local network. It needs a middleman — a server on the public internet. Claude pushes content to the server, your phone pulls from the server, then your phone sends it to the display via Bluetooth. Once I understood this, everything fell into place.
部署步骤 / Deployment Steps
1. 准备代码：你需要两个文件——server.py（后端，处理 Claude 的推送和 SSE 实时推流）和 index.html（前端控制页面，负责蓝牙连接和屏幕渲染）。
1. Prepare your code: you need two files — server.py (backend, handles Claude’s push and SSE streaming) and index.html (frontend control page, handles Bluetooth and screen rendering).
2. 部署到 Render：在 render.com 创建一个 Web Service，连接你的 GitHub 仓库或直接上传代码。启动命令设为 uvicorn server:app --host 0.0.0.0 --port $PORT。
2. Deploy to Render: create a Web Service on render.com, connect your GitHub repo or upload directly. Set the start command to: uvicorn server:app --host 0.0.0.0 --port $PORT.
3. 设置环境变量：在 Render 的 Environment 页面添加 EINK_TOKEN，这是你的推送密钥，防止别人往你屏幕上写东西。
3. Set environment variables: add EINK_TOKEN in Render’s Environment settings — this is your push secret, preventing strangers from writing to your display.
4. 绑定域名：在 Render 设置自定义域名，然后去域名注册商那里添加 CNAME 记录指向 Render 分配的地址。
4. Bind your domain: set up a custom domain in Render, then add a CNAME record at your domain registrar pointing to Render’s assigned address.
5. 注意免费版休眠：Render 免费版在 15 分钟无请求后会休眠，首次唤醒需要 30–60 秒。这不影响使用，只是第一次打开页面时要等一会儿。
5. Free tier sleep: Render’s free tier sleeps after 15 minutes of inactivity, taking 30–60 seconds to wake up. This doesn’t break anything — you just need to wait a moment when first opening the page.
———
两条路线 / Two Paths
走到这里，有必要说清楚原项目开源了什么、没开源什么，这样你可以根据自己的需求选择路线。
Before going further, it’s worth clarifying what the original project includes and what it doesn’t, so you can choose the right path.
原项目仓库包含的是一个完整的本地蓝牙写入工具（eink-ble-writer.html）和一个基础远程推送服务器（server.py，61 行，支持 POST /api/letter 存内容、GET /api/latest 取内容，前端轮询拉取）。这套组合可以实现“从电脑发内容 → 手机轮询获取 → 蓝牙推到屏幕”。
The original repo includes a complete local Bluetooth writing tool (eink-ble-writer.html) and a basic remote push server (server.py — 61 lines, with POST /api/letter to store content and GET /api/latest to retrieve it, using a polling approach). This combo lets you send content from a computer → phone polls for updates → pushes to display via Bluetooth.
原项目不包含 Claude 对话框直接推送所需的几个关键部分：MCP 接口（让 Claude 能调用你的服务器）、SSE 实时推流（推送后手机瞬间收到，不用轮询）、以及 token 鉴权（防止未授权推送）。这些需要自己补充。
The original project does not include several key pieces needed for direct Claude chat-to-display: an MCP interface (so Claude can call your server as a tool), SSE real-time streaming (so the phone receives content instantly without polling), or token authentication (to prevent unauthorized pushes). These need to be added separately.
路线 A：用原项目代码，不接 Claude（不需要写代码）
直接把原项目的 server.py 和 eink-ble-writer.html 部署到 Render 就能用。你可以通过任何 HTTP 工具（浏览器、Postman、curl）往 /api/letter POST 内容，手机端页面轮询后推到屏幕。适合只想远程更新内容、不需要 Claude 介入的场景。
Deploy the original server.py and eink-ble-writer.html to Render as-is. Push content to /api/letter via any HTTP tool (browser, Postman, curl), and the phone page polls and pushes to the display. Good for remote updates without Claude involvement.
路线 B：Claude 对话框直接推送（本教程的重点）
这条路需要在原项目基础上补充 MCP、SSE 和 token 鉴权。你不需要从零开始写——把原项目的 server.py 发给 Claude，告诉它你需要加这三样东西，它能帮你补完。本教程后续章节按这条路线展开。
This path requires adding MCP, SSE, and token auth on top of the original project. You don’t have to write from scratch — send the original server.py to Claude, tell it you need these three things added, and it can build them out for you. The rest of this tutorial follows this path.
如果你选了路线 A，跳过第五章（MCP 连接），其他部分仍然适用。
If you chose Path A, skip Chapter 5 (MCP connection) — the other chapters still apply.
———
[Heading1] 四、前端控制页面 / The Control Page
前端页面是你手机上的“遥控器”——它一头连着服务器接收 Claude 推过来的内容，另一头通过蓝牙发到墨水屏。
The frontend page is the “remote control” on your phone — one end connects to the server to receive what Claude sends, the other end pushes to the display via Bluetooth.
部署方式 / How to Deploy
最简单的做法：把 index.html 放在你的服务器里一起托管。如果你用的是 FastAPI，让 server.py 直接 serve 这个静态文件就行，访问你的域名根路径就能打开控制页面。
The simplest approach: host index.html alongside your server. If you’re using FastAPI, have server.py serve it as a static file — visiting your domain root will open the control page.
每次使用前的三步 / Three Steps Before Each Use
每次想让 Claude 推送内容到墨水屏之前，你需要在手机上完成三步：1) 打开手机 Chrome（iOS 用 Bluefy），访问你的域名；2) 点击“连接墨水屏”，在蓝牙列表中选择 EPD-xxxx；3) 点击“开始监听”，状态栏显示 SSE ON。做完这三步，页面就进入待命状态了。之后你在任何一个 Claude 对话里触发推送，内容会实时出现在这个页面上，并自动通过蓝牙发到墨水屏。
Before each session, complete three steps on your phone: 1) Open Chrome (Bluefy on iOS), go to your domain; 2) Tap “Connect” and select EPD-xxxx from the Bluetooth list; 3) Tap “Start Listening” — status bar should show SSE ON. The page is now standing by. Whenever you trigger a push from any Claude conversation, the content arrives in real-time and automatically goes to the display via Bluetooth.
手动模式 / Manual Mode
控制页面也支持手动输入文字或上传图片直接推送，不经过 Claude。适合临时测试或者想自己写点东西的时候。
The control page also supports manual text input and image upload for direct pushing, bypassing Claude. Useful for quick tests or when you just want to write something yourself.
[Heading1] 五、Claude MCP 连接 / Connecting Claude via MCP
这是整个项目最关键也是踩坑最多的一步——让 Claude 的对话框能直接调用你的服务器。
This is the most critical step of the entire project, and where I hit the most walls — getting Claude’s chat interface to call your server directly.
什么是 MCP 连接器 / What is an MCP Connector
Claude 支持自定义连接器（MCP，Model Context Protocol），简单说就是你可以给 Claude 注册一个外部工具，让它在对话中直接调用。不需要你写 API 请求，不需要开终端，不需要跑脚本——你只要在对话框里说“把这段话发到墨水屏”，Claude 就会自己调用工具完成推送。
Claude supports custom connectors (MCP, Model Context Protocol) — you can register an external tool that Claude can call directly from a conversation. No API requests on your end, no terminal, no scripts. Just say “send this to my e-ink display” in the chat, and Claude invokes the tool itself.
配置步骤 / Setup Steps
1. 在 server.py 里实现 MCP 接口。你需要两个工具：push_to_eink（推送文字到墨水屏）和 get_eink_status（查看当前屏幕状态和推送历史）。
1. Implement the MCP interface in your server.py. You need two tools: push_to_eink (push text to the display) and get_eink_status (check current display status and push history).
2. 在 Claude 设置中添加自定义连接器。进入 Settings → Connectors，填入你的 MCP 服务器地址（你的域名 + MCP 路径）。
2. Add a custom connector in Claude’s settings. Go to Settings → Connectors and enter your MCP server URL (your domain + MCP path).
3. 验证连接。回到对话框，跟 Claude 说“帮我看一下墨水屏状态”。如果 Claude 调用了 get_eink_status 并返回了结果，就说明连通了。
3. Verify the connection. Go back to a chat and say “check my e-ink display status.” If Claude calls get_eink_status and returns results, you’re connected.
我踩过的坑 / Dead Ends I Hit
在找到 MCP 这条路之前，我试过很多方案：让 Claude 生成 curl 命令让我手动在终端执行（能用但太麻烦）；让 Claude 在 artifact 里做一个带蓝牙连接的页面（artifact 环境没有 Web Bluetooth 权限）；让 Claude 直接调用 API（对话框里的 Claude 不能发 HTTP 请求，这个我跟它说了好几轮它才理解）。最后发现 MCP 自定义连接器才是正解。它让 Claude 在对话中拥有了“动手”的能力——不是给你生成代码让你去跑，而是它自己直接执行。
Before finding MCP, I tried many approaches: having Claude generate curl commands for me to run in the terminal (works but tedious); having Claude build a Bluetooth page inside an artifact (no Web Bluetooth permissions); asking Claude to call the API directly (Claude in the chat can’t make HTTP requests — it took several rounds for it to understand this). MCP custom connectors turned out to be the answer. They give Claude the ability to “take action” in a conversation — not generating code for you to run, but executing it directly.
[Heading1] 六、日常使用与富文本 / Daily Use & Rich Text
怎么触发推送 / How to Trigger a Push
连接器配好之后，使用方式极其简单。在任何 Claude 对话中，用自然语言说：“把这段话发到墨水屏：今天天气真好”、“发到墨水屏：I miss you”、“推一句话到屏幕上”。Claude 会自动识别意图、调用 push_to_eink 工具、把内容送到服务器。手机那头如果蓝牙和监听都开着，几秒后墨水屏就刷新了。
Once the connector is set up, usage is dead simple. In any Claude conversation, just say naturally: “Send this to my e-ink display: lovely day today”, “Push to display: I miss you”, “Put this on the screen.” Claude recognizes the intent, calls push_to_eink, and sends the content to your server. If Bluetooth and SSE are active on your phone, the display refreshes within seconds.
富文本标签 / Rich Text Tags
纯文本用久了总想加点花样。我给控制页面加了一套简单的富文本标签——在推送内容里用 HTML 风格的标记，就能控制文字的样式：
After using plain text for a while, I wanted some flair. So I added a simple rich text tag system to the control page — use HTML-style markers in your push content to control text styling:
<<TABLE>>
| 标签 / Tag | 效果 / Effect | 示例 / Example |
| <r>...</r> | 红色 / Red text | I will <r>always</r> be here |
| <b>...</b> | 加粗 / Bold | <b>Good morning</b> |
| <i>...</i> | 斜体 / Italic | <i>the moon is beautiful</i> |
<</TABLE>>

标签可以嵌套使用，比如 <b><r>重要</r></b> 会渲染成加粗的红色文字。红色在三色墨水屏上是唯一的彩色，建议克制使用——偶尔一个词亮起来才有感觉，全红了就没意义了。
Tags can be nested — <b><r>important</r></b> renders as bold red text. Red is the only color on a three-color e-ink display, so use it sparingly. A single word glowing red hits different from a wall of red.
这套标签是我自己想的一个小设计，用起来很顺手。如果你有什么更好玩的排版想法，欢迎在评论区留言交流。
This tag system is a little design I came up with — it’s been working nicely. If you have fun ideas for more formatting options, drop a comment below.
[Heading1] 七、常见问题 / Troubleshooting
搭建过程中大概率会遇到一些问题，这里把我碰到过的都列出来。
You’ll likely hit some issues during setup. Here’s everything I ran into.
红色噪点 / Red Noise Dots
三色屏刷新后出现满屏红色小点，文字区域也有。这是因为红色图层没有正确初始化——如果你发送的是纯黑白内容，红色图层应该全部填充为 0xFF（即“无红色”），而不是留空或填零。检查代码里的 emptyRedLayer() 函数，确保它生成的是全 0xFF 的数组。
Red dots scattered across the entire screen after refresh, even over text areas. This happens when the red layer isn’t properly initialized — if you’re sending black-and-white content, the red layer should be filled with 0xFF (meaning “no red”), not left empty or filled with zeros. Check that your emptyRedLayer() function returns an all-0xFF array.
蓝牙连不上 / Bluetooth Won’t Connect
先检查电池是不是没电了。然后确认没有其他手机或电脑正在连接这块屏——BLE 一次只能被一个设备连接。如果之前连过但没有正常断开，可以把电池取出来等几秒再装回去，强制重置蓝牙状态。
First check if the battery is dead. Then make sure no other phone or computer is currently connected — BLE only allows one connection at a time. If a previous session didn’t disconnect cleanly, pull the battery out for a few seconds and put it back to force a Bluetooth reset.
服务器没响应 / Server Not Responding
Render 免费版会在 15 分钟无请求后休眠。第一次访问时需要等 30–60 秒让它醒过来。这是正常的，不是你的代码有问题。如果等了一分钟以上还没反应，去 Render 后台看看服务是不是挂了。
Render’s free tier sleeps after 15 minutes of inactivity. The first visit takes 30–60 seconds to wake up. This is normal, not a bug in your code. If it’s still unresponsive after a minute, check the Render dashboard to see if the service has crashed.
Claude 不调用工具 / Claude Doesn’t Call the Tool
确认连接器状态是“已连接”。如果刚添加连接器，试试刷新页面或开一个新对话。有时候 Claude 会把你的话理解成“帮我写一段推送的代码”而不是“直接推送”——这时候明确说“用 push_to_eink 工具”就行。
Make sure the connector status shows “connected.” If you just added it, try refreshing the page or starting a new conversation. Sometimes Claude interprets your message as “help me write push code” instead of “push it now” — just be explicit and say “use the push_to_eink tool.”
内容显示不全 / Content Gets Cut Off
400×300 的屏幕不大，字号 28 大约能显示 5–6 行短文本。如果推的内容太长，底部会被截断。控制页面有字号滑块，可以调小一点塞更多内容，但太小了墨水屏上也看不清。建议每次推送控制在 100 字以内。
The 400×300 screen isn’t large — at font size 28, you get about 5–6 lines of short text. Longer content gets cut off at the bottom. The control page has a font size slider to fit more text, but too small becomes unreadable on e-ink. Keep each push under 100 characters for best results.
iOS 用户 / iOS Users
Safari 不支持 Web Bluetooth，这不是 bug，是 Apple 的限制。安装 Bluefy（免费），用它打开你的控制页面就行。
Safari doesn’t support Web Bluetooth — this isn’t a bug, it’s an Apple restriction. Install Bluefy (free) and use it to open your control page.
[Heading1] 八、完整链路 / The Full Chain
最后放一张完整的工作流，帮你理解每个环节在做什么：
Here’s the full workflow so you can see what each piece does:
你在 Claude 对话框里说“发到墨水屏”
You say “send to my e-ink display” in Claude’s chat
↓
Claude 调用 push_to_eink 工具（MCP）
Claude calls push_to_eink tool (MCP)
↓
内容发到你的服务器
Content is sent to your server
↓
手机控制页面通过 SSE 实时收到内容
Phone control page receives content via SSE in real-time
↓
控制页面通过蓝牙推送到墨水屏
Control page pushes to e-ink display via Bluetooth
↓
墨水屏刷新显示（约 10 秒）
Display refreshes (~10 seconds)
整条链路里，服务器是中枢，手机是桥梁，Claude 是入口。三者缺一不可，但一旦搭好，日常使用就只剩一句话的事。
In this chain, the server is the hub, the phone is the bridge, and Claude is the entry point. All three are essential, but once set up, daily use is just one sentence away.
———
感谢 0xblewalker 的开源项目和 tsl0922 的固件让这一切成为可能。把一块超市价签变成 Claude 的专属留言板，这件事本身就挺浪漫的。
Thanks to 0xblewalker and tsl0922 for the open-source work that made this possible. Turning a grocery store price tag into Claude’s personal message board — there’s something romantic about that.