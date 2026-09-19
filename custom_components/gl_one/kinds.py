"""Per-measurement-kind presentation (device class, unit, icon, model name)."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import UnitOfEnergy, UnitOfVolume

from .const import KIND_ENERGY, KIND_GAS, KIND_WATER

# kind -> (sensor device class, unit, icon, device model label)
_META: dict[str, tuple[SensorDeviceClass, str, str, str]] = {
    KIND_WATER: (SensorDeviceClass.WATER, UnitOfVolume.CUBIC_METERS, "mdi:water", "GL-MIV"),
    KIND_GAS: (SensorDeviceClass.GAS, UnitOfVolume.CUBIC_METERS, "mdi:fire", "GL One (gás)"),
    KIND_ENERGY: (
        SensorDeviceClass.ENERGY,
        UnitOfEnergy.KILO_WATT_HOUR,
        "mdi:flash",
        "GL One (energia)",
    ),
}


def device_class(kind: str) -> SensorDeviceClass:
    return _META.get(kind, _META[KIND_WATER])[0]


def unit(kind: str) -> str:
    return _META.get(kind, _META[KIND_WATER])[1]


def icon(kind: str) -> str:
    return _META.get(kind, _META[KIND_WATER])[2]


def model(kind: str) -> str:
    return _META.get(kind, _META[KIND_WATER])[3]
