from __future__ import annotations

import logging
import dns.resolver
import requests
import urllib3

from datetime import timedelta
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_LOGGER = logging.getLogger(__name__)


class UnifiFqdnCoordinator(DataUpdateCoordinator):

    def __init__(self, hass: HomeAssistant, config: dict) -> None:
        self.host         = config["host"]
        self.api_key      = config["api_key"]
        self.verify_ssl   = config.get("verify_ssl", False)
        self.dns_resolver = config.get("dns_resolver", "1.1.1.1")

        super().__init__(
            hass,
            _LOGGER,
            name="UniFi FQDN",
            update_interval=timedelta(seconds=config.get("interval", 300)),
        )

    # ------------------------------------------------------------------ #
    # Session
    # ------------------------------------------------------------------ #

    def _get_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update({
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        })
        session.verify = self.verify_ssl
        return session

    # ------------------------------------------------------------------ #
    # DNS
    # ------------------------------------------------------------------ #

    def _resolve_fqdn(self, fqdn: str, record_types=("A",)) -> list[str]:
        resolver = dns.resolver.Resolver()
        resolver.nameservers = [self.dns_resolver]
        ips = []
        for record_type in record_types:
            try:
                answers = resolver.resolve(fqdn, record_type)
                ips.extend(str(r) for r in answers)
            except (
                dns.resolver.NoAnswer,
                dns.resolver.NXDOMAIN,
                dns.exception.DNSException,
            ):
                pass
        return ips

    # ------------------------------------------------------------------ #
    # UniFi API
    # ------------------------------------------------------------------ #

    def _list_firewall_groups(self, session: requests.Session) -> list[dict]:
        resp = session.get(
            f"https://{self.host}/proxy/network/api/s/default/rest/firewallgroup"
        )
        resp.raise_for_status()
        return resp.json().get("data", [])

    def _get_firewall_group(self, session: requests.Session, group_id: str) -> dict:
        resp = session.get(
            f"https://{self.host}/proxy/network/api/s/default/rest/firewallgroup/{group_id}"
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])
        if not data:
            raise ValueError(f"No data returned for group '{group_id}'")
        return data[0]

    def _update_firewall_group(
        self, session: requests.Session, existing: dict, ips: list[str]
    ) -> None:
        payload = {**existing, "group_members": ips}
        resp = session.put(
            f"https://{self.host}/proxy/network/api/s/default/rest/firewallgroup/{existing['_id']}",
            json=payload,
        )
        resp.raise_for_status()

    # ------------------------------------------------------------------ #
    # Poll
    # ------------------------------------------------------------------ #

    async def _async_update_data(self) -> dict:
        """Called by HA on every update interval. Returns state for sensors."""
        try:
            return await self.hass.async_add_executor_job(self._update_all_groups)
        except requests.HTTPError as e:
            raise UpdateFailed(f"HTTP error communicating with UDM: {e}") from e
        except Exception as e:
            raise UpdateFailed(f"Unexpected error: {e}") from e

    def _update_all_groups(self) -> dict:
        """Synchronous worker — runs in executor thread."""
        session = self._get_session()
        all_groups = self._list_firewall_groups(session)

        fqdn_groups = [
            {
                "id":   g["_id"],
                "name": g["name"],
                "fqdn": g["name"][len("fqdn:"):],
            }
            for g in all_groups
            if g.get("name", "").startswith("fqdn:")
        ]

        results = {}
        for g in fqdn_groups:
            fqdn = g["fqdn"]
            ips  = self._resolve_fqdn(fqdn)

            if not ips:
                _LOGGER.warning("No IPs resolved for %s, skipping.", fqdn)
                results[g["name"]] = {"fqdn": fqdn, "ips": [], "status": "no_ips"}
                continue

            try:
                existing = self._get_firewall_group(session, g["id"])
                self._update_firewall_group(session, existing, ips)
                _LOGGER.info("Updated '%s' -> %s", g["name"], ips)
                results[g["name"]] = {"fqdn": fqdn, "ips": ips, "status": "ok"}
            except Exception as e:
                _LOGGER.error("Failed to update '%s': %s", g["name"], e)
                results[g["name"]] = {"fqdn": fqdn, "ips": [], "status": "error"}

        return results