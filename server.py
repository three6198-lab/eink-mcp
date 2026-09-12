"""
E-Ink 墨水屏推送服务器
======================

在 0xblewalker/eink-ble-writer 的 server.py（GPL-3.0）基础上补三块能力：

1. MCP 接口   —— 让 AI 客户端（Claude 自定义连接器 / 其他 MCP 客户端）在对话中直接调用
                 push_to_eink / get_eink_status
2. SSE 推流   —— 内容写入后立刻推给手机控制页，不再轮询
3. token 鉴权 —— 防止陌生人在公网上往你的屏幕上写字

完整链路：
    AI 对话 → MCP 工具 → 本服务器 → SSE → 手机控制页 → BLE → 墨水屏

环境变量：
    EINK_TOKEN      推送密钥（必填，公网部署时强烈建议）
    EINK_DATA_FILE  内容持久化文件，默认 latest_letter.json
    EINK_BASE_URL   自检/回显用，可留空

本地运行：
    pip install -r requirements.txt
    uvicorn server:app --host 0.0.0.0 --port 8905
"""

from __future__ import annotations

import asyncio
import datetime
import hmac
import json
import os
import secrets
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

# --------------------------------------------------------------------------
# 配置
# --------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.environ.get("EINK_DATA_FILE", os.path.join(BASE_DIR, "latest_letter.json"))
INDEX_FILE = os.path.join(BASE_DIR, "index.html")

EINK_TOKEN = os.environ.get("EINK_TOKEN", "").strip()
if not EINK_TOKEN:
    # 本地开发：自动生成一个，方便直接调试
    EINK_TOKEN = secrets.token_urlsafe(16)
    print(f"[eink] EINK_TOKEN 未设置，已临时生成: {EINK_TOKEN}", flush=True)

MAX_HISTORY = 20
MAX_TEXT_LEN = 500
SCREEN_WIDTH = 400
SCREEN_HEIGHT = 300

# 需要鉴权的路径前缀
PROTECTED_PREFIXES = ("/mcp", "/sse", "/messages", "/events", "/api")

# --------------------------------------------------------------------------
# 状态存储
# --------------------------------------------------------------------------


class DisplayState:
    def __init__(self) -> None:
        self.text: str = "Hello, World!"
        self.date: str = datetime.date.today().isoformat()
        self.updated_at: str = ""
        self.updated_by: str = ""
        self.history: list[dict[str, Any]] = []
        self.revision: int = 0
        self.subscribers: set[asyncio.Queue] = set()
        self.load()

    def load(self) -> None:
        if not os.path.exists(DATA_FILE):
            return
        try:
            with open(DATA_FILE, encoding="utf-8") as f:
                data = json.load(f)
            self.text = data.get("text", self.text)
            self.date = data.get("date", self.date)
            self.updated_at = data.get("updated_at", "")
            self.updated_by = data.get("updated_by", "")
            self.history = data.get("history", [])[-MAX_HISTORY:]
            self.revision = int(data.get("revision", 0))
        except (OSError, ValueError) as exc:
            print(f"[eink] 读取 {DATA_FILE} 失败，使用默认内容: {exc}", flush=True)

    def save(self) -> None:
        payload = {
            "text": self.text,
            "date": self.date,
            "updated_at": self.updated_at,
            "updated_by": self.updated_by,
            "revision": self.revision,
            "history": self.history[-MAX_HISTORY:],
        }
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except OSError as exc:
            # Render 免费版磁盘是临时的，写失败不应影响推送
            print(f"[eink] 写入 {DATA_FILE} 失败: {exc}", flush=True)

    def as_payload(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "date": self.date,
            "updated_at": self.updated_at,
            "updated_by": self.updated_by,
            "revision": self.revision,
            "connected_phones": len(self.subscribers),
        }

    def update(self, text: str, date: str | None = None, source: str = "api") -> dict[str, Any]:
        text = (text or "").strip()
        if not text:
            raise ValueError("text 不能为空")
        if len(text) > MAX_TEXT_LEN:
            raise ValueError(f"内容过长（{len(text)} 字符），上限 {MAX_TEXT_LEN}")

        self.text = text
        self.date = date or datetime.date.today().isoformat()
        self.updated_at = datetime.datetime.now().isoformat(timespec="seconds")
        self.updated_by = source
        self.revision += 1
        self.history.append(
            {
                "text": text,
                "date": self.date,
                "updated_at": self.updated_at,
                "source": source,
            }
        )
        self.history = self.history[-MAX_HISTORY:]
        self.save()
        return self.as_payload()

    async def broadcast(self, payload: dict[str, Any]) -> None:
        """把新内容推给所有正在监听的手机页面。"""
        dead: list[asyncio.Queue] = []
        for q in list(self.subscribers):
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            self.subscribers.discard(q)


