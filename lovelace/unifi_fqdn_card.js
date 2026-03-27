/**
 * UniFi FQDN Card — custom Lovelace card
 *
 * Installation:
 *   1. Copy this file to your HA config's www/ folder
 *      e.g.  /config/www/unifi_fqdn_card.js
 *   2. In HA go to Settings → Dashboards → ⋮ → Resources → Add resource
 *      URL:  /local/unifi_fqdn_card.js
 *      Type: JavaScript module
 *   3. Add a Manual card to your dashboard with:
 *        type: custom:unifi-fqdn-card
 */

const SUMMARY_IDS = [
  'sensor.unifi_fqdn_last_updated',
  'sensor.unifi_fqdn_group_count',
];

const BADGE = {
  ok:     '🟢',
  error:  '🔴',
  no_ips: '🟡',
};

function relativeTime(isoString) {
  if (!isoString || isoString === 'unknown' || isoString === 'unavailable') {
    return 'never';
  }
  const diff = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000);
  if (diff < 60)   return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

class UniFiFqdnCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  setConfig(config) {
    this._config = config;
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _render() {
    const hass = this._hass;
    if (!hass) return;

    const countState   = hass.states['sensor.unifi_fqdn_group_count'];
    const lastRunState = hass.states['sensor.unifi_fqdn_last_updated'];

    const host     = countState?.attributes?.host ?? this._config?.title ?? 'UniFi FQDN';
    const count    = countState?.state ?? '0';
    const lastRun  = relativeTime(lastRunState?.state);

    const fqdnSensors = Object.values(hass.states)
      .filter(s => s.entity_id.startsWith('sensor.unifi_fqdn_') && !SUMMARY_IDS.includes(s.entity_id))
      .sort((a, b) => a.attributes.friendly_name?.localeCompare(b.attributes.friendly_name));

    const rows = fqdnSensors.map(s => {
      const name  = (s.attributes.friendly_name ?? s.entity_id).replace('Unifi FQDN: ', '');
      const badge = BADGE[s.state] ?? '⚪';
      return `<li class="row">${badge}&nbsp;${name}</li>`;
    }).join('');

    this.shadowRoot.innerHTML = `
      <style>
        ha-card {
          padding: 16px 20px 20px;
          box-sizing: border-box;
        }
        .title {
          font-size: 1.05em;
          font-weight: 600;
          margin-bottom: 10px;
          display: flex;
          align-items: center;
          gap: 6px;
        }
        .meta {
          display: flex;
          gap: 20px;
          font-size: 0.85em;
          color: var(--secondary-text-color);
          margin-bottom: 12px;
        }
        .meta span { display: flex; align-items: center; gap: 4px; }
        hr {
          border: none;
          border-top: 1px solid var(--divider-color);
          margin: 0 0 12px;
        }
        .label {
          font-size: 0.78em;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          color: var(--secondary-text-color);
          margin-bottom: 8px;
        }
        ul {
          list-style: none;
          margin: 0;
          padding: 0;
        }
        .row {
          padding: 3px 0;
          font-size: 0.95em;
        }
        .empty {
          font-size: 0.88em;
          color: var(--secondary-text-color);
          font-style: italic;
        }
      </style>
      <ha-card>
        <div class="title">
          <ha-icon icon="mdi:shield-network-outline"></ha-icon>
          ${host}
        </div>
        <div class="meta">
          <span><ha-icon icon="mdi:check-circle-outline"></ha-icon>${count} ${count === '1' ? 'group' : 'groups'}</span>
          <span><ha-icon icon="mdi:clock-outline"></ha-icon>${lastRun}</span>
        </div>
        <hr>
        <div class="label">Managed FQDNs</div>
        ${fqdnSensors.length
          ? `<ul>${rows}</ul>`
          : '<p class="empty">No FQDN groups found.</p>'
        }
      </ha-card>
    `;
  }

  getCardSize() {
    return Math.max(3, Math.ceil((this._fqdnCount ?? 0) / 2) + 2);
  }
}

customElements.define('unifi-fqdn-card', UniFiFqdnCard);
