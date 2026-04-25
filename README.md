# UniFi FQDN Firewall Group Updater

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/Cronin-Technology/unifi-fqdn-ha)](https://github.com/Cronin-Technology/unifi-fqdn-ha/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A [HACS](https://hacs.xyz/) custom integration for Home Assistant that brings **FQDN-based firewall group management** to UniFi Dream Machine and UDM Pro devices.

UniFi firewall rules require static IP addresses — this integration bridges that gap by automatically resolving domain names to their current IP addresses and keeping your firewall groups in sync on a configurable schedule.

---

## How It Works

Any firewall group in UniFi whose name begins with `fqdn:` is automatically managed by this integration. The domain name following the prefix is resolved via DNS, and the resulting IP addresses are pushed into that firewall group via the UniFi local API.

```
Firewall Group:  fqdn:github.com
                      └──────────────── resolved IPs pushed to UniFi
                        140.82.112.4
                        140.82.114.3
                        ...
```

On every update interval the coordinator:
1. Lists all firewall groups on your UDM
2. Filters for groups whose name starts with `fqdn:`
3. Resolves each domain via the configured DNS resolver (A records)
4. Updates the corresponding firewall group's members in UniFi

If a domain resolves to no IPs, the group is skipped and logged as a warning rather than being cleared.

---

## Features

- 🔍 **Automatic DNS resolution** — uses `dnspython` with a configurable upstream resolver (Cloudflare, Google, or custom)
- 🔄 **Configurable polling interval** — default 300 seconds, adjustable at any time via Options
- 📡 **Sensor entities per group** — state reflects update status (`ok`, `no_ips`, `error`), attributes include the resolved IPs
- 📊 **Summary sensors** — group count and last-updated timestamp included automatically
- 🃏 **Custom Lovelace card** — auto-registered as a frontend JS module resource
- ⚙️ **Full UI config flow** — set up and reconfigured entirely through the HA UI
- 🔐 **API key auth** — uses the UniFi OS local API key (`X-API-Key` header), no username/password needed
- 🔒 **SSL verification toggle** — can disable SSL verification for self-signed UDM certificates

---

## Requirements

- Home Assistant 2023.x or later
- [HACS](https://hacs.xyz/) installed
- A UniFi Dream Machine, UDM Pro, or UDR running UniFi OS with the **Network** application
- A **local API key** generated from your UDM (not a Ubiquiti SSO account)

---

## Installation

### Via HACS (Recommended)

1. Open HACS in Home Assistant.
2. Go to **Integrations** → click the three-dot menu → **Custom repositories**.
3. Add `https://github.com/Cronin-Technology/unifi-fqdn-ha` and select **Integration** as the category.
4. Search for **UniFi FQDN Firewall Group Updater** and click **Download**.
5. Restart Home Assistant.

### Manual

1. Copy the `custom_components/unifi_fqdn/` directory into your HA `config/custom_components/` folder.
2. Restart Home Assistant.

---

## Generating a UniFi API Key

1. Log in to your UDM's local web UI.
2. Go to **Settings → Control Plane → Integrations → API Keys** (UniFi OS 3.x+).
3. Create a new API key with admin-level access and copy it — you will need it during setup.

> ⚠️ This integration uses the UniFi **local** API (`/proxy/network/api/`). Cloud-based Ubiquiti SSO credentials will not work.

---

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **UniFi FQDN Firewall Group Updater**.
3. Fill in the setup form:

| Field | Description | Default |
|---|---|---|
| **UDM IP Address** | IP or hostname of your UDM/controller | — |
| **API Key** | Local API key from UniFi OS | — |
| **Update interval (seconds)** | How often to re-resolve and sync IPs | `300` |
| **Verify SSL certificate** | Enable to validate the UDM's TLS cert | `false` |
| **DNS Resolver** | Upstream DNS server used for resolution | `1.1.1.1` |

The DNS resolver field accepts Cloudflare (`1.1.1.1`), Google (`8.8.8.8`), or any custom IP address you type in.

> Only one integration entry is allowed per UDM host. Attempting to add the same host twice will be blocked automatically.

### Updating Options

After initial setup, all fields except the host can be changed via **Settings → Devices & Services → UniFi FQDN → Configure**. Changes take effect immediately and the integration reloads automatically.

---

## Setting Up FQDN Firewall Groups

1. In the **UniFi Network** console, go to **Firewall & Security → Firewall Groups**.
2. Create a new group with type **IPv4 Address Group**.
3. Name it with the `fqdn:` prefix followed by the domain to manage:

   | Group Name | Domain resolved |
   |---|---|
   | `fqdn:github.com` | `github.com` |
   | `fqdn:api.example.com` | `api.example.com` |
   | `fqdn:update.myservice.io` | `update.myservice.io` |

4. Leave the IP member list empty — the integration will populate it on the next poll.

The integration discovers all `fqdn:` groups dynamically. Adding a new group in UniFi requires no changes to HA — it will be picked up automatically on the next update cycle.

---

## Sensors

The integration creates the following entities automatically.

### Summary Sensors (always present)

| Entity | Description |
|---|---|
| `sensor.unifi_fqdn_last_updated` | Timestamp of the last successful coordinator run |
| `sensor.unifi_fqdn_group_count` | Number of `fqdn:` groups currently tracked; attributes list all managed domains |

### Per-Group Sensors (one per `fqdn:` group)

Entity name format: `sensor.unifi_fqdn_<domain>`

| State value | Meaning |
|---|---|
| `ok` | Group resolved and updated successfully |
| `no_ips` | DNS returned no results; group was skipped |
| `error` | An error occurred updating this group in UniFi |

**Attributes:**

| Attribute | Description |
|---|---|
| `fqdn` | The domain being resolved |
| `resolved_ips` | List of IPs currently pushed to the firewall group |

Per-group sensor entities are created dynamically as new `fqdn:` groups are discovered, and removed from HA automatically if they disappear from UniFi.

---

## Lovelace Card

The integration ships a custom Lovelace card that is automatically registered as a JS module resource at:

```
/unifi_fqdn/www/unifi-fqdn-card.js
```

If auto-registration fails (visible in the HA log as a warning), you can add it manually:

1. Go to **Settings → Dashboards → three-dot menu → Resources**.
2. Add `/unifi_fqdn/www/unifi-fqdn-card.js` as a **JavaScript Module**.

To add the card to a dashboard:

```yaml
type: custom:unifi-fqdn-card
```

---

## Troubleshooting

**Groups not being picked up**
- Confirm the group name starts exactly with `fqdn:` — the prefix is case-sensitive.
- Check **Settings → System → Logs** and filter for `unifi_fqdn`.

**`no_ips` status on a group**
- The configured DNS resolver returned no A records for that domain.
- Test manually: `nslookup <domain> 1.1.1.1` from your HA host.
- Consider switching to an internal resolver if the domain is on a private DNS zone.

**`invalid_auth` during setup**
- Ensure you are using a **local API key**, not a Ubiquiti cloud password.
- Confirm the API key has admin-level access to the Network application.

**`cannot_connect` during setup**
- Verify the UDM IP is reachable from your Home Assistant host on port `443`.
- If using a self-signed certificate, ensure **Verify SSL** is set to `false`.

**SSL warnings in logs**
- SSL verification is disabled by default to accommodate UDM self-signed certificates. `urllib3` warnings are suppressed intentionally. Enable **Verify SSL** only if your UDM has a valid trusted certificate.

**Lovelace card not loading**
- Check the HA log for a line containing `Could not register Lovelace resource`. If present, add the resource manually as described above.
- The auto-registration method differs between HA versions. On HA 2024.4+, the integration uses the Lovelace resources storage API; on older versions it uses `add_extra_js_url`.

---

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| `dnspython` | `2.6.1` | DNS resolution with configurable nameserver |
| `requests` | HA bundled | UniFi local API communication |

---

## Contributing

Pull requests are welcome. For significant changes, please open an issue first.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes
4. Push and open a pull request

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Acknowledgments

- [UniFi Network API](https://ubntwiki.com/products/software/unifi-controller/api) — community-documented local API reference
- [HACS](https://hacs.xyz/) — Home Assistant Community Store
- [dnspython](https://www.dnspython.org/) — DNS toolkit for Python