"""The hubc2000pp service integration (Bolid C2000PP modbus converter poll/configure service)."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, KEY_SETUP_LOCK, KEY_UNSUB_STOP, LISTENER_KEY
from .hubc2000pp import HUBC2000PPUdpReceiver, get_devices, update_device

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.ALARM_CONTROL_PANEL,
    Platform.SWITCH,
]


async def update_listener(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Update config entry listener."""
    await hass.config_entries.async_reload(config_entry.entry_id)


class HUBC2000PPDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Data update coordinator for HUB-C2000PP service."""

    def __init__(self, hass: HomeAssistant, host: str, port: int) -> None:
        """Initialize coordinator data."""
        self._hass = hass
        self._host = host
        self._port = port
        self._devices: dict[str, Any] | None = None

        update_interval = timedelta(minutes=1)
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=update_interval)

    @property
    def host(self) -> str:
        """Host getter."""
        return self._host

    @property
    def port(self) -> int:
        """Port getter."""
        return self._port

    async def _async_update_data(self):
        """Request data from hub."""
        result = await get_devices(self._host, self._port)
        if not result["error"]:
            self._devices = result
        else:
            _LOGGER.warning("HUB-C2000PP update error: %s", result["error"])
            raise UpdateFailed()
        return self._devices

    def udp_callback(self, message):
        """Handle push from hub."""
        update_device(message, self._devices)
        self.async_update_listeners()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up hubc2000pp from a config entry."""

    hass.data.setdefault(DOMAIN, {})
    setup_lock = hass.data[DOMAIN].setdefault(KEY_SETUP_LOCK, asyncio.Lock())

    host = entry.data["host"]
    port = entry.data["port"]

    if LISTENER_KEY not in hass.data[DOMAIN]:
        async with setup_lock:
            listener = HUBC2000PPUdpReceiver(port + 1)
            hass.data[DOMAIN][LISTENER_KEY] = listener
            await listener.start_listen()

            @callback
            def stop_udp(event):
                """Stop hub listener."""
                _LOGGER.debug("Shutting down HUB listener")
                listener.stop_listen()

            unsub = hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stop_udp)
            hass.data[DOMAIN][KEY_UNSUB_STOP] = unsub

    listener = hass.data[DOMAIN][LISTENER_KEY]
    coordinator = HUBC2000PPDataUpdateCoordinator(hass, host, port)
    await coordinator.async_config_entry_first_refresh()

    listener.register_hub(host, coordinator.udp_callback)
    _LOGGER.info("HUB '%s:%d' connected, listening for pushes", host, port)

    entry.async_on_unload(entry.add_update_listener(update_listener))

    hass.data[DOMAIN][entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