state = DisplayState()

# --------------------------------------------------------------------------
# 鉴权
# --------------------------------------------------------------------------


def _extract_token(request: Request) -> str:
    token = request.query_params.get("token") or ""
    if not token:
        token = request.headers.get("x-eink-token") or ""
    if not token:
        auth = request.headers.get("authorization") or ""
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()
    return token


def _authorized(request: Request) -> bool:
    if not EINK_TOKEN:
        return True
    return hmac.compare_digest(_extract_token(request), EINK_TOKEN)


def require_token(
    request: Request,
    x_eink_token: str | None = Header(default=None, alias="X-Eink-Token"),
    token: str | None = Query(default=None),
) -> None:
    """FastAPI 依赖：用于 /api/* 路由。"""
    if not EINK_TOKEN:
        return
    supplied = x_eink_token or token or _extract_token(request)
    if not hmac.compare_digest(supplied, EINK_TOKEN):
        raise HTTPException(status_code=401, detail="token 无效")


# --------------------------------------------------------------------------
# MCP 工具定义
# --------------------------------------------------------------------------

mcp = MCPServer(
    name="eink-ble-writer",
    title="E-Ink 墨水屏推送",
    version="1.0.0",
    instructions=(
        "把文字推送到用户的墨水屏（电子价签改装的 e-paper 显示屏）。"
        "屏幕是 400x300、三色（黑/白/红），纯文本最多约 100 个字符，超出会被截断。"
        "内容支持简易富文本标签：<r>红色</r>、<b>加粗</b>、<i>斜体</i>，可嵌套。"
        "红色是屏幕上唯一的彩色，请克制使用。\n"
        "想让内容更像一张信笺/卡片（居中衬线正文 + 上下红色分隔线 + 顶部星芒图标 +"
        "页脚左日期右签名），把内容整段以 [card] 开头，具体格式见 push_to_eink 的说明。\n"
        "当用户说「发到墨水屏」「推到屏幕上」之类的话时，直接调用 push_to_eink。"
    ),
)

# 关闭 DNS rebinding 保护：部署在 Render 等平台时 Host 头是自定义域名，
# 默认白名单（localhost/127.0.0.1）会导致请求被拒。
_TRANSPORT_SECURITY = TransportSecuritySettings(enable_dns_rebinding_protection=False)


