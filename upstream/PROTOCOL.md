# BLE Protocol Reference

Full documentation of the BLE communication protocol used by EPD-nRF5 firmware.

## Service & Characteristic

| Name | UUID |
|------|------|
| EPD Service | `62750001-d828-918d-fb46-b6c11c675aec` |
| EPD Write Characteristic | `62750002-d828-918d-fb46-b6c11c675aec` |
| App Version Characteristic | `62750003-d828-918d-fb46-b6c11c675aec` |

## Commands

Each BLE write begins with a 1-byte command ID:

| Command | ID | Description |
|---------|----|-------------|
| SET_PINS | `0x00` | Set EPD pin mapping |
| INIT | `0x01` | Initialize display driver |
| CLEAR | `0x02` | Clear screen |
| SEND_COMMAND | `0x03` | Send raw command to EPD |
| SEND_DATA | `0x04` | Send raw data to EPD |
| REFRESH | `0x05` | Display RAM content on screen |
| SLEEP | `0x06` | Enter sleep mode |
| SET_TIME | `0x20` | Set time (Unix timestamp) |
| WRITE_IMAGE | `0x30` | Write image data to RAM |
| SET_CONFIG | `0x90` | Set full EPD config |
| SYS_RESET | `0x91` | MCU reset |
| SYS_SLEEP | `0x92` | MCU enter deep sleep |
| CFG_ERASE | `0x99` | Erase config and reset |

## Image Transfer

### Workflow

`
1. Send INIT (0x01)                    # Initialize display
2. Wait ~200ms
3. Send BW layer via WRITE_IMAGE       # Black/white data
4. Send Red layer via WRITE_IMAGE      # Red data (three-color only)
5. Send REFRESH (0x05)                 # Update screen
`

### WRITE_IMAGE Packet Format

`
[0x30] [flag_byte] [image_data...]
`

The `flag_byte` encodes two pieces of information:

- **Upper nibble** (bits 7-4): `0x00` = first chunk of this layer, `0xF0` = continuation
- **Lower nibble** (bits 3-0): `0x0F` = BW layer (RAM1), `0x00` = Red layer (RAM2)

| Flag | Meaning |
|------|---------|
| `0x0F` | BW layer, first chunk |
| `0xFF` | BW layer, continuation |
| `0x00` | Red layer, first chunk |
| `0xF0` | Red layer, continuation |

### Pixel Encoding

Image data is 1bpp (1 bit per pixel), packed 8 pixels per byte, MSB first.

**BW Layer (RAM1):**
- Bit = 1: White pixel
- Bit = 0: Black pixel

**Red Layer (RAM2):**
- Bit = 0: Red pixel
- Bit = 1: Non-red pixel

Each row is `ceil(width / 8)` bytes. Total layer size = `ceil(width / 8) * height` bytes.

### Chunking

Data is split into chunks based on the negotiated MTU size (typically 242 bytes). The device reports its MTU via notifications as `mtu=NNN` after connection.

### Example (JavaScript)

`javascript
const CMD_INIT = 0x01, CMD_WRITE = 0x30, CMD_REFRESH = 0x05;

async function sendLayer(char, data, layerFlag, mtu) {
  for (let i = 0; i < data.length; i += mtu) {
    const chunk = data.slice(i, i + mtu);
    const isFirst = i === 0 ? 0x00 : 0xF0;
    const flag = layerFlag | isFirst;
    await char.writeValueWithResponse(
      new Uint8Array([CMD_WRITE, flag, ...chunk])
    );
  }
}
`

## MTU Negotiation

After connecting and enabling notifications on the write characteristic, send `CMD_INIT`. The device responds with a notification containing `mtu=NNN` where NNN is the negotiated ATT MTU. Subtract 2 for the command + flag bytes to get the maximum chunk size.

## References

- [EPD-nRF5 firmware source](https://github.com/tsl0922/EPD-nRF5)
- [SSD1619A datasheet](https://github.com/tsl0922/EPD-nRF5/blob/main/docs/datasheets/SSD1619A.pdf)
- [Web Bluetooth API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Bluetooth_API)