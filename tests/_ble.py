"""Helper to build a synthetic BluetoothServiceInfoBleak for tests."""

from __future__ import annotations

import time

from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak

from custom_components.gl_one.decoder import MANUFACTURER_ID

ADDRESS = "AA:BB:CC:DD:EE:FF"


def make_service_info(raw: bytes, address: str = ADDRESS, rssi: int = -60):
    """Wrap a 0xF0DA manufacturer-data payload in a BluetoothServiceInfoBleak."""
    manufacturer_data = {MANUFACTURER_ID: raw}
    device = BLEDevice(address, None, {})
    advertisement = AdvertisementData(
        local_name=None,
        manufacturer_data=manufacturer_data,
        service_data={},
        service_uuids=[],
        tx_power=-127,
        rssi=rssi,
        platform_data=(),
    )
    return BluetoothServiceInfoBleak(
        name=address,
        address=address,
        rssi=rssi,
        manufacturer_data=manufacturer_data,
        service_data={},
        service_uuids=[],
        source="local",
        device=device,
        advertisement=advertisement,
        connectable=False,
        time=time.monotonic(),
        tx_power=-127,
    )
