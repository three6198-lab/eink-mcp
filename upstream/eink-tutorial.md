# E-Ink BLE 情书机：从零开始的完整教程

> 把一块超市货架的电子价签，变成你的私人墨水屏留言板。通过手机蓝牙推送文字和图片，超低功耗，一颗纽扣电池续航数月。

---

## 这是什么？

一个基于 **Web Bluetooth** 的墨水屏（E-Ink）写入工具。你可以用手机浏览器直接连接墨水屏，把文字或图片推送上去。不需要任何 App，不需要额外硬件，打开网页就能用。

**核心组件：**

- 一块带 nRF5x 芯片的电子墨水屏（最常见的来源是超市电子价签）
- 刷入 [EPD-nRF5](https://github.com/tsl0922/EPD-nRF5) 开源固件
- 一个纯前端 HTML 页面（本项目提供，无需后端服务器）

**平台兼容性：**

| 平台 | 浏览器 | 状态 |
|------|--------|------|
| Android | Chrome 56+ | ✅ 原生支持 Web Bluetooth |
| macOS | Chrome / Edge | ✅ 原生支持 |
| Windows | Chrome / Edge | ✅ 原生支持 |
| iOS | Bluefy 浏览器 | ✅ 需安装 Bluefy（Safari 不支持 Web Bluetooth） |

---

## 第一步：获取硬件

### 关于墨水屏的选择

你需要的不是特定品牌的价签，而是搭载以下 MCU 芯片之一的电子墨水屏：

- **nRF52811**（盒马/阿里巴巴价签常用，推荐）
- **nRF52810**（司非品牌常用）
- **nRF51822**（老吴 4.2 寸黑白版）
- **nRF51802**（老吴 4.2 寸三色版）

**常见来源：**

1. **闲鱼/淘宝**：搜索"电子价签 墨水屏"或"ESL 电子标签"，价格通常 5-30 元不等
2. **拆机屏**：从下架的超市电子价签中回收
3. **Waveshare 等品牌**：购买带 nRF 芯片的开发板（价格较高但文档齐全）

**购买前确认：**

- 芯片型号是否为上述 nRF5x 系列
- 屏幕驱动芯片是否为 SSD16xx 或 UC81xx 系列
- 屏幕尺寸（常见 4.2 寸 400×300，也有 2.9 寸、7.5 寸等）
- 颜色类型：黑白（BW）或三色（Black/White/Red）

### 刷写固件

墨水屏需要刷入 EPD-nRF5 固件才能通过蓝牙接收图像。

**你需要：**

- J-Link 或 DAPLink 编程器（淘宝 10-30 元）
- 杜邦线若干
- 焊接工具（如果价签没有引出调试接口）

**步骤：**

1. 找到价签板上的 SWD 调试接口（通常是 SWDIO、SWCLK、VCC、GND 四个焊点）
2. 用杜邦线连接编程器
3. 按 [EPD-nRF5 文档](https://github.com/tsl0922/EPD-nRF5/blob/main/docs/develop.md) 的步骤：
   - 先擦除芯片
   - 刷入 SoftDevice 蓝牙协议栈（只需一次）
   - 编译并刷入固件
4. 刷完后，墨水屏会通过蓝牙广播自己，名称通常为 `EPD-xxxx`

> 💡 如果你购买的是已经刷好固件的屏幕（闲鱼上有卖家提供），可以跳过这一步。

---

## 第二步：使用前端工具

### 方式一：纯离线使用（推荐新手）

直接用本项目提供的 `eink-ble-writer.html` 文件：

1. 把 HTML 文件保存到手机/电脑
2. 用支持 Web Bluetooth 的浏览器打开（Android 用 Chrome，iOS 用 Bluefy）
3. 输入文字或上传图片
4. 点击 "Connect" 搜索并连接墨水屏
5. 点击 "Send to Display" 发送

这个文件完全离线可用，不需要服务器，不需要网络。

### 方式二：搭配后端服务器（进阶玩法）

如果你想实现"远程推送"——比如在电脑上写内容，自动同步到家里的墨水屏——可以搭建一个简单的后端：

```python
# server.py — 最简后端示例
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
import json, os, datetime

app = FastAPI()
DATA_FILE = 'latest_letter.json'

class Note(BaseModel):
    text: str = ''
    date: Optional[str] = None

@app.get('/api/latest')
def get_latest():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return {'text': 'Hello, World!', 'date': datetime.date.today().isoformat()}

@app.post('/api/letter')
def update_note(note: Note):
    data = note.model_dump()
    if not data.get('date'):
        data['date'] = datetime.date.today().isoformat()
    data['updated_at'] = datetime.datetime.now().isoformat()
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, ensure_ascii=False)
    return {'status': 'ok', 'data': data}

# 运行: uvicorn server:app --host 0.0.0.0 --port 8905
```

前端通过轮询 `/api/latest` 获取最新内容，检测到更新后自动推送到墨水屏。

---

## 第三步：理解 BLE 协议

如果你想自己写客户端或做二次开发，需要了解 BLE 通信协议。

### 蓝牙服务

| 名称 | UUID |
|------|------|
| EPD Service | `62750001-d828-918d-fb46-b6c11c675aec` |
| EPD Characteristic (Write) | `62750002-d828-918d-fb46-b6c11c675aec` |

### 命令格式

每个 BLE 写入操作的第一个字节是命令 ID：

| 命令 | ID | 说明 |
|------|----|------|
| INIT | `0x01` | 初始化显示驱动 |
| CLEAR | `0x02` | 清屏 |
| REFRESH | `0x05` | 刷新显示（将 RAM 内容显示到屏幕） |
| WRITE_IMAGE | `0x30` | 写入图像数据到 RAM |
| SLEEP | `0x06` | 进入睡眠模式 |

### 图像发送流程

```
1. 发送 INIT (0x01)
2. 等待 200ms
3. 发送 BW 图层（黑白数据）
4. 发送 Red 图层（红色数据，仅三色屏）
5. 发送 REFRESH (0x05)
```

### WRITE_IMAGE 数据格式

```
[0x30] [flag] [image_data...]
```

**flag 字节的含义：**

- 高 4 位（upper nibble）：`0x00` = 该图层第一个分包，`0xF0` = 后续分包
- 低 4 位（lower nibble）：`0x0F` = BW 图层（RAM1），`0x00` = Red 图层（RAM2）

**组合示例：**

| Flag | 含义 |
|------|------|
| `0x0F` | BW 图层，第一个分包 |
| `0xFF` | BW 图层，后续分包 |
| `0x00` | Red 图层，第一个分包 |
| `0xF0` | Red 图层，后续分包 |

### 图像数据格式

每个图层是一个 1bpp（每像素1位）的位图：

**BW 图层：**
- `1` = 白色像素
- `0` = 黑色像素

**Red 图层：**
- `0` = 红色像素
- `1` = 非红色像素

数据按行扫描，每 8 个像素打包成一个字节，高位在前（MSB first）。每行的字节数为 `ceil(width / 8)`。

### JavaScript 实现参考

```javascript
// Canvas 像素 → EPD 位图
function canvasToEPD(canvas) {
  const ctx = canvas.getContext('2d');
  const w = canvas.width, h = canvas.height;
  const data = ctx.getImageData(0, 0, w, h).data;
  const byteWidth = Math.ceil(w / 8);
  const bwData  = new Uint8Array(byteWidth * h);
  const redData = new Uint8Array(byteWidth * h);

  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const i = (y * w + x) * 4;
      const r = data[i], g = data[i+1], b = data[i+2];
      const gray = Math.round(0.299*r + 0.587*g + 0.114*b);
      const byteIdx = y * byteWidth + (x >> 3);
      const bitIdx  = 7 - (x & 7);

      if (gray >= 140) bwData[byteIdx] |= (1 << bitIdx);

      const isRed = r > 160 && r > g && r > b;
      if (!isRed) redData[byteIdx] |= (1 << bitIdx);
    }
  }
  return { bwData, redData };
}

// 分包发送单个图层
async function sendLayer(characteristic, data, stepFlag, mtu) {
  for (let i = 0; i < data.length; i += mtu) {
    const chunk = data.slice(i, i + mtu);
    const firstFlag = i === 0 ? 0x00 : 0xF0;
    const flag = stepFlag | firstFlag;
    const payload = new Uint8Array([0x30, flag, ...chunk]);
    await characteristic.writeValueWithResponse(payload);
  }
}
```

---

## 常见问题

### Q: iOS 上 Safari 能用吗？

不能。Safari 不支持 Web Bluetooth API。iOS 用户需要安装 [Bluefy](https://apps.apple.com/app/bluefy-web-ble-browser/id1492822055) 浏览器（免费）。

### Q: 一次刷新要多久？

- 黑白屏：约 2-3 秒
- 三色屏（黑白红）：约 15 秒（红色墨水需要更长的驱动时间）
- BLE 数据传输：约 3-8 秒（取决于 MTU 和屏幕尺寸）

### Q: 电池能用多久？

墨水屏的特性是只在刷新时耗电，显示内容时几乎零功耗。一颗 CR2450 纽扣电池通常可以支持数百到数千次刷新，日常使用可达数月。

### Q: 怎么判断价签用的是什么芯片？

- 拆开看 PCB 上的芯片丝印
- 或用 nRF Connect App（iOS/Android）扫描蓝牙广播，看设备信息
- 刷好固件后，设备会广播为 `EPD-xxxx`

### Q: 支持中文显示吗？

Canvas 渲染支持任何 Unicode 字符，包括中文。但需要注意：
- 确保使用的字体包含中文字符（如 Noto Serif SC）
- 墨水屏分辨率有限（4.2 寸通常为 400×300），中文字号不宜太小
- 在线字体需要网络，离线使用建议用系统自带字体

### Q: 能显示图片吗？

可以。前端工具支持上传图片，会自动缩放到屏幕尺寸并进行抖动处理（dithering）。支持三种抖动算法：
- **Threshold**：简单阈值，适合高对比度图像
- **Floyd-Steinberg**：经典误差扩散，适合照片
- **Atkinson**：保留更多对比度，适合线条图

---

## 项目结构

```
eink-ble-writer.html    ← 通用前端工具（完全独立，无需后端）
server.py               ← 可选的后端服务器（用于远程推送）
```

### 前端代码关键模块

| 模块 | 功能 |
|------|------|
| BLE Connection | Web Bluetooth API 连接管理、MTU 协商 |
| Text Renderer | Canvas 文字渲染（字体/大小/颜色/对齐可配置） |
| Image Processor | 图片加载、缩放、三色/黑白抖动 |
| EPD Encoder | Canvas 像素 → 1bpp 位图转换 |
| BLE Sender | 分包发送、进度显示 |

---

## 致谢

- [tsl0922/EPD-nRF5](https://github.com/tsl0922/EPD-nRF5) — 墨水屏固件
- [Web Bluetooth API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Bluetooth_API) — 浏览器蓝牙标准
- [Bluefy](https://apps.apple.com/app/bluefy-web-ble-browser/id1492822055) — iOS Web Bluetooth 浏览器

---

*Made with ♥ — 把科技变成温柔的载体。*
