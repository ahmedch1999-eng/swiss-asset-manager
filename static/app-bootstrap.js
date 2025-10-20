// Backend-first bootstrap: load config dictionaries once and expose to window
(function(){
  const BOOTSTRAP_URL = '/api/bootstrap';
  async function loadBootstrap(){
    try {
      const res = await fetch(BOOTSTRAP_URL, { cache: 'no-store' });
      if(!res.ok) throw new Error('bootstrap fetch failed: ' + res.status);
      const json = await res.json();
      if(!json.success) throw new Error(json.error || 'bootstrap error');
      const d = json.data || {};
      // Expose to global without overriding if already present
      window.__bootstrap = Object.assign({
        swiss_stocks: [], benchmark_indices: {}, indices: {}, other_assets: {},
        market_cycles: {}, swiss_bank_portfolios: {}, scenarios: {}, translations: {}
      }, d);
      // Optional: expose shortcuts (non-breaking – only used if code reads them)
      window.SWISS_STOCKS_BOOT = d.swiss_stocks || [];
      window.INDICES_BOOT = d.indices || {};
      window.OTHER_ASSETS_BOOT = d.other_assets || {};
      window.TRANSLATIONS_BOOT = d.translations || {};
      console.log('[bootstrap] loaded');
    } catch(err){
      console.warn('[bootstrap] fallback (offline or API down):', err.message);
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', loadBootstrap);
  else loadBootstrap();
})();
