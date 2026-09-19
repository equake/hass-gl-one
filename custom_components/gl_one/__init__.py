"""GroupLink water-meter (GL-MIV) integration for Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONFIG_ENTRY_VERSION
from .coordinator import GLOneCoordinator

_LOGGER = logging.getLogger(__name__)

type GLOneConfigEntry = ConfigEntry[GLOneCoordinator]

PLATFORMS = [Platform.SENSOR, Platform.NUMBER]


async def async_setup_entry(hass: HomeAssistant, entry: GLOneConfigEntry) -> bool:
    coordinator = GLOneCoordinator(hass, entry)
    await coordinator.async_setup()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: GLOneConfigEntry) -> bool:
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator: GLOneCoordinator = entry.runtime_data
        await coordinator.async_shutdown()
    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, entry: GLOneConfigEntry) -> bool:
    """Migrate a config entry to the current version."""
    _LOGGER.debug("Migrating GL water entry from version %s", entry.version)
    if entry.version == CONFIG_ENTRY_VERSION:
        return True
    _LOGGER.error("Cannot migrate GL water config entry from version %s", entry.version)
    return False
