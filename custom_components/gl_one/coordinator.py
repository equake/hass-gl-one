"""Coordinator for the GL One (GroupLink) integration.

Each config entry is one physical meter (water, gas or energy) identified by
its pairing/serial id. The meter is read passively: it broadcasts a cumulative
register in a BLE advertisement (manufacturer id 0xF0DA). We register a callback
with Home Assistant's Bluetooth integration, decode each matching advertisement,
and keep the latest reading for this entry's device id. No connection, no cloud,
no key.

Multiple meters = multiple config entries, each with its own coordinator and its
own Bluetooth callback filtering on its device id, so they are fully independent.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import (
    BluetoothChange,
    BluetoothScanningMode,
    BluetoothServiceInfoBleak,
)
from homeassistant.components.bluetooth.match import BluetoothCallbackMatcher
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    CONF_DEVICE_ID,
    CONF_INCREMENT,
    CONF_KIND,
    CONF_OFFSET,
    DEFAULT_INCREMENT,
    DEFAULT_KIND,
    DEFAULT_OFFSET,
    DOMAIN,
    STALE_AFTER,
    STALE_CHECK_INTERVAL,
)
from .decoder import MANUFACTURER_ID, GLReading, decode
from .kinds import model as kind_model

_LOGGER = logging.getLogger(__name__)


class GLOneCoordinator:
    """Holds the latest decoded reading for one GL One meter."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.device_id: int = int(entry.data[CONF_DEVICE_ID])
        self.kind: str = entry.data.get(CONF_KIND, DEFAULT_KIND)
        # Offset is owned by the Number entity (persisted via RestoreNumber);
        # this is the working value the index sensor reads. Seeded from config.
        self.offset: float = float(entry.data.get(CONF_OFFSET, DEFAULT_OFFSET))
        self.increment: float = float(
            entry.options.get(
                CONF_INCREMENT,
                entry.data.get(CONF_INCREMENT, DEFAULT_INCREMENT.get(self.kind, 0.01)),
            )
        )

        self.reading: GLReading | None = None
        self.rssi: int | None = None
        self.last_seen: datetime | None = None
        self._last_seen_mono: float | None = None

        self._listeners: list[Callable[[], None]] = []
        self._unsub_bluetooth: Callable[[], None] | None = None
        self._unsub_stale: Callable[[], None] | None = None

    # ------------------------------------------------------------------ setup
    async def async_setup(self) -> None:
        self._unsub_bluetooth = bluetooth.async_register_callback(
            self.hass,
            self._async_on_advertisement,
            BluetoothCallbackMatcher(
                manufacturer_id=MANUFACTURER_ID, connectable=False
            ),
            BluetoothScanningMode.PASSIVE,
        )
        self._unsub_stale = async_track_time_interval(
            self.hass, self._async_check_stale, STALE_CHECK_INTERVAL
        )

    async def async_shutdown(self) -> None:
        if self._unsub_bluetooth:
            self._unsub_bluetooth()
            self._unsub_bluetooth = None
        if self._unsub_stale:
            self._unsub_stale()
            self._unsub_stale = None

    # ------------------------------------------------------- advertisement in
    @callback
    def _async_on_advertisement(
        self,
        service_info: BluetoothServiceInfoBleak,
        change: BluetoothChange,
    ) -> None:
        raw = service_info.manufacturer_data.get(MANUFACTURER_ID)
        if not raw:
            return
        reading = decode(bytes(raw))
        if reading is None or reading.device_id != self.device_id:
            return  # different beacon type, or another GL meter
        self.reading = reading
        self.rssi = service_info.rssi
        self.last_seen = datetime.now(UTC)
        self._last_seen_mono = time.monotonic()
        self._notify_listeners()

    @callback
    def _async_check_stale(self, _now: object = None) -> None:
        # Refresh entity state so `available` flips when data stops arriving.
        self._notify_listeners()

    # -------------------------------------------------------------- accessors
    @property
    def available(self) -> bool:
        if self._last_seen_mono is None:
            return False
        return (time.monotonic() - self._last_seen_mono) < STALE_AFTER.total_seconds()

    @property
    def consumption(self) -> float | None:
        """Consumption since install, in the kind's unit (m³ or kWh)."""
        if self.reading is None:
            return None
        return round(self.reading.register * self.increment, 2)

    @property
    def index(self) -> float | None:
        """Absolute meter index (consumption + install offset), matches the app."""
        consumo = self.consumption
        if consumo is None:
            return None
        return round(consumo + self.offset, 2)

    def set_offset(self, value: float) -> None:
        self.offset = value
        self._notify_listeners()

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, str(self.device_id))},
            name=f"GL One {self.device_id}",
            manufacturer="GroupLink",
            model=kind_model(self.kind),
            serial_number=str(self.device_id),
        )

    # -------------------------------------------------------------- listeners
    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(listener)

        def _remove() -> None:
            try:
                self._listeners.remove(listener)
            except ValueError:
                pass

        return _remove

    def _notify_listeners(self) -> None:
        for cb in self._listeners:
            try:
                cb()
            except Exception:
                _LOGGER.exception("Error in GL One listener callback")
