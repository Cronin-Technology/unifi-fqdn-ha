function relativeTime(isoString) {
  if (!isoString || isoString === "unknown" || isoString === "unavailable") return "never";
  const diff = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000);
  if (diff < 60)    return `${diff}s ago`;
  if (diff < 3600)  return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

class UnifiFqdnCard extends HTMLElement {

  set hass(hass) {
    if (!this.content) {
      this.innerHTML = `
        <ha-card>
          <div class="card-content" id="unifi-fqdn-content"></div>
        </ha-card>
      `;
      this.content = this.querySelector("#unifi-fqdn-content");
    }

    const config        = this._config;
    const countEntity   = hass.states[config.count_entity];
    const lastRunEntity = hass.states[config.last_run_entity];
    const count         = countEntity   ? countEntity.state  : "?";
    const host          = countEntity?.attributes?.host ?? "UniFi FQDN";

    const summary = [config.count_entity, config.last_run_entity];
    const fqdnSensors = Object.values(hass.states)
      .filter(e => e.entity_id.startsWith("sensor.unifi_fqdn_"))
      .filter(e => !summary.includes(e.entity_id))
      .sort((a, b) => (a.attributes.friendly_name ?? "").localeCompare(b.attributes.friendly_name ?? ""));

    const badge = state => {
      if (state === "ok")     return "🟢";
      if (state === "error")  return "🔴";
      if (state === "no_ips") return "🟡";
      return "⚪";
    };

    const rows = fqdnSensors.map(s => {
      const name = (s.attributes.friendly_name ?? s.entity_id).replace("Unifi FQDN: ", "");
      return `<li style="padding:3px 0;font-size:0.95em;">${badge(s.state)}&nbsp;${name}</li>`;
    }).join("");

    this.content.innerHTML = `
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
        <ha-icon icon="mdi:shield-network-outline"></ha-icon>
        <span style="font-size:1.05em;font-weight:600;">${host}</span>
      </div>

      <div style="display:flex;gap:20px;font-size:0.85em;color:var(--secondary-text-color);margin-bottom:12px;">
        <span>
          <ha-icon icon="mdi:check-circle-outline"></ha-icon>
          ${count} ${count === "1" ? "group" : "groups"}
        </span>
        <span>
          <ha-icon icon="mdi:clock-outline"></ha-icon>
          ${relativeTime(lastRunEntity?.state)}
        </span>
      </div>

      <hr style="border:none;border-top:1px solid var(--divider-color);margin:0 0 12px;">

      <div style="font-size:0.78em;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;color:var(--secondary-text-color);margin-bottom:8px;">
        Managed FQDNs
      </div>

      ${fqdnSensors.length
        ? `<ul style="list-style:none;margin:0;padding:0;">${rows}</ul>`
        : `<p style="font-size:0.88em;font-style:italic;color:var(--secondary-text-color);">
             No FQDN groups found. Name a UniFi group <code>fqdn:&lt;hostname&gt;</code>.
           </p>`
      }
    `;
  }

  setConfig(config) {
    if (!config.count_entity || !config.last_run_entity) {
      throw new Error("count_entity and last_run_entity are required");
    }
    this._config = config;
  }

  getCardSize() { return 4; }

  static getStubConfig() {
    return {
      count_entity:    "sensor.unifi_fqdn_group_count",
      last_run_entity: "sensor.unifi_fqdn_last_updated",
    };
  }
}

customElements.define("unifi-fqdn-card", UnifiFqdnCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type:        "unifi-fqdn-card",
  name:        "UniFi FQDN Card",
  description: "Displays UniFi FQDN firewall group status",
  preview:     true,
});
