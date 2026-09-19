"""Number platform: the meter's install index (offset), adjustable in the UI.

The BLE register counts consumption since the sensor was installed (from 0).
The official app shows ``install_index + register * increment``. This Number
lets you enter that install index so the "Meter index" sensor matches the app.
It is persisted across restarts (RestoreNumber) and never depends on the meter
being in range, so it is always settable.
"""

from __future__ import annotations

from homeassistant.components.number import NumberMode, RestoreNumber
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import GLOneConfigEntry, kinds
from .coordinator import GLOneCoordinator
from .entity import GLOneEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GLOneConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([GLOneOffsetNumber(entry.runtime_data)])


class GLOneOffsetNumber(GLOneEntity, RestoreNumber):
    """Adjustable install-index offset (in the meter's unit)."""

    _attr_translation_key = "offset"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 0.0
    _attr_native_max_value = 1_000_000.0
    _attr_native_step = 0.01
    _attr_mode = NumberMode.BOX
    _attr_icon = "mdi:tune"

    def __init__(self, coordinator: GLOneCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device_id}_offset"
        self._attr_native_unit_of_measurement = kinds.unit(coordinator.kind)
        self._attr_native_value = coordinator.offset

    @property
    def available(self) -> bool:
        # A config value: always settable, independent of BLE reception.
        return True

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_number_data()
        if last is not None and last.native_value is not None:
            self._attr_native_value = last.native_value
            self._coordinator.set_offset(last.native_value)

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = value
        self._coordinator.set_offset(value)
        self.async_write_ha_state()
