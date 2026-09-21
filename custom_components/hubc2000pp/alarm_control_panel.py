"""Support for HUB-C2000PP alarm_control_panel."""
import logging
from typing import Any
from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import HUBC2000PPDataUpdateCoordinator
from .const import ARMED_EVENTS, ARMING_EVENTS, DISARMED_EVENTS, DOMAIN, ALARM_EVENTS
from .hubc2000pp import ArmFailed, DisarmFailed, arm_partition, disarm_partition

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Bolid sensor."""
    coordinator: HUBC2000PPDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    devices = coordinator.data["parts"]
    entities = []
    for device in devices:
        if device["desc"]:
            entities.append(AlarmControlPanelDevice(device, coordinator))

    async_add_entities(entities)


class AlarmControlPanelDevice(
    CoordinatorEntity[HUBC2000PPDataUpdateCoordinator], AlarmControlPanelEntity
):
    """Representation of an Bolid partition from HUB-C2000PP data."""

    def __init__(
        self, device: dict[str, Any], coordinator: HUBC2000PPDataUpdateCoordinator
    ) -> None:
        """Initialize the Bolid partition."""
        super().__init__(coordinator)

        device_name = f'Раздел {device["id"]}'
        device_uid = f'partition_{device["id"]}'

        self._attr_device_info = DeviceInfo(
            identifiers={
                (DOMAIN, device_uid),
            },
            manufacturer="Bolid",
            model="Раздел",
            name=device_name,
        )

        self.partition_id = int(device["id"])
        self._attr_name = device["desc"]
        self._attr_unique_id = device_uid
        self._attr_code_arm_required = False
        self._attr_code_format = None
        self._attr_extra_state_attributes = {}
        self._attr_supported_features = AlarmControlPanelEntityFeature.ARM_AWAY

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        """Disarm partition."""
        _LOGGER.warning("DISARM partition %d", self.partition_id)
        coordinator = self.coordinator
        result = await disarm_partition(
            self.partition_id,
            coordinator.host,
            coordinator.port,
        )
        if not result:
            _LOGGER.error("Can't DISARM partition: %d, self.partition_id")
            raise DisarmFailed()

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        """Arm partition."""
        _LOGGER.warning("ARM partition %s", self._attr_unique_id)
        coordinator = self.coordinator
        result = await arm_partition(
            self.partition_id,
            coordinator.host,
            coordinator.port,
        )
        if not result:
            _LOGGER.error("Can't ARM partition: %s", self._attr_unique_id)
            raise ArmFailed()

    def _get_status_by_code(self, code: int) -> str:
        """Get status or event description for code."""
        if code in ARMED_EVENTS:
            return AlarmControlPanelState.ARMED_AWAY
        if code in ARMING_EVENTS:
            return AlarmControlPanelState.ARMING
        if code in DISARMED_EVENTS:
            return AlarmControlPanelState.DISARMED
        if code in ALARM_EVENTS:
            return AlarmControlPanelState.TRIGGERED
        return None
        # result = DEVICE_STATUSES_DICT.get(code, None)
        # if not result:
        #    result = DEVICE_EVENTS_DICT.get(code, DEVICE_STATUSES_DICT[0])
        # return result

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        device: dict[str, Any] | None = next(
            (
                device
                for device in self.coordinator.data["parts"]
                if device["uid"] == self.unique_id
            ),
            None,
        )

        if device:
            current_code = None
            if (
                self._attr_extra_state_attributes
                and "code" in self._attr_extra_state_attributes
            ):
                current_code = self._attr_extra_state_attributes.get("stat", None)
            state_code = int(device["stat"])
            if current_code != state_code:
                self._attr_extra_state_attributes = {"code": state_code}
                #self._attr_state = self._get_status_by_code(state_code)
                super()._handle_coordinator_update()

    @property
    def alarm_state(self) -> AlarmControlPanelState | None:
        """Return the current state of the alarm."""
        device: dict[str, Any] | None = next(
            (
                device
                for device in self.coordinator.data["parts"]
                if device["uid"] == self.unique_id
            ),
            None,
        )

        if device:
            return self._get_status_by_code(int(device["stat"]))
        return None

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()
