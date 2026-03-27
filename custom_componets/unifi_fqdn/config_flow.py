from __future__ import annotations

import voluptuous as vol
import requests
import urllib3

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DOMAIN = "unifi_fqdn"

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("host"): str,
        vol.Required("api_key"): str,
        vol.Optional("interval", default=300): int,
        vol.Optional("verify_ssl", default=False): bool,
    }
)


def test_connection(host: str, api_key: str, verify_ssl: bool) -> str | None:
    """Return None on success or an error key string."""
    try:
        resp = requests.get(
            f"https://{host}/proxy/network/api/s/default/stat/sysinfo",
            headers={"X-API-Key": api_key, "Content-Type": "application/json"},
            verify=verify_ssl,
            timeout=10,
        )
        if resp.status_code == 401:
            return "invalid_auth"
        if resp.status_code == 403:
            return "invalid_auth"
        resp.raise_for_status()
        return None
    except requests.exceptions.ConnectionError:
        return "cannot_connect"
    except Exception:
        return "unknown"


class UnifiFqdnConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow for UniFi FQDN."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            # Prevent duplicate entries for the same host
            await self.async_set_unique_id(user_input["host"])
            self._abort_if_unique_id_configured()

            error = await self.hass.async_add_executor_job(
                test_connection,
                user_input["host"],
                user_input["api_key"],
                user_input["verify_ssl"],
            )

            if error is None:
                return self.async_create_entry(
                    title=f"UniFi FQDN ({user_input['host']})",
                    data=user_input,
                )
            errors["base"] = error

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )