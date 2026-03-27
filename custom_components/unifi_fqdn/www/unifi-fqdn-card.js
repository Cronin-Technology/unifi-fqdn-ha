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

    const config   = this._config;
    const countEntity    = hass.states[config.count_entity];
    const lastRunEntity  = hass.states[config.last_run_entity];
    const count    = countEntity    ? countEntity.state    : "?";
    const lastRun  = lastRunEntity  ? lastRunEntity.state  : "unknown";

    // Collect all fqdn sensors
    const summary = [config.count_entity, config.last_run_entity];
    const fqdnSensors = Object.values(hass.states)
      .filter(e => e.entity_id.startsWith("sensor.unifi_fqdn_"))
      .filter(e => !summary.includes(e.entity_id))
      .sort((a, b) => a.attributes.friendly_name?.localeCompare(b.attributes.friendly_name));

    const badge = state => {
      if (state === "ok")     return "🟢";
      if (state === "error")  return "🔴";
      if (state === "no_ips") return "🟡";
      return "⚪";
    };

    const rows = fqdnSensors.map(s => {
      const name = (s.attributes.friendly_name || s.entity_id)
        .replace("Unifi FQDN ", "")
        .replace("UniFi FQDN: ", "");
      const ips = s.attributes.resolved_ips || [];
      return `
        <tr>
          <td>${badge(s.state)}</td>
          <td style="font-size:0.9em;">${name}</td>
          <td style="font-size:0.85em;">${s.state}</td>
          <td style="font-size:0.85em;">${ips.length ? ips.join("<br>") : "—"}</td>
        </tr>
      `;
    }).join("");

    this.content.innerHTML = `
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
        <ha-icon icon="mdi:shield-network-outline"></ha-icon>
        <span style="font-size:1.1em;font-weight:500;">
          ${countEntity?.attributes?.friendly_name ?? "UniFi FQDN"}
        </span>
      </div>

      <div style="display:flex;flex-direction:column;gap:6px;margin-bottom:12px;">
        <div>
          <ha-icon icon="mdi:check-circle-outline"></ha-icon>
          <strong>Active Groups</strong>
          <code>${count} ${count === "1" ? "group" : "groups"}</code>
        </div>
        <div>
          <ha-icon icon="mdi:clock-outline"></ha-icon>
          <strong>Last Run</strong>
          <code>${lastRun !== "unknown" && lastRun !== "unavailable" ? lastRun : "never"}</code>
        </div>
      </div>

      <hr style="margin-bottom:12px;">

      ${fqdnSensors.length ? `
        <table style="width:100%;border-collapse:collapse;">
          <thead>
            <tr style="opacity:0.6;font-size:0.8em;">
              <th style="text-align:left;padding:4px 8px;"></th>
              <th style="text-align:left;padding:4px 8px;">FQDN</th>
              <th style="text-align:left;padding:4px 8px;">Status</th>
              <th style="text-align:left;padding:4px 8px;">Resolved IPs</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      ` : `<p><em>No FQDN groups found. Name a UniFi group <code>fqdn:&lt;hostname&gt;</code>.</em></p>`}
    `;
  }

  setConfig(config) {
    if (!config.count_entity || !config.last_run_entity) {
      throw new Error("count_entity and last_run_entity are required");
    }
    this._config = config;
  }

  getCardSize() { return 4; }

  static getConfigElement() {
    return document.createElement("unifi-fqdn-card-editor");
  }

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