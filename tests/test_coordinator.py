"""Coordinator tests: decode an injected advertisement and compute values."""

from unittest.mock import patch

import pytest
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


@pytest.fixture
async def coordinator(hass: HomeAssistant):
    """Set up a coordinator with a captured Bluetooth callback; always shut down."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=str(DEVICE_ID),
        data={CONF_DEVICE_ID: DEVICE_ID, CONF_KIND: KIND_WATER, CONF_OFFSET: 31.12},
    )
    entry.add_to_hass(hass)
    coord = GLOneCoordinator(hass, entry)
    captured: dict = {}

    def fake_register(hass_, cb, matcher, mode):
        captured["cb"] = cb
        return lambda: None

    with patch(
        "custom_components.gl_one.coordinator.bluetooth.async_register_callback",
        side_effect=fake_register,
    ):
        await coord.async_setup()

    yield coord, captured

    await coord.async_shutdown()


async def test_decodes_and_computes(coordinator) -> None:
    coord, captured = coordinator

    assert coord.available is False
    assert coord.consumption is None
    assert coord.index is None

    captured["cb"](make_service_info(METER), BluetoothChange.ADVERTISEMENT)

    assert coord.available is True
    assert coord.reading is not None
    assert coord.reading.device_id == DEVICE_ID
    assert coord.consumption == 2.59
    assert coord.consumption_liters == 2590.0  # 259 units x 10 L
    assert coord.index == 33.71  # 2.59 + 31.12 install offset
    assert coord.rssi == -60


async def test_ignores_other_device(coordinator) -> None:
    coord, captured = coordinator
    coord.device_id = 999999999  # a valid meter beacon, but not ours
    captured["cb"](make_service_info(METER), BluetoothChange.ADVERTISEMENT)
    assert coord.reading is None
    assert coord.available is False


async def test_offset_updates_index(coordinator) -> None:
    coord, captured = coordinator
    captured["cb"](make_service_info(METER), BluetoothChange.ADVERTISEMENT)
    coord.set_offset(0.0)
    assert coord.index == 2.59  # consumption only, no offset
