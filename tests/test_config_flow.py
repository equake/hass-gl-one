"""Config-flow tests for the GL One integration.

The flow steps are exercised directly (rather than through the flow manager) so
the tests don't need the full Bluetooth stack set up — they validate our own
flow logic: id validation, unique-id handling, discovery decode and the data we
persist.
"""

import pytest
from _ble import make_service_info
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import AbortFlow, FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry
from test_decoder import METER, PHONE

from custom_components.gl_one.config_flow import GLOneConfigFlow
from custom_components.gl_one.const import (
    CONF_DEVICE_ID,
    CONF_KIND,
    CONF_OFFSET,
    DOMAIN,
    KIND_WATER,
)

DEVICE_ID = 2986005667


def _flow(hass: HomeAssistant, source: str = SOURCE_USER) -> GLOneConfigFlow:
    flow = GLOneConfigFlow()
    flow.hass = hass
    flow.handler = DOMAIN
    flow.context = {"source": source}
    return flow


async def test_user_flow_creates_entry(hass: HomeAssistant) -> None:
    flow = _flow(hass)
    form = await flow.async_step_user()
    assert form["type"] is FlowResultType.FORM

    result = await flow.async_step_user(
        {CONF_DEVICE_ID: DEVICE_ID, CONF_KIND: KIND_WATER, CONF_OFFSET: 31.12}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_DEVICE_ID: DEVICE_ID,
        CONF_KIND: KIND_WATER,
        CONF_OFFSET: 31.12,
    }
    assert flow.unique_id == str(DEVICE_ID)


async def test_user_flow_invalid_id(hass: HomeAssistant) -> None:
    flow = _flow(hass)
    result = await flow.async_step_user(
        {CONF_DEVICE_ID: 0, CONF_KIND: KIND_WATER, CONF_OFFSET: 0}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_device_id"}


async def test_user_flow_duplicate(hass: HomeAssistant) -> None:
    MockConfigEntry(domain=DOMAIN, unique_id=str(DEVICE_ID)).add_to_hass(hass)
    flow = _flow(hass)
    with pytest.raises(AbortFlow) as err:
        await flow.async_step_user(
            {CONF_DEVICE_ID: DEVICE_ID, CONF_KIND: KIND_WATER, CONF_OFFSET: 0}
        )
    assert err.value.reason == "already_configured"


async def test_bluetooth_discovery(hass: HomeAssistant) -> None:
    flow = _flow(hass)
    form = await flow.async_step_bluetooth(make_service_info(METER))
    assert form["type"] is FlowResultType.FORM
    assert form["step_id"] == "bluetooth_confirm"
    assert flow.unique_id == str(DEVICE_ID)

    result = await flow.async_step_bluetooth_confirm(
        {CONF_KIND: KIND_WATER, CONF_OFFSET: 31.12}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_DEVICE_ID] == DEVICE_ID


async def test_bluetooth_not_meter(hass: HomeAssistant) -> None:
    flow = _flow(hass)
    result = await flow.async_step_bluetooth(make_service_info(PHONE))
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "not_supported"
