"""Sensor platform for the GL One integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import GLOneConfigEntry, kinds
from .coordinator import GLOneCoordinator
from .entity import GLOneEntity


@dataclass(frozen=True, kw_only=True)
class GLOneSensorDescription(SensorEntityDescription):
    """Describes a GL One sensor and how to read its value."""

    value_fn: Callable[[GLOneCoordinator], float | int | datetime | None]


# Diagnostics are the same regardless of kind. The two volume/energy sensors
# (consumption, index) are built per entry from the meter's kind.
DIAGNOSTIC_SENSORS: tuple[GLOneSensorDescription, ...] = (
    GLOneSensorDescription(
        key="register",
        translation_key="register",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:numeric",
        value_fn=lambda c: c.reading.register if c.reading else None,
    ),
    GLOneSensorDescription(
        key="rssi",
        translation_key="rssi",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda c: c.rssi,
    ),
    GLOneSensorDescription(
        key="uptime",
        translation_key="uptime",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda c: c.reading.uptime_s if c.reading else None,
    ),
    GLOneSensorDescription(
        key="last_seen",
        translation_key="last_seen",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: c.last_seen,
    ),
)


def _consumption_sensors(kind: str) -> tuple[GLOneSensorDescription, ...]:
    device_class = kinds.device_class(kind)
    unit = kinds.unit(kind)
    return (
        GLOneSensorDescription(
            key="consumption",
            translation_key="consumption",
            device_class=device_class,
            state_class=SensorStateClass.TOTAL_INCREASING,
            native_unit_of_measurement=unit,
            icon=kinds.icon(kind),
            value_fn=lambda c: c.consumption,
        ),
        GLOneSensorDescription(
            key="index",
            translation_key="index",
            device_class=device_class,
            state_class=SensorStateClass.TOTAL_INCREASING,
            native_unit_of_measurement=unit,
            icon="mdi:counter",
            value_fn=lambda c: c.index,
        ),
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GLOneConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    descriptions = _consumption_sensors(coordinator.kind) + DIAGNOSTIC_SENSORS
    async_add_entities(GLOneSensor(coordinator, desc) for desc in descriptions)


class GLOneSensor(GLOneEntity, SensorEntity):
    """A single GL One sensor."""

    entity_description: GLOneSensorDescription

    def __init__(
        self, coordinator: GLOneCoordinator, description: GLOneSensorDescription
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.device_id}_{description.key}"

    @property
    def available(self) -> bool:
        # last_seen stays available so the "when" is readable after the device
        # goes quiet; everything else follows freshness.
        if self.entity_description.key == "last_seen":
            return self._coordinator.last_seen is not None
        return super().available

    @property
    def native_value(self) -> float | int | datetime | None:
        return self.entity_description.value_fn(self._coordinator)
