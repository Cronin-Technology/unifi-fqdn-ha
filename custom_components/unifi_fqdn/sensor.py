from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
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

    known_groups: set[str] = set()

    @callback
    def _add_new_entities() -> None:
        new_groups = set(coordinator.data) - known_groups
        if new_groups:
            known_groups.update(new_groups)
            async_add_entities(
                [UnifiFqdnSensor(coordinator, name) for name in new_groups]
            )

    _add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_entities))


class UnifiFqdnSensor(CoordinatorEntity, SensorEntity):

    def __init__(self, coordinator: UnifiFqdnCoordinator, group_name: str) -> None:
        super().__init__(coordinator)
        self._group_name     = group_name
        self._attr_name      = f"UniFi FQDN {group_name}"
        self._attr_unique_id = f"unifi_fqdn_{group_name}"

    @callback
    def _handle_coordinator_update(self) -> None:
        if self._group_name not in self.coordinator.data:
            self.hass.async_create_task(self.async_remove())
            return
        super()._handle_coordinator_update()

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