"""Constants for the GL One (GroupLink) integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "gl_one"

# Config entry keys
CONF_DEVICE_ID = "device_id"          # the QR/pairing id printed on the device
CONF_KIND = "kind"                    # what the meter measures
CONF_OFFSET = "offset"                # install index added to the register
CONF_INCREMENT = "increment"          # measured units per register step

# Measurement kinds. GL One is a generic network that carries water, gas and
# energy meters that share this BLE protocol. Only water is fully calibrated so
# far; gas/energy expose the same register with a configurable step.
KIND_WATER = "water"
KIND_GAS = "gas"
KIND_ENERGY = "energy"
KINDS = [KIND_WATER, KIND_GAS, KIND_ENERGY]
DEFAULT_KIND = KIND_WATER

# Units per register step. Water is verified (1 step = 10 L = 0.01 m³ = the
# app's 2-decimal resolution). Gas/energy default to the same 0.01 until we
# have samples to calibrate them; the user can override per entry.
DEFAULT_INCREMENT: dict[str, float] = {
    KIND_WATER: 0.01,
    KIND_GAS: 0.01,
    KIND_ENERGY: 0.01,
}
DEFAULT_OFFSET = 0.0

# The device advertises roughly once per second while in range. If nothing has
# been heard for this long the entities go unavailable.
STALE_AFTER = timedelta(minutes=15)
STALE_CHECK_INTERVAL = timedelta(minutes=1)

CONFIG_ENTRY_VERSION = 1