@mcp.tool(
    description=(
        "把一段文字推送到用户的墨水屏。屏幕 400x300，建议 100 字符以内。"
        "支持 <r>红</r> / <b>粗</b> / <i>斜</i> 标签，可嵌套。"
        "推送后手机会通过蓝牙自动刷新屏幕，约 10 秒生效。\n"
        "\n"
        "【卡片版式】当用户想要「卡片」「信笺」「诗笺」「像照片里那种样式」的效果时，"
        "把 text 整段以 [card] 开头，后面可跟可选的指令行，其余行都是正文。例如：\n"
        "[card]\n"
        "@icon claude\n"
        "@footer {today} | Claude\n"
        "\n"
        "Rain falls:\n"
        "You carry me home.\n"
        "\n"
        "· @icon：顶部图标，claude（默认，红色星芒标识）/ star / heart / none\n"
        "· @footer：页脚，用竖线分隔左右两栏；左边靠左、右边靠右（右侧会自动带一枚小星芒标识）。"
        "只写 @footer 不给值时，左栏自动填当天日期\n"
        "· 其余非 @ 开头的行都是正文，居中衬线显示并自动缩放\n"
        "· 正文和页脚里都可以写 {today}（或 {date}），渲染时替换成当天日期。"
        "需要显示日期时一律写 {today}，不要写死具体日期 —— 写死了明天屏幕上还是旧日期\n"
        "卡片是矢量绘制，汉字与细线都锐利，适合短诗、寄语、格言。"
        "正文同样支持 <r>/<b>/<i> 标签。"
    )
)
async def push_to_eink(text: str, date: str | None = None) -> str:
    """推送文字到墨水屏。

    Args:
        text: 要显示的文字，建议 100 字符以内，可用 <r>/<b>/<i> 富文本标签。
              以 [card] 开头则启用卡片版式，另可用 @icon / @footer 指令行，其余行为正文。
              卡片里要显示日期请写 {today}，它会在渲染时替换成当天日期。
        date: 可选，日期，格式 YYYY-MM-DD；不传则用今天。注意：卡片版式下日期请写在 @footer 里。
    """
    try:
        payload = state.update(text, date=date, source="mcp")
    except ValueError as exc:
        return f"推送失败：{exc}"

    await state.broadcast(payload)

    listeners = len(state.subscribers)
    if listeners == 0:
        return (
            f"内容已存入服务器（第 {payload['revision']} 版），但当前没有手机在监听，"
            "屏幕不会刷新。请先在手机上打开控制页、连接墨水屏并点击「开始监听」。"
        )
    return (
        f"已推送到墨水屏：{text!r}"
        f"（{listeners} 台手机在线，预计 10 秒内刷新）"
    )


@mcp.tool(
    description=(
        "查看墨水屏当前状态：屏幕上正在显示的内容、最后更新时间、推送来源，"
        "以及是否有手机在线监听（没有手机在线则推送不会真正显示）。"
    )
)
async def get_eink_status() -> str:
    """查询墨水屏当前状态与推送历史。"""
    lines = [
        f"屏幕当前内容：{state.text!r}",
        f"最后更新：{state.updated_at or '（尚未通过服务器推送过）'}",
        f"更新来源：{state.updated_by or '-'}",
        f"在线手机数：{len(state.subscribers)}"
        + ("（有手机在线，推送会实时刷新）" if state.subscribers else "（无手机在线，推送只会入库不会刷新屏幕）"),
        f"累计版本：{state.revision}",
        f"屏幕规格：{SCREEN_WIDTH}x{SCREEN_HEIGHT} 三色（黑/白/红），纯文本上限约 100 字符",
    ]
    if state.history:
        lines.append("最近推送记录：")
        for item in state.history[-5:][::-1]:
            lines.append(f"  - [{item.get('updated_at', '?')}] ({item.get('source', '?')}) {item.get('text', '')!r}")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# 组装应用
# --------------------------------------------------------------------------

