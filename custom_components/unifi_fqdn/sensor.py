from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN
from .coordinator import UnifiFqdnCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: UnifiFqdnCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        UnifiFqdnSensor(coordinator, group_name)
        for group_name in coordinator.data
    ]
    async_add_entities(entities, update_before_add=False)


class UnifiFqdnSensor(CoordinatorEntity, SensorEntity):

    def __init__(self, coordinator: UnifiFqdnCoordinator, group_name: str) -> None:
        super().__init__(coordinator)
        self._group_name  = group_name
        self._attr_name   = f"UniFi FQDN {group_name}"
        self._attr_unique_id = f"unifi_fqdn_{group_name}"

    @property
    def native_value(self) -> str:
        """Last known status for this group."""
        group = self.coordinator.data.get(self._group_name, {})
        return group.get("status", "unknown")

    @property
    def extra_state_attributes(self) -> dict:
        group = self.coordinator.data.get(self._group_name, {})
        return {
            "fqdn": group.get("fqdn"),
            "resolved_ips": group.get("ips", []),
        }