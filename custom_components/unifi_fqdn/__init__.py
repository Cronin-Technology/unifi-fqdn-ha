from __future__ import annotations

import os
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant
from homeassistant.components.http import StaticPathConfig

from .coordinator import UnifiFqdnCoordinator

DOMAIN    = "unifi_fqdn"
PLATFORMS = ["sensor"]
_LOGGER   = logging.getLogger(__name__)
_CARD_URL = "/unifi_fqdn/www/unifi-fqdn-card.js"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Serve the Lovelace card JS and register it as a frontend resource."""
    www_path = os.path.join(os.path.dirname(__file__), "www")

    await hass.http.async_register_static_paths([
        StaticPathConfig(
            url_path="/unifi_fqdn/www",
            path=www_path,
            cache_headers=True,
        )
    ])

    # add_extra_js_url was removed in HA 2024.4 — try it for older installs,
    # then fall through to the Lovelace resources API.
    try:
        from homeassistant.components.frontend import add_extra_js_url  # type: ignore[attr-defined]
        add_extra_js_url(hass, _CARD_URL)
        return True
    except (ImportError, AttributeError):
        pass

    # Modern approach: add to Lovelace resource storage once HA has fully started
    # (the lovelace component must be initialised first).
    async def _register_lovelace_resource(_=None) -> None:
        try:
            resources = hass.data.get("lovelace", {}).get("resources")
            if resources is None:
                _LOGGER.warning(
                    "Lovelace resources storage not available. "
                    "Add %s manually as a JS module resource.", _CARD_URL
                )
                return

            existing = list(resources.async_items())
            if any(r.get("url") == _CARD_URL for r in existing):
                return  # already registered, nothing to do

            await resources.async_create_item({"res_type": "module", "url": _CARD_URL})
            _LOGGER.info("Registered Lovelace resource: %s", _CARD_URL)
        except Exception as err:
            _LOGGER.warning("Could not register Lovelace resource %s: %s", _CARD_URL, err)

    if hass.is_running:
        await _register_lovelace_resource()
    else:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _register_lovelace_resource)

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