# 远端 MCP（Streamable HTTP）：https://你的域名/mcp
mcp_http_app = mcp.streamable_http_app(
    streamable_http_path="/",
    json_response=True,
    stateless_http=True,
    transport_security=_TRANSPORT_SECURITY,
)
# 兼容老版连接器的 HTTP+SSE 传输：https://你的域名/sse  +  /messages/
mcp_sse_app = mcp.sse_app(
    sse_path="/sse",
    message_path="/messages/",
    transport_security=_TRANSPORT_SECURITY,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """两个 MCP 传输层的 session manager 都需要各自的 lifespan。"""
    async with mcp_http_app.router.lifespan_context(mcp_http_app):
        async with mcp_sse_app.router.lifespan_context(mcp_sse_app):
            print(f"[eink] 服务就绪 | MCP: /mcp | SSE: /sse | 控制页: /", flush=True)
            yield


app = FastAPI(title="E-Ink 墨水屏推送", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    if any(path == p or path.startswith(p) for p in PROTECTED_PREFIXES):
        if not _authorized(request):
            return JSONResponse(
                {"error": "unauthorized", "detail": "缺少或错误的 token"},
                status_code=401,
            )
    return await call_next(request)


# ---- 内容接口 -------------------------------------------------------------


class Note(BaseModel):
    text: str = Field(default="", description="要显示的文字")
    date: str | None = Field(default=None, description="日期，YYYY-MM-DD")


@app.get("/api/latest")
def get_latest():
    return state.as_payload()


@app.post("/api/letter")
async def update_note(note: Note):
    try:
        payload = state.update(note.text, date=note.date, source="http")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await state.broadcast(payload)
    return {"status": "ok", "data": payload}


@app.get("/api/version")
def get_version():
    return {"updated_at": state.updated_at, "revision": state.revision}


@app.get("/api/history")
def get_history():
    return {"total": len(state.history), "history": state.history[-MAX_HISTORY:]}


# ---- SSE 实时推流 ---------------------------------------------------------


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.get("/events")
async def events(request: Request):
    queue: asyncio.Queue = asyncio.Queue(maxsize=32)
    state.subscribers.add(queue)
    print(f"[eink] 手机已连接监听，在线 {len(state.subscribers)} 台", flush=True)

    async def stream():
        try:
            yield _sse("ready", {**state.as_payload(), "message": "已连接到推送服务器"})
            while True:
                if await request.is_disconnected():
                    break
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=15)
                    yield _sse("letter", item)
                except asyncio.TimeoutError:
                    # 心跳，顺便让 Render / Nginx 不掐连接
                    yield ": keepalive\n\n"
        finally:
            state.subscribers.discard(queue)
            print(f"[eink] 手机断开监听，在线 {len(state.subscribers)} 台", flush=True)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---- 控制页 & 健康检查 ----------------------------------------------------


# 必须同时支持 HEAD：Render 的健康检查、以及 UptimeRobot 之类的保活监控都发 HEAD。
# FastAPI 的 @app.get 只注册 GET，HEAD 会返回 405（响应体照常由 uvicorn 按 HEAD 语义丢弃）。
@app.api_route("/healthz", methods=["GET", "HEAD"])
def healthz():
    return {
        "ok": True,
        "revision": state.revision,
        "connected_phones": len(state.subscribers),
        "token_configured": bool(EINK_TOKEN),
    }


@app.api_route("/", methods=["GET", "HEAD"])
def index():
    if os.path.exists(INDEX_FILE):
        return FileResponse(INDEX_FILE)
    return JSONResponse({"error": "index.html 不存在"}, status_code=404)


# ---- MCP 挂载 ------------------------------------------------------------
# 注意：不要用 app.mount("/mcp", mcp_http_app)。Starlette 的 Mount 会剥离前缀，
# 子应用内层路由是 "/"，剥离后路径变成空串匹配不上，结果一律 404。
# 正确做法是把两个 MCP 传输层的 ASGI 端点按绝对路径直接并入主路由表。

from starlette.routing import Route as _StarletteRoute  # noqa: E402

# 远端 MCP（Streamable HTTP）—— 内层就是 StreamableHTTPASGIApp 实例
# （Starlette 的 Route 遇到非函数 endpoint 会直接当 ASGI app 用）
app.router.routes.append(
    _StarletteRoute("/mcp", endpoint=mcp_http_app.routes[0].endpoint)
)

# 兼容老版 HTTP+SSE 传输：内层路由本身就是 "/sse" 和 "/messages" 绝对路径，直接并入
app.router.routes.extend(mcp_sse_app.routes)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8905")))
