# E-Ink BLE Writer

A standalone Web Bluetooth tool for writing text and images to nRF5x e-paper displays. No app required 鈥?open the HTML file in your browser and connect.

![E-Ink Display Demo](docs/demo.jpg)

## Features

- **Text mode**: Type messages with configurable font, size, alignment, and color (black/red)
- **Image mode**: Upload images with Floyd-Steinberg / Atkinson dithering
- **Three-color support**: Black/White/Red displays (and B/W only mode)
- **Configurable display size**: Works with 4.2", 2.9", 7.5" and other resolutions
- **Fully offline**: Single HTML file, no server or internet required
- **Cross-platform**: Android (Chrome), macOS/Windows (Chrome/Edge), iOS (Bluefy browser)

## Quick Start

1. Flash your e-paper display with [EPD-nRF5](https://github.com/tsl0922/EPD-nRF5) firmware
2. Open `eink-ble-writer.html` in a Web Bluetooth-capable browser
3. Click **Connect** and select your display
4. Type your message or upload an image
5. Click **Send to Display**

## Supported Hardware

Any electronic shelf label (ESL) running EPD-nRF5 firmware with:

| MCU | Common Source |
|-----|--------------|
| nRF52811 | Hema / Alibaba ESL |
| nRF52810 | Sifei ESL |
| nRF51822 | Laowu 4.2" B/W |
| nRF51802 | Laowu 4.2" B/W/Red |

Display drivers: SSD16xx, UC81xx series (black/white and three-color).

## BLE Protocol

| Item | Value |
|------|-------|
| Service UUID | `62750001-d828-918d-fb46-b6c11c675aec` |
| Characteristic UUID | `62750002-d828-918d-fb46-b6c11c675aec` |
| CMD_INIT | `0x01` |
| CMD_WRITE_IMAGE | `0x30` |
| CMD_REFRESH | `0x05` |

See [PROTOCOL.md](PROTOCOL.md) for full protocol documentation.

## iOS Support

Safari does not support Web Bluetooth. iOS users need [Bluefy](https://apps.apple.com/app/bluefy-web-ble-browser/id1492822055) (free).

## Optional: Remote Push Server

For remote updates (e.g., push messages from your computer to a display at home), see `server.py` 鈥?a minimal FastAPI backend that the frontend can poll for new content.

## Acknowledgments

This project is a Web Bluetooth client for the excellent [EPD-nRF5](https://github.com/tsl0922/EPD-nRF5) firmware by [@tsl0922](https://github.com/tsl0922), which is licensed under GPL-3.0. The firmware handles all e-paper display driving and BLE communication.

This client (the HTML/JS code in this repository) is an independent work that communicates with EPD-nRF5 firmware over Bluetooth Low Energy, and is released under the GPL-3.0 License.

## License

GPL-3.0 License. See [LICENSE](LICENSE) for details.