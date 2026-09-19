#!/usr/bin/env python3
"""Standalone helper: decode a GL-MIV beacon, or scan live.

Decode a captured 0xF0DA manufacturer-data payload (20 bytes, hex)::

    python helpers/decode_beacon.py d7d53053ac8a481876d4299b259471cbd0671ec0

Scan live (needs `pip install bleak`, and a local Bluetooth adapter)::

    python helpers/decode_beacon.py --scan [seconds]

Prints device id, raw register, and consumption (register x 0.01 m3).
"""

import asyncio
import os
import sys

# Import the pure decoder module directly, without loading the integration
# package (which imports Home Assistant).
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "custom_components", "gl_one"))
from decoder import MANUFACTURER_ID, decode


def _print(reading, extra: str = "") -> None:
    print(
        f"device_id={reading.device_id}  register={reading.register}  "
        f"consumo={reading.consumption_m3:.2f} m3  uptime={reading.uptime_s}s"
        f"{('  ' + extra) if extra else ''}"
    )


def decode_hex(hex_str: str) -> None:
    reading = decode(bytes.fromhex(hex_str))
    if reading is None:
        print("Not a valid GL-MIV meter beacon (CRC/use-case check failed).")
        sys.exit(1)
    _print(reading)


async def scan(seconds: int) -> None:
    from bleak import BleakScanner

    seen: set[tuple[int, int]] = set()

    def cb(_device, adv) -> None:
        raw = adv.manufacturer_data.get(MANUFACTURER_ID)
        if not raw:
            return
        reading = decode(bytes(raw))
        if reading is None:
            return
        key = (reading.device_id, reading.register)
        if key in seen:
            return
        seen.add(key)
        _print(reading, extra=f"rssi={adv.rssi}")

    print(f"Scanning {seconds}s for GL-MIV meters (0xF0DA)...")
    scanner = BleakScanner(detection_callback=cb, scanning_mode="active")
    async with scanner:
        await asyncio.sleep(seconds)


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    if args[0] == "--scan":
        asyncio.run(scan(int(args[1]) if len(args) > 1 else 60))
    else:
        decode_hex(args[0])


if __name__ == "__main__":
    main()
