"""Unit tests for the pure GL-MIV beacon decoder (no Home Assistant needed).

Run with:  pytest tests/
Vectors are real captures from a GL-MIV meter (pairing id 2986005667) and from
a phone advertising under the same company id.
"""

import os
import sys

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "custom_components", "gl_one")
)
from decoder import crc32_glc, decode, rc4

# A real meter beacon: device 2986005667, register 259 (2.59 m3), use case 0x03.
METER = bytes.fromhex("e37fddab50a9f9af70b55e7d73a88979d6f7c546")
# A phone advertising under the same company id (use case 0x4f) — must be ignored.
PHONE = bytes.fromhex("c1499986e83978a4fe0901c8b210ae6ba04e7f57")


def test_decode_meter():
    reading = decode(METER)
    assert reading is not None
    assert reading.device_id == 2986005667
    assert reading.register == 259
    assert reading.use_case == 0x03
    assert reading.consumption_m3 == 2.59


def test_phone_beacon_ignored():
    # Decodes/validates (CRC ok) but is not the meter use case -> None.
    assert decode(PHONE) is None


def test_bad_length():
    assert decode(b"\x00" * 10) is None


def test_crc_rejects_corruption():
    corrupt = bytearray(METER)
    corrupt[0] ^= 0xFF  # flip a ciphertext byte; CRC must no longer match
    assert decode(bytes(corrupt)) is None


def test_rc4_symmetric():
    key = b"\x01\x02\x03\x04"
    data = bytes(range(16))
    assert rc4(key, rc4(key, data)) == data


def test_crc_matches_embedded_key():
    # The last 4 bytes of the advertisement are the CRC of the plaintext.
    plaintext = rc4(METER[16:20], METER[0:16])
    assert crc32_glc(plaintext) == METER[16:20]
