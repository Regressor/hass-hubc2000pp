"""Support for HUB-C2000PP binary sensor."""
import logging
from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import HUBC2000PPDataUpdateCoordinator
from .const import DOMAIN
from .hubc2000pp import RelayFailed, switch_relay

_LOGGER = logging.getLogger(__name__)

SWITCH_SENSORS = {
    "relaySensor",
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Bolid sensor."""
    coordinator: HUBC2000PPDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    devices = coordinator.data["relays"]
    entities = []
    for device in devices:
        entities.append(SwitchDevice(device, coordinator))

    async_add_entities(entities)


class SwitchDevice(CoordinatorEntity[HUBC2000PPDataUpdateCoordinator], SwitchEntity):
    """Representation of an Bolid sensor from HUB-C2000PP data."""

    def __init__(
        self,
        device: dict[str, Any],
        coordinator: HUBC2000PPDataUpdateCoordinator,
    ) -> None:
        """Initialize the Bolid sensor."""
        super().__init__(coordinator)

        device_uid = f'relay_{device["id"]}'
        device_name = "Реле"
        device_class = SwitchDeviceClass.SWITCH

        self._attr_device_info = DeviceInfo(
            identifiers={
                (DOMAIN, device_uid),
            },
            manufacturer="Bolid",
            model="Relay",
            name=device_name,
        )

        self.relay_id = int(device["id"])
        self._attr_name = device["desc"]
        self._attr_unique_id = device_uid
        self._type = "Relay"
        self._attr_device_class = device_class

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        device: dict[str, Any] | None = next(
            (
                device
                for device in self.coordinator.data["relays"]
                if f'relay_{device["id"]}' == self.unique_id
            ),
            None,
        )

        if device:
            state = device["stat"]
            is_on = state == "true"

            # Call update entry only if data was changed
            if self._attr_is_on != is_on:
                self._attr_is_on = is_on
                super()._handle_coordinator_update()

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        coordinator = self.coordinator
        result = await switch_relay(
            self.relay_id,
            True,
            coordinator.host,
            coordinator.port,
        )
        if not result:
            _LOGGER.error("Can't DISARM partition: %d, self.partition_id")
            raise RelayFailed()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        coordinator = self.coordinator
        result = await switch_relay(
            self.relay_id,
            False,
            coordinator.host,
            coordinator.port,
        )
        if not result:
            _LOGGER.error("Can't DISARM partition: %d, self.partition_id")
            raise RelayFailed()
