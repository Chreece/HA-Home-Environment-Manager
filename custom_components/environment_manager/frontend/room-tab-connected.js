/* HEM v0.8.1b1 - connected room tabs.
 * The unchanged base card is still the canonical source for all controls;
 * this small resource fixes the visual seam in its Shadow DOM only.
 */
(() => {
  'use strict';
  const selector = 'home-environment-manager-card';
  const marker = 'data-hem-room-tab-connected081';
  const css = `
    .hem-room-fold87 {
      --hem-room-outline081:var(--aqa-edge);
      border:0;border-radius:0;background:transparent;
    }
    .hem-room-fold87.hem-room-attention {
      --hem-room-outline081:color-mix(in srgb,var(--aqa-amber),transparent 55%);
    }
    .hem-room-fold87>summary.hem-room-glance87 {
      display:flex;flex-wrap:wrap;align-items:center;gap:0;
      position:relative;isolation:isolate;min-height:0;padding:0;
      background:transparent;overflow:visible;
    }
    .hem-room-fold87>summary.hem-room-glance87::before {
      content:"";position:absolute;inset:35px 0 0;
      box-sizing:border-box;z-index:0;pointer-events:none;
      border:1px solid var(--hem-room-outline081);
      border-radius:0 10px 10px 10px;
      background:var(--aqa-surface);
    }
    .hem-room-tabline080 {
      display:flex;flex:0 0 100%;min-width:0;max-width:100%;
      box-sizing:border-box;height:36px;padding:0;border:0;
      position:relative;z-index:1;
    }
    .hem-room-tab080 {
      display:inline-flex;align-items:center;gap:6px;min-width:0;
      max-width:100%;height:36px;box-sizing:border-box;
      padding:0 2px 0 10px;position:relative;z-index:2;
      border:1px solid var(--hem-room-outline081);
      border-top-color:var(--aqa-green);
      border-bottom-color:var(--aqa-surface);
      border-radius:10px 10px 0 0;
      background:var(--aqa-surface);
    }
    .hem-room-tab080 .hem-room-name87 {
      min-width:0;font-size:13px;line-height:1.35;
    }
    .hem-room-tab080 .hem-room-settings114 {
      flex:0 0 34px;width:34px;height:34px;border-radius:6px;
    }
    .hem-room-overview080 {
      display:flex;align-items:center;flex:1 1 0;min-width:0;
      gap:5px;box-sizing:border-box;padding:7px 8px;
      position:relative;z-index:1;
    }
    .hem-room-glance87>.hem-room-overview080 .hem-room-air89 {
      min-width:0;max-width:none;
    }
    .hem-room-glance87>.hem-room-overview080 .hem-room-alerts87 {
      margin-inline-start:auto;
    }
    .hem-room-fold87>summary.hem-room-glance87>ha-icon:last-child {
      align-self:center;margin-inline:0 8px;position:relative;z-index:1;
    }
    .hem-room-fold87[open]>summary.hem-room-glance87::before {
      border-bottom-color:transparent;
      border-bottom-left-radius:0;border-bottom-right-radius:0;
    }
    .hem-room-fold87[open]>.hem-room-body87 {
      border:1px solid var(--hem-room-outline081);border-top:0;
      border-radius:0 0 10px 10px;background:var(--aqa-surface);
    }
    @container hem-rooms107 (max-width:340px) {
      .hem-room-tabline080 {padding-inline:0}
      .hem-room-overview080 {gap:3px;padding-inline:6px}
      .hem-room-fold87>summary.hem-room-glance87>ha-icon:last-child {
        margin-inline-end:6px;
      }
    }
  `;
  const install = () => {
    const Card = customElements.get(selector);
    if (!Card || Card.prototype.__hemConnectedTab081) return;
    const previous = Card.prototype._styles;
    if (typeof previous !== 'function') return;
    Card.prototype._styles = function(...args) {
      return previous.apply(this, args) + '<style ' + marker + '>' + css + '</style>';
    };
    Object.defineProperty(Card.prototype, '__hemConnectedTab081', {value:true});
    // If Home Assistant finished a first render before this extra resource
    // loaded, restyle that instance now; later renders use _styles above.
    for (const card of document.querySelectorAll(selector)) {
      const root = card.shadowRoot;
      if (!root || root.querySelector('style[' + marker + ']')) continue;
      const style = document.createElement('style');
      style.setAttribute(marker, '');
      style.textContent = css;
      root.appendChild(style);
    }
  };
  if (customElements.get(selector)) install();
  else customElements.whenDefined(selector).then(install);
})();
