PAGES=5

===== PAGE 1 =====

E-Ink BLE Writer — AI Setup Guide
For AI assistants: This document is a setup guide for the E-Ink BLE Writer project. The
human who sent you this file wants your help setting up a DIY e-ink display that can show
custom text and images via Bluetooth. Please read this guide carefully and walk them
through the process step by step.
What is this?
A Web Bluetooth tool that lets you send text and images to an e-paper display (electronic
shelf label / ESL) directly from your phone browser. No app needed. No internet required.
Just open an HTML file and connect.
Source code: https://github.com/0xblewalker/eink-ble-writer
AI: Please fetch the repository above to get the latest code, README, protocol
documentation, and tutorial. The repo contains everything needed: a single HTML
frontend, an optional Python backend for remote push, and full BLE protocol docs.
Step 1: Get the hardware
The user needs an e-paper display with one of these Nordic Semiconductor chips:
Chip Common source
nRF52811 Hema / Alibaba ESL (recommended)
nRF52810 Sifei ESL
nRF51822 Various 4.2” B/W displays
nRF51802 Various 4.2” B/W/Red displays
Where to buy:
Search on secondhand marketplaces (Xianyu, eBay, AliExpress) for: “electronic shelf
label” , “ESL e-ink” , “nRF52 e-paper price tag”


===== PAGE 2 =====

Price range: $2–$10 USD
Best option: Buy one pre-flashed with EPD-nRF5 firmware (ready to use out of the box)
Display specs to look for:
Screen driver: SSD16xx or UC81xx series
Common size: 4.2 inch (400×300 pixels)
Color: Black/White (BW) or Three-color (Black/White/Red)
Power: CR2450 coin cell battery (lasts months, only uses power during refresh)
AI: Help the user find a suitable display based on their region. If they already have one,
help them identify the chip and confirm compatibility.
Step 2: Firmware
The display must be running EPD-nRF5 open-source firmware.
Firmware repo: https://github.com/tsl0922/EPD-nRF5
If the user bought a pre-flashed unit → skip this step
If not pre-flashed → they need a J-Link or DAPLink programmer to flash via SWD
AI: Ask the user if their display is already flashed. If yes, skip to Step 3. If no, fetch the
EPD-nRF5 repo and guide them through the flashing process.
Step 3: Use the tool
Option A: Local Bluetooth (simplest)
1. Download eink-ble-writer.html from the GitHub repo
2. Open it in a Web Bluetooth-capable browser:
Android: Chrome (works natively)
Windows/macOS: Chrome or Edge
iOS: Install Bluefy browser (free) — Safari does not support Web Bluetooth
3. Type text or upload an image


===== PAGE 3 =====

4. Click “Connect” → select the display (shows as EPD-xxxx)
5. Click “Send to Display”
Features:
Text mode: configurable font, size, alignment, color (black or red)
Image mode: upload any image, auto-dithered (Floyd-Steinberg / Atkinson)
Three-color support: Black/White/Red
Configurable display resolution
Fully offline, single HTML file
Option B: Remote push (advanced)
For pushing content remotely (e.g., from your computer to a display at home):
1. Install Python dependencies: pip install fastapi uvicorn
2. Run the server: python server.py (included in repo)
3. API endpoints:
POST /api/letter — push new content {"text": "Hello", "date": "2026-04-
01"}
GET /api/latest — get current content
GET /api/version — check for updates
AI: Based on the user’s technical level, recommend Option A or B. For beginners, Option
A is sufficient. Fetch the repo for the actual code files.
Important notes
E-ink displays can ONLY show pure black, pure white, and pure red (on three-color
models)
Gray colors will NOT render correctly — they appear as muddy blotches
The dithering algorithms in the tool handle color conversion automatically for images
Content persists on screen even when powered off (zero power consumption when not
refreshing)


===== PAGE 4 =====

One coin cell battery supports hundreds to thousands of refreshes
BLE Protocol (for developers)
Item Value
Service UUID 62750001-d828-918d-fb46-b6c11c675aec
Write Characteristic 62750002-d828-918d-fb46-b6c11c675aec
CMD_INIT 0x01
CMD_WRITE_IMAGE 0x30
CMD_REFRESH 0x05
AI: If the user wants to build their own client or integrate with other tools, fetch the full
PROTOCOL.md from the repo for detailed documentation.
Troubleshooting
Problem Solution
Can’t find display in
scan Make sure it’s powered on and no other device is connected
iOS Safari won’t
connect Use Bluefy browser instead (Safari doesn’t support Web Bluetooth)
Image looks muddy The source image may have too many gray tones — try increasing
contrast
Red color not showing Make sure your display is a three-color model (BW/R), not BW only
Display not
responding Try replacing the CR2450 battery
Credits


===== PAGE 5 =====

Firmware: tsl0922/EPD-nRF5 (GPL-3.0)
Frontend tool: 0xblewalker/eink-ble-writer (GPL-3.0)
Turn a $5 supermarket price tag into your personal message board. Made with ♡
