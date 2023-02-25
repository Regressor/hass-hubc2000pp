"""Support for HUB-C2000PP binary sensor."""
import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import HUBC2000PPDataUpdateCoordinator
from .const import DOMAIN, DOOR_EVENTS, FIRE_EVENTS, MOTION_EVENTS

_LOGGER = logging.getLogger(__name__)

BINARY_SENSORS = {
    "doorSensor",
    "motionSensor",
    "smokeSensor",
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Bolid sensor."""
    coordinator: HUBC2000PPDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    devices = coordinator.data["zones"]
    entities = []
    for device in devices:
        if device["type"] in BINARY_SENSORS:
            entities.append(BinaryDevice(device, coordinator))

    async_add_entities(entities)


class BinaryDevice(
    CoordinatorEntity[HUBC2000PPDataUpdateCoordinator], BinarySensorEntity
):
    """Representation of an Bolid sensor from HUB-C2000PP data."""

    def __init__(
        self,
        device: dict[str, Any],
        coordinator: HUBC2000PPDataUpdateCoordinator,
    ) -> None:
        """Initialize the Bolid sensor."""
        super().__init__(coordinator)

        device_name = self.name
        device_uid = f'{device["dev"]}.{device["sh"]}'

        if device["type"] == "smokeSensor":
            device_name = "ДИП-34А"
            device_class = BinarySensorDeviceClass.SMOKE

        if device["type"] == "doorSensor":
            device_name = "с2000-смк"
            device_class = BinarySensorDeviceClass.DOOR

        if device["type"] == "windowSensor":
            device_name = "с2000-смк"
            device_class = BinarySensorDeviceClass.WINDOW

        if device["type"] == "motionSensor":
            device_name = "с2000-ИК"
            device_class = BinarySensorDeviceClass.MOTION

        self._attr_device_info = DeviceInfo(
            identifiers={
                (DOMAIN, device_uid),
            },
            manufacturer="Bolid",
            model=device["type"],
            name=device_name,
        )

        self._attr_name = device["desc"]
        self._attr_unique_id = device["uid"]
        self._type = device["type"]
        self._attr_device_class = device_class

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        device: dict[str, Any] | None = next(
            (
                device
                for device in self.coordinator.data["zones"]
                if device["uid"] == self.unique_id
            ),
            None,
        )

        if device:
            state_code = int(device["state"])
            if device["state"] != "-":
                if device["type"] == "smokeSensor":
                    is_on = state_code in FIRE_EVENTS

                if device["type"] in ("doorSensor", "windowSensor"):
                    is_on = state_code in DOOR_EVENTS

                if device["type"] == "motionSensor":
                    is_on = state_code in MOTION_EVENTS

                # Call update entry only if data was changed
                if self._attr_is_on != is_on:
                    self._attr_is_on = is_on
                    super()._handle_coordinator_update()

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()
