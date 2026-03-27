from __future__ import annotations

import voluptuous as vol
import requests
import urllib3

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers import selector

try:
    from homeassistant.config_entries import ConfigFlowResult as FlowResult
except ImportError:
    from homeassistant.data_entry_flow import FlowResult  # type: ignore[attr-defined]

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DOMAIN = "unifi_fqdn"

DNS_RESOLVER_OPTIONS = [
    {"value": "1.1.1.1", "label": "Cloudflare (1.1.1.1)"},
    {"value": "8.8.8.8", "label": "Google (8.8.8.8)"},
]
DEFAULT_DNS_RESOLVER = "1.1.1.1"

DNS_RESOLVER_SELECTOR = selector.SelectSelector(
    selector.SelectSelectorConfig(
        options=DNS_RESOLVER_OPTIONS,
        custom_value=True,
        mode=selector.SelectSelectorMode.DROPDOWN,
    )
)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("host"): str,
        vol.Required("api_key"): str,
        vol.Optional("interval", default=300): int,
        vol.Optional("verify_ssl", default=False): bool,
        vol.Optional("dns_resolver", default=DEFAULT_DNS_RESOLVER): DNS_RESOLVER_SELECTOR,
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

    @staticmethod
    @config_entries.callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "UnifiFqdnOptionsFlow":
        return UnifiFqdnOptionsFlow(config_entry)

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


class UnifiFqdnOptionsFlow(config_entries.OptionsFlow):
    """Allow reconfiguring API key, interval, SSL verification, and DNS resolver."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        current = {**self._config_entry.data, **self._config_entry.options}

        if user_input is not None:
            error = await self.hass.async_add_executor_job(
                test_connection,
                current["host"],
                user_input["api_key"],
                user_input["verify_ssl"],
            )
            if error is None:
                return self.async_create_entry(title="", data=user_input)
            errors["base"] = error

        schema = vol.Schema(
            {
                vol.Required("api_key", default=current.get("api_key", "")): str,
                vol.Optional("interval", default=current.get("interval", 300)): int,
                vol.Optional("verify_ssl", default=current.get("verify_ssl", False)): bool,
                vol.Optional(
                    "dns_resolver",
                    default=current.get("dns_resolver", DEFAULT_DNS_RESOLVER),
                ): DNS_RESOLVER_SELECTOR,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
        )
