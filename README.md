# GL One (GroupLink) — Home Assistant Integration

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=equake&repository=hass-gl-one&category=integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A **fully local** Home Assistant integration for **GL One** (GroupLink) utility
meters — the Bluetooth sensors behind the *"Consumo Inteligente"* app. It reads
your meter straight from its Bluetooth advertisement — **no cloud, no account,
no API key, no phone** — and exposes the reading to Home Assistant.

> **Status:** water meters (GL-MIV) are fully supported and calibrated. Gas and
> energy meters use the same protocol and are scaffolded but **not yet
> implemented/calibrated** — see [Roadmap](#roadmap--todo).

---

## What is GL One?

**GL One** is GroupLink's (GLOne) utility-monitoring network. A small
battery sensor clips onto a mechanical **water, gas or energy** meter and
broadcasts the reading over Bluetooth. The official app normally shows it via
GroupLink's cloud, fed by a **crowd-relay network** — any nearby phone running
the app picks up the broadcast and forwards it to GLOne's servers.

That same broadcast is readable by anyone in range. This integration decodes it
locally, so your data never leaves the house and updates in real time — often
**ahead of the official app**, which depends on the relay + cloud sync.

> The register is transmitted in the BLE advertisement itself, lightly
> obfuscated (RC4 keyed by a CRC that is sent in the clear). No per-device key
> or pairing is required to read it. See [`docs/PROTOCOL.md`](docs/PROTOCOL.md).

---

## Features

| Platform | What you get |
|---|---|
| **Sensor** | Consumption since install (`total_increasing` → works with the Energy/Water dashboard and `utility_meter`) |
| **Sensor** | Meter index — consumption + install index, to cross-check the official app |
| **Sensor** | Diagnostics: raw register, signal strength (RSSI), device uptime, last seen |
| **Number** | Install index (offset), adjustable from the UI and persisted across restarts |

Everything is **push-based** (`local_push`): the integration registers a
callback with Home Assistant's Bluetooth stack and updates the moment a beacon
arrives (the meter broadcasts periodically — often only every several minutes).

### Multiple meters

Each meter is a **separate config entry / device**. Add the integration once per
serial (via auto-discovery or manually) and each one gets its own independent
device and entities — mix water, gas and energy freely. They never interfere:
every entry decodes the shared broadcast and keeps only the beacon whose id
matches its own.

---

## Requirements

- A working **Bluetooth** setup in Home Assistant (a local adapter or an
  [ESPHome Bluetooth Proxy](https://esphome.io/components/bluetooth_proxy.html)
  within range of the meter).
- Your meter's **pairing / QR id** — the number printed on the device / its QR
  sticker (e.g. `2986005667`), also shown as the `deviceId` during setup.

---

## How readings map to the official app (water)

The sensor's register counts consumption **since the sensor was installed**, in
steps of **10 L (0.01 m³)**. The official app shows the meter's absolute index:

```
app (m³) = install_index + register × 0.01
```

`install_index` is the reading the mechanical meter already had when the
technician fitted the sensor (typically 30-something m³). Set it in the
**Install index** number entity to make the *Meter index* sensor match the app.
If you only care about consumption over time (daily/monthly), leave it at 0 and
use the *Consumption* sensor with a `utility_meter` helper.

### Counter rollover

The register is a 16-bit counter, so it wraps to 0 after 655.36 m³ (~4.5 years
at typical usage). This is handled natively by the `total_increasing` state
class — Home Assistant treats the wrap as a meter reset, losing at most the
0.01 m³ straddling the boundary.

---

## Roadmap / TODO

- [ ] **Gas meters** — the protocol is shared, but we have **no gas unit to test
      with**, so the register-to-m³ scale and the device-type byte are
      unverified. The integration exposes a `gas` kind with a configurable step,
      but it is **not validated**.
- [ ] **Energy meters** — same story: exposed as an `energy` kind (kWh) but
      **not implemented/calibrated**, for lack of hardware to test.

If you own a GL One **gas or energy** sensor and can help, a short capture of its
advertisements (see [`helpers/decode_beacon.py`](helpers/decode_beacon.py)) plus
the value shown in the official app is enough to calibrate it — please open an
issue. Water (GL-MIV) is fully calibrated and confirmed.

---

## Installation

### Via HACS (recommended)

1. HACS → ⋮ → *Custom repositories* → add this repo as an **Integration**.
2. Install **GL One (GroupLink)** and restart Home Assistant.

### Manual

Copy `custom_components/gl_one` into your Home Assistant `config/custom_components/`
directory and restart.

---

## Setup

### Auto-discovery

If a meter is in Bluetooth range, Home Assistant discovers it automatically
(*Settings → Devices & Services*). The discovery card shows the decoded pairing
id — pick the one matching **your** meter (neighbours' GL One meters may also be
discovered), choose what it measures, and optionally enter the install index.

### Manual

*Add Integration → GL One*, then enter your pairing/QR id, the measurement type,
and (optionally) the install index. Repeat for each meter you own.

---

## Entities created per device

| Entity | Class | Notes |
|---|---|---|
| Consumption m³ | `total_increasing` | Consumption since install, in m³. Feed to `utility_meter` |
| Consumption liters | `total_increasing` | Same, in litres (water only) — handy for the water dashboard |
| Meter index | `total_increasing` | = consumption + install index; matches the app |
| Raw register | diagnostic | The on-air 16-bit counter (water: 1 = 10 L) |
| Signal strength | diagnostic | Disabled by default |
| Device uptime | diagnostic | Disabled by default |
| Last seen | diagnostic | When the last valid beacon arrived |
| Install index | number (config) | Adjustable offset |

---

## Example: daily and monthly consumption

```yaml
# configuration.yaml
utility_meter:
  agua_diaria:
    source: sensor.gl_one_2986005667_consumption_m3
    cycle: daily
  agua_mensal:
    source: sensor.gl_one_2986005667_consumption_m3
    cycle: monthly
```

You can also add the *Consumption* sensor directly to the **Water** (or Gas /
Energy) section of the Energy dashboard.

---

## Troubleshooting

**The meter isn't discovered / entities are unavailable.** Confirm Home
Assistant's Bluetooth integration is set up and an adapter or Bluetooth proxy is
within range. The meter broadcasts only periodically (often every several minutes); entities
go unavailable after 60 minutes of silence.

**A neighbour's meter showed up.** GL One meters all use the same manufacturer
id, so nearby ones are discovered too. Each is keyed by its own pairing id —
just pick yours (the number on your QR sticker).

**The Meter index doesn't match the app.** Set the **Install index** to the
reading the meter had at install (or read the app once and set it to
`app_value − consumption`). The app can also simply be lagging — it syncs
through the cloud, while this integration is real-time.

---

## How it works — the protocol

The full reverse-engineering write-up is in [`docs/PROTOCOL.md`](docs/PROTOCOL.md):
the 0xF0DA advertisement layout, the RC4+CRC obfuscation, the plaintext fields,
and how the water register was calibrated to 10 L / 0.01 m³ per step.

---

## References

- **GroupLink / GL One** — official site: <https://grouplinkone.com>
  (water sensor product page: <https://grouplinkone.com/pt/gl-utilities-water-mdi>)
- **GL One SDK documentation**: <https://sdk.grouplinkone.com/docs/SDK%20Documentation/Introduction>
- **Official app "Consumo Inteligente"**:
  [Google Play](https://play.google.com/store/apps/details?id=com.grouplinknetwork.gl_consumo_inteligente)
  · [App Store](https://apps.apple.com/br/app/consumo-inteligente/id6450606003)
- Protocol notes: [`docs/PROTOCOL.md`](docs/PROTOCOL.md)

The integration icon lives in `custom_components/gl_one/brand/` and can be replaced.

---

## License

MIT — see [LICENSE](LICENSE). Not affiliated with GroupLink / GLOne. For
interoperability with your own meter and your own data.
