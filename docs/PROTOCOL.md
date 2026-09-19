# GL-MIV BLE protocol — reverse-engineering notes

How the GroupLink GL-MIV water-meter sensor broadcasts its reading, and how
this integration decodes it locally. Reconstructed from the official
*Consumo Inteligente* Android app (`com.grouplinknetwork.gl_consumo_inteligente`,
a Flutter app; the BLE logic lives in the bundled native SDK `com.andriod.lib`),
and validated against live captures from a real meter (pairing id `2986005667`).

## Transport

- **BLE advertisement**, manufacturer-specific data, **company id `0xF0DA` (61658)**.
  (`0xF0DE`/61662 is a second beacon type — *InfoAir* notifications — not the reading.)
- Payload is **20 bytes**. Read it with a passive scan; no pairing, no GATT
  connection, no cloud.
- The MAC address rotates (privacy), and the meter often carries no device name,
  so devices are identified by the **device id inside the decoded payload**, not
  by MAC. Phones running the app also advertise under `0xF0DA` — those decode to
  a different use case (`0x4f`) and are ignored.

## Obfuscation (not encryption)

The 20-byte payload is `RC4(key, plaintext[16])[0:16] ++ key[4]`, where the RC4
`key` is a 4-byte CRC of the plaintext — **and that same CRC is appended in the
clear as bytes [16..19]**. So the "key" travels with the message and decoding
needs no secret:

```
plaintext(16) = RC4(adv[16:20], adv[0:16])      # RC4 is symmetric
valid  ⇔  crc32_glc(plaintext) == adv[16:20]
```

- **RC4**: standard, from the SDK's `Arc4Controller`.
- **CRC**: `CrcBleGl` — CRC-32, polynomial `0x04C11DB7`, init `0xFFFFFFFF`,
  processed MSB-first, final bitwise-NOT, emitted big-endian.

(A newer protocol variant adds an AES-ECB layer with 256 byte-indexed keys
embedded in the app and a SHA-256 integrity prefix; it is also fully offline.
The observed GL-MIV uses the RC4+CRC "old" protocol — the CRC check confirms it.)

## Plaintext layout (16 bytes)

| Bytes | Field | Notes |
|------:|-------|-------|
| `[0]` | device type | `0x17` on the observed meter |
| `[1]` | use case | `0x03` = meter beacon (`0x4f` = a phone; ignore) |
| `[2:5]` | device uptime | seconds, big-endian, 3 bytes (increments ~1/s) |
| `[5:9]` | **device id** | big-endian; equals the QR/pairing id |
| `[9]` | reserved | `0` |
| `[10]` | tx power | `0` observed |
| `[11:13]` | **consumption register** | little-endian 16-bit (`[12]` low, `[13]` high) |
| `[13:16]` | per-device config | constant per device |

## The consumption register

- `register = plaintext[12] + (plaintext[13] << 8)` — a **cumulative counter,
  monotonic non-decreasing**, counting consumption **since the sensor was
  installed** (from 0).
- **1 unit = 10 L = 0.01 m³**, matching the app's 2-decimal m³ resolution.
- The official app shows the meter's absolute index:
  `app_m³ = install_index + register × 0.01`.

### How the register was calibrated

Live captures from two meters in range:

- A neighbour's meter climbed `156 → 200` over ~3.7 h in bursts (water use) —
  proving the register tracks consumption, not time.
- On the target meter, a measured draw (shower with a tankless heater reading
  **55 L** of hot water + a ~6 L flush + shower cold-mix) moved the register
  `259 → 266` = **7 units ≈ 70 L**, i.e. **10 L/unit**. Gallons were ruled out:
  7 gal = 26.5 L is less than the 55 L of hot water alone.
- **Absolute confirmation:** at register `266` the official app read **33.78 m³**
  ⇒ `install_index = 33.78 − 266×0.01 = 31.12 m³`, and `266×0.01 + 31.12 = 33.78`
  exactly. A subsequent flush moved the register to `267` while the app still
  showed `33.78` — the local BLE read is one pulse **ahead** of the cloud.

### Rollover

The register is 16-bit, so it wraps to 0 after `65535` units = **655.36 m³**
(~4.5 years at typical usage). Handled natively by Home Assistant's
`total_increasing` state class (treats the wrap as a meter reset), which loses
at most the 0.01 m³ straddling the boundary — negligible.

## Inside this integration

- `decoder.py` — pure functions: `rc4`, `crc32_glc`, `decode()` → `GLReading`.
- `coordinator.py` — registers a Bluetooth callback
  (`bluetooth.async_register_callback`, matcher `manufacturer_id=0xF0DA`,
  `connectable=false`, passive), decodes each advert, keeps the latest reading
  for the configured device id, and notifies entity listeners (`local_push`).
- `sensor.py` / `number.py` — consumption & index sensors, diagnostics, and the
  adjustable install-index offset.
