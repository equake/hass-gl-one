"""Coordinator tests: decode an injected advertisement and compute values."""

from unittest.mock import patch

from _ble import make_service_info
from homeassistant.components.bluetooth import BluetoothChange
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from test_decoder import METER

from custom_components.gl_one.const import (
    CONF_DEVICE_ID,
    CONF_KIND,
    CONF_OFFSET,
    DOMAIN,
    KIND_WATER,
)
from custom_components.gl_one.coordinator import GLOneCoordinator

DEVICE_ID = 2986005667


def _entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id=str(DEVICE_ID),
        data={CONF_DEVICE_ID: DEVICE_ID, CONF_KIND: KIND_WATER, CONF_OFFSET: 31.12},
    )


async def _setup_coordinator(hass: HomeAssistant) -> tuple[GLOneCoordinator, dict]:
    entry = _entry()
    entry.add_to_hass(hass)
    coordinator = GLOneCoordinator(hass, entry)
    captured: dict = {}

    def fake_register(hass_, cb, matcher, mode):
        captured["cb"] = cb
        return lambda: None

    with patch(
        "custom_components.gl_one.coordinator.bluetooth.async_register_callback",
        side_effect=fake_register,
    ):
        await coordinator.async_setup()
    return coordinator, captured


async def test_decodes_and_computes(hass: HomeAssistant) -> None:
    coordinator, captured = await _setup_coordinator(hass)

    assert coordinator.available is False
    assert coordinator.consumption is None
    assert coordinator.index is None

    captured["cb"](make_service_info(METER), BluetoothChange.ADVERTISEMENT)

    assert coordinator.available is True
    assert coordinator.reading is not None
    assert coordinator.reading.device_id == DEVICE_ID
    assert coordinator.consumption == 2.59
    assert coordinator.index == 33.71  # 2.59 + 31.12 install offset
    assert coordinator.rssi == -60

    await coordinator.async_shutdown()


async def test_ignores_other_device(hass: HomeAssistant) -> None:
    coordinator, captured = await _setup_coordinator(hass)

    # A valid meter beacon but a different device id must be ignored. Rebuild a
    # METER payload but point the coordinator at a different id.
    coordinator.device_id = 999999999
    captured["cb"](make_service_info(METER), BluetoothChange.ADVERTISEMENT)

    assert coordinator.reading is None
    assert coordinator.available is False

    await coordinator.async_shutdown()


async def test_offset_updates_index(hass: HomeAssistant) -> None:
    coordinator, captured = await _setup_coordinator(hass)
    captured["cb"](make_service_info(METER), BluetoothChange.ADVERTISEMENT)

    coordinator.set_offset(0.0)
    assert coordinator.index == 2.59  # consumption only, no offset

    await coordinator.async_shutdown()
