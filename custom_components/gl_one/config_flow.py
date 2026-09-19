"""Config flow for the GL One (GroupLink) integration.

One config entry per physical meter (identified by its pairing/serial id), so
several meters — water, gas, energy — can be added independently.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_DEVICE_ID,
    CONF_KIND,
    CONF_OFFSET,
    DEFAULT_KIND,
    DEFAULT_OFFSET,
    DOMAIN,
    KINDS,
)
from .decoder import MANUFACTURER_ID, decode

_KIND_SELECTOR = SelectSelector(
    SelectSelectorConfig(
        options=KINDS, translation_key="kind", mode=SelectSelectorMode.DROPDOWN
    )
)


class GLOneConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for GL One meters."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovered_id: int | None = None

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle a meter discovered over Bluetooth."""
        raw = discovery_info.manufacturer_data.get(MANUFACTURER_ID)
        reading = decode(bytes(raw)) if raw else None
        if reading is None:
            return self.async_abort(reason="not_supported")

        await self.async_set_unique_id(str(reading.device_id))
        self._abort_if_unique_id_configured()
        self._discovered_id = reading.device_id
        self.context["title_placeholders"] = {"device_id": str(reading.device_id)}
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm a Bluetooth-discovered meter and set its kind / install index."""
        assert self._discovered_id is not None
        if user_input is not None:
            return self.async_create_entry(
                title=f"GL One {self._discovered_id}",
                data={
                    CONF_DEVICE_ID: self._discovered_id,
                    CONF_KIND: user_input[CONF_KIND],
                    CONF_OFFSET: user_input[CONF_OFFSET],
                },
            )
        return self.async_show_form(
            step_id="bluetooth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_KIND, default=DEFAULT_KIND): _KIND_SELECTOR,
                    vol.Optional(CONF_OFFSET, default=DEFAULT_OFFSET): vol.Coerce(float),
                }
            ),
            description_placeholders={"device_id": str(self._discovered_id)},
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manual setup: enter the pairing/QR id printed on the meter."""
        errors: dict[str, str] = {}
        if user_input is not None:
            device_id = int(user_input[CONF_DEVICE_ID])
            if device_id <= 0:
                errors["base"] = "invalid_device_id"
            else:
                await self.async_set_unique_id(str(device_id))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"GL One {device_id}",
                    data={
                        CONF_DEVICE_ID: device_id,
                        CONF_KIND: user_input[CONF_KIND],
                        CONF_OFFSET: user_input.get(CONF_OFFSET, DEFAULT_OFFSET),
                    },
                )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE_ID): vol.Coerce(int),
                    vol.Required(CONF_KIND, default=DEFAULT_KIND): _KIND_SELECTOR,
                    vol.Optional(CONF_OFFSET, default=DEFAULT_OFFSET): vol.Coerce(float),
                }
            ),
            errors=errors,
        )
