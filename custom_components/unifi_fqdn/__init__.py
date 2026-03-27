from __future__ import annotations

import os
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig

from .coordinator import UnifiFqdnCoordinator

DOMAIN    = "unifi_fqdn"
PLATFORMS = ["sensor"]
_LOGGER   = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register the Lovelace card JS as a static resource."""
    www_path = os.path.join(os.path.dirname(__file__), "www")

    await hass.http.async_register_static_paths([
        StaticPathConfig(
            url_path  = f"/unifi_fqdn/www",
            path      = www_path,
            cache_headers = True,
        )
    ])

    add_extra_js_url(hass, "/unifi_fqdn/www/unifi-fqdn-card.js")
    return True



async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    config = {**entry.data, **entry.options}
    coordinator = UnifiFqdnCoordinator(hass, config)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)