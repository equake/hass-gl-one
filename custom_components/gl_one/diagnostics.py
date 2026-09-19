"""Diagnostics support for the GL One integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import GLOneConfigEntry
from .const import CONF_DEVICE_ID

# The device/serial id identifies the physical meter — redact it from shared
# diagnostics. (It is public on the QR sticker, but not something to paste in
# an issue.)
TO_REDACT = {CONF_DEVICE_ID}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: GLOneConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    reading = coordinator.reading
    return {
        "config": async_redact_data(dict(entry.data), TO_REDACT),
        "options": dict(entry.options),
        "state": {
            "kind": coordinator.kind,
            "increment": coordinator.increment,
            "offset": coordinator.offset,
            "available": coordinator.available,
            "rssi": coordinator.rssi,
            "last_seen": coordinator.last_seen.isoformat()
            if coordinator.last_seen
            else None,
            "consumption": coordinator.consumption,
            "index": coordinator.index,
        },
        "reading": {
            "register": reading.register,
            "uptime_s": reading.uptime_s,
            "device_type": reading.device_type,
            "use_case": reading.use_case,
        }
        if reading
        else None,
    }
