"""Support for HUB-C2000PP common sensor."""
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import HUBC2000PPDataUpdateCoordinator
from .const import DEVICE_EVENTS_DICT, DEVICE_STATUSES_DICT, DOMAIN

_LOGGER = logging.getLogger(__name__)

DEVICE_CLASS_MAP = {
    "temperatureSensor": SensorDeviceClass.TEMPERATURE,
    "humiditySensor": SensorDeviceClass.HUMIDITY,
    "ripOutputSensor": SensorDeviceClass.VOLTAGE,
    "ripCurrentSensor": SensorDeviceClass.CURRENT,
    "ripBatteryVoltageSensor": SensorDeviceClass.VOLTAGE,
    "ripBatteryLevelSensor": SensorDeviceClass.BATTERY,
    "ripInputVoltageSensor": SensorDeviceClass.VOLTAGE,
}

STATE_CLASS_MAP = {
    "temperatureSensor": SensorStateClass.MEASUREMENT,
    "humiditySensor": SensorStateClass.MEASUREMENT,
    "ripOutputSensor": SensorStateClass.MEASUREMENT,
    "ripCurrentSensor": SensorStateClass.MEASUREMENT,
    "ripBatteryVoltageSensor": SensorStateClass.MEASUREMENT,
    "ripBatteryLevelSensor": SensorStateClass.MEASUREMENT,
    "ripInputVoltageSensor": SensorStateClass.MEASUREMENT,
}

UNIT_MAP = {
    "temperatureSensor": UnitOfTemperature.CELSIUS,
    "humiditySensor": PERCENTAGE,
    "ripOutputSensor": UnitOfElectricPotential.VOLT,
    "ripCurrentSensor": UnitOfElectricCurrent.AMPERE,
    "ripBatteryVoltageSensor": UnitOfElectricPotential.VOLT,
    "ripBatteryLevelSensor": PERCENTAGE,
    "ripInputVoltageSensor": UnitOfElectricPotential.VOLT,
}

ADC_SENSORS = {
    "temperatureSensor",
    "humiditySensor",
    "ripOutputSensor",
    "ripCurrentSensor",
    "ripBatteryVoltageSensor",
    "ripBatteryLevelSensor",
    "ripInputVoltageSensor",
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Bolid sensor."""
    coordinator: HUBC2000PPDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    devices = coordinator.data["zones"]
    entities = []
    for device in devices:
        if device["type"] in ADC_SENSORS:
            entities.append(Device(device, coordinator, True))
        entities.append(Device(device, coordinator, False))

    async_add_entities(entities)


class Device(CoordinatorEntity[HUBC2000PPDataUpdateCoordinator], SensorEntity):
    """Representation of an Bolid sensor from HUB-C2000PP data."""

    def __init__(
        self,
        device: dict[str, Any],
        coordinator: HUBC2000PPDataUpdateCoordinator,
        adc: bool,
    ) -> None:
        """Initialize the Bolid sensor."""
        super().__init__(coordinator)

        device_name = self.name
        device_uid = device["uid"]

        if device["type"] == "smokeSensor":
            device_name = "ДИП-34А"
            device_uid = f'{device["dev"]}.{device["sh"]}'

        if device["type"] == "doorSensor":
            device_name = "с2000-смк"
            device_uid = f'{device["dev"]}.{device["sh"]}'

        if device["type"] == "windowSensor":
            device_name = "с2000-смк"
            device_uid = f'{device["dev"]}.{device["sh"]}'

        if device["type"] == "motionSensor":
            device_name = "с2000-ИК"
            device_uid = f'{device["dev"]}.{device["sh"]}'

        if device["type"].startswith("rip"):
            device_name = "РИП12-RS"
            device_uid = device["dev"]

        if device["type"].startswith("temperature") or device["type"].startswith(
            "humidity"
        ):
            device_name = "C2000-BT"
            device_uid = f'{device["dev"]}.{device["sh"]}'

        self._attr_device_info = DeviceInfo(
            identifiers={
                (DOMAIN, device_uid),
            },
            manufacturer="Bolid",
            model=device["type"],
            name=device_name,
        )

        if adc:
            # ADC entinity with predefined types
            self._attr_name = device["desc"]
            self._attr_unique_id = device["uid"]
            self._type = device["type"]

            self._attr_device_class = DEVICE_CLASS_MAP[device["type"]]
            self._attr_state_class = STATE_CLASS_MAP[device["type"]]
            self._attr_native_unit_of_measurement = UNIT_MAP[device["type"]]
            self._attr_native_value = 0
            self._attr_suggested_display_precision = 2
        else:
            # "status" entinity
            self._attr_name = f'Статус. {device["desc"]}'
            self._attr_unique_id = f'{device["uid"]}_state'
            self._type = device["type"]

            self._attr_icon = "mdi:information-variant"
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_options = list(DEVICE_STATUSES_DICT.values()) + list(
                DEVICE_EVENTS_DICT.values()
            )

    def _get_status_by_code(self, code: int) -> str:
        """Get status or event description for code."""
        result = DEVICE_STATUSES_DICT.get(code, None)
        if not result:
            result = DEVICE_EVENTS_DICT.get(code, DEVICE_STATUSES_DICT[0])
        return result

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        device = next(
            (
                device
                for device in self.coordinator.data["zones"]
                if self.unique_id in (device["uid"], f"{device['uid']}_state")
            ),
            None,
        )
        if self._attr_device_class != SensorDeviceClass.ENUM:
            if device is not None and "adc" in device and device["adc"] != "-":
                if self._attr_native_value != device["adc"]:
                    self._attr_native_value = device["adc"]
                    super()._handle_coordinator_update()
        else:
            if device is not None and "state" in device and device["state"] != "-":
                value = self._get_status_by_code(int(device["state"]))
                code = int(device["state"])
                if self._attr_native_value != value:
                    self._attr_native_value = value
                    self._attr_extra_state_attributes = {"code": code}
                    super()._handle_coordinator_update()

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()
