"""Decoder for the GroupLink GL-MIV water-meter BLE advertisement.

Reverse-engineered from the official "Consumo Inteligente" app (see
``docs/PROTOCOL.md``). Pure functions, no Home Assistant dependency, so the
decode can be unit-tested in isolation.

The meter broadcasts manufacturer-specific data under company id 0xF0DA
(61658), 20 bytes. The "encryption" is obfuscation only: RC4 keyed by a CRC-32
of the plaintext, and that same CRC is appended in clear as the last 4 bytes,
so it decodes with no key and no cloud::

    plaintext[16] = RC4(key = adv[16:20], data = adv[0:16])   # RC4 is symmetric
    valid  <=>  crc32_glc(plaintext) == adv[16:20]

Plaintext layout (16 bytes)::

    [0]      device type
    [1]      use case (0x03 for the meter beacon)
    [2:5]    device uptime, seconds (big-endian, 3 bytes)
    [5:9]    device id  (big-endian, == the QR/pairing id)
    [9]      reserved
    [10]     tx power
    [11:13]  cumulative consumption register, little-endian 16-bit
             (byte[12] = low, byte[13] = high); 1 unit = 10 L = 0.01 m3
    [13:16]  per-device config bytes

The register counts consumption *since the sensor was installed* (from 0). The
official app shows ``install_index + register * 0.01`` m3.
"""

from __future__ import annotations

from dataclasses import dataclass

MANUFACTURER_ID = 0xF0DA  # 61658
_ADV_LEN = 20
_USE_CASE_METER = 0x03

# CRC-32 as used by the SDK's CrcBleGl: poly 0x04C11DB7, init 0xFFFFFFFF,
# process MSB-first, final bitwise-NOT, emitted big-endian.
_POLY = 0x04C11DB7


def _crc_table() -> list[int]:
    table: list[int] = []
    for i in range(256):
        value = i << 24
        for _ in range(8):
            value = ((value << 1) ^ _POLY) if (value & 0x80000000) else (value << 1)
            value &= 0xFFFFFFFF
        table.append(value)
    return table


_TABLE = _crc_table()


def crc32_glc(data: bytes) -> bytes:
    """Return the 4-byte (big-endian) GroupLink CRC of ``data``."""
    crc = 0xFFFFFFFF
    for byte in data:
        crc = ((crc << 8) & 0xFFFFFFFF) ^ _TABLE[((crc >> 24) ^ byte) & 0xFF]
    return ((~crc) & 0xFFFFFFFF).to_bytes(4, "big")


def rc4(key: bytes, data: bytes) -> bytes:
    """Standard RC4 (symmetric: encrypt == decrypt)."""
    s = list(range(256))
    j = 0
    for i in range(256):
        j = (j + s[i] + key[i % len(key)]) & 0xFF
        s[i], s[j] = s[j], s[i]
    out = bytearray()
    i = j = 0
    for byte in data:
        i = (i + 1) & 0xFF
        j = (j + s[i]) & 0xFF
        s[i], s[j] = s[j], s[i]
        out.append(byte ^ s[(s[i] + s[j]) & 0xFF])
    return bytes(out)


@dataclass(frozen=True)
class GLReading:
    """One decoded meter advertisement."""

    device_id: int
    register: int          # raw cumulative counter (1 unit = 10 L)
    uptime_s: int
    device_type: int
    use_case: int

    @property
    def consumption_m3(self) -> float:
        """Consumption since sensor install, in m3 (1 unit = 0.01 m3)."""
        return round(self.register * 0.01, 2)


def decode(manufacturer_data: bytes) -> GLReading | None:
    """Decode a 0xF0DA advertisement payload; return None if invalid/not a meter.

    ``manufacturer_data`` is the value bytes for company id 0xF0DA (the 20-byte
    payload, without the 2-byte company id prefix).
    """
    if len(manufacturer_data) != _ADV_LEN:
        return None
    key = manufacturer_data[16:20]
    plaintext = rc4(key, manufacturer_data[0:16])
    if crc32_glc(plaintext) != key:
        return None  # not the OLD protocol / corrupt / different beacon type
    use_case = plaintext[1]
    if use_case != _USE_CASE_METER:
        return None  # e.g. a phone advertising (use case 0x4f) — ignore
    return GLReading(
        device_id=int.from_bytes(plaintext[5:9], "big"),
        register=plaintext[12] + (plaintext[13] << 8),
        uptime_s=int.from_bytes(plaintext[2:5], "big"),
        device_type=plaintext[0],
        use_case=use_case,
    )
