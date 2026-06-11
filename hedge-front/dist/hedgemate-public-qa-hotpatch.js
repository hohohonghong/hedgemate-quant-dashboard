(() => {
  const api = (path) => fetch(path, { credentials: 'include' }).then((r) => (r.ok ? r.json() : null)).catch(() => null);
  const state = { user: null, market: null, assets: null, startedAt: Date.now() };
  const fmtDate = (value) => {
    if (!value) return '';
    const text = String(value);
    const m = text.match(/^(\d{4})-(\d{2})-(\d{2})/);
    return m ? `${m[1]}.${m[2]}.${m[3]}` : text.replaceAll('-', '.');
  };
  const fmtKst = (value) => {
    if (!value) return '';
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return fmtDate(value);
    const parts = new Intl.DateTimeFormat('ko-KR', {
      timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', hour12: false,
    }).formatToParts(d).reduce((acc, p) => (acc[p.type] = p.value, acc), {});
    return `${parts.year}.${parts.month}.${parts.day} ${parts.hour}:${parts.minute}`;
  };
  const textNodes = (root = document.body) => {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    return nodes;
  };
  const nearestElement = (node) => node && (node.nodeType === 1 ? node : node.parentElement);
  const hideElementWithText = (text) => {
    textNodes().forEach((node) => {
      if ((node.nodeValue || '').includes(text)) {
        const el = nearestElement(node);
        if (el) el.style.display = 'none';
      }
    });
  };
  const nativeSetValue = (input, value) => {
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set;
    if (setter) setter.call(input, value);
    else input.value = value;
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
  };
  const normalizedAssets = () => (state.assets || []).map((asset) => ({
    ticker: asset.ticker || asset.symbol || '',
    name: asset.label || asset.displayLabel || asset.name || asset.popularName || asset.ticker || asset.symbol || '',
    group: asset.assetClass || asset.currency || asset.exchange || '',
    search: [asset.ticker, asset.symbol, asset.label, asset.displayLabel, asset.name, asset.popularName, asset.assetClass, ...(asset.aliases || [])].filter(Boolean).join(' ').toLowerCase(),
  })).filter((asset) => asset.ticker);
  const ensureAssets = async () => {
    if (state.assets) return state.assets;
    const payload = await api('/api/assets');
    state.assets = Array.isArray(payload) ? payload : (payload?.assets || payload?.items || []);
    return state.assets;
  };
  const renderTickerOverlay = async (input) => {
    if (!input || input.dataset.hmQaTickerPatched !== '1') return;
    await ensureAssets();
    const container = input.closest('.ticker-input-container') || input.parentElement;
    if (!container) return;
    container.style.position = container.style.position || 'relative';
    let panel = container.querySelector('.hm-qa-asset-overlay');
    if (!panel) {
      panel = document.createElement('div');
      panel.className = 'hm-qa-asset-overlay suggestions-dropdown';
      panel.style.maxHeight = '340px';
      panel.style.overflowY = 'auto';
      panel.style.zIndex = '9999';
      panel.style.minWidth = '360px';
      container.appendChild(panel);
    }
    const q = String(input.value || '').trim().toLowerCase();
    const qNoSpace = q.replace(/\s+/g, '');
    const rows = normalizedAssets().filter((asset) => !q || asset.search.includes(q) || asset.ticker.toLowerCase().includes(qNoSpace)).slice(0, q ? 80 : 160);
    panel.innerHTML = '';
    const header = document.createElement('div');
    header.className = 'suggestion-state';
    header.textContent = `${rows.length}개 표시 / HedgeMate 전체 ${normalizedAssets().length}개 자산`;
    panel.appendChild(header);
    rows.forEach((asset) => {
      const row = document.createElement('div');
      row.className = 'suggestion-item';
      row.innerHTML = `<div class="suggestion-info"><span class="suggestion-ticker"></span><span class="suggestion-name"></span></div><span class="suggestion-exchange">HedgeMate</span>`;
      row.querySelector('.suggestion-ticker').textContent = asset.ticker;
      row.querySelector('.suggestion-name').textContent = asset.name;
      row.addEventListener('mousedown', (event) => {
        event.preventDefault();
        nativeSetValue(input, asset.ticker);
        const nameInput = input.closest('tr')?.querySelector('td:nth-child(2) input');
        if (nameInput) nativeSetValue(nameInput, asset.name);
        panel.remove();
      });
      panel.appendChild(row);
    });
  };
  const patchTickerInputs = () => {
    document.querySelectorAll('.ticker-input-container input').forEach((input) => {
      if (input.dataset.hmQaTickerPatched === '1') return;
      input.dataset.hmQaTickerPatched = '1';
      input.addEventListener('focus', () => renderTickerOverlay(input));
      input.addEventListener('input', () => renderTickerOverlay(input));
      input.addEventListener('blur', () => setTimeout(() => input.closest('.ticker-input-container')?.querySelector('.hm-qa-asset-overlay')?.remove(), 220));
    });
  };
  const replaceText = () => {
    const user = state.user || {};
    const email = user.email || user.username || user.user?.email || '';
    const displayName = user.displayName || user.name || email || 'HedgeMate 계정';
    const accountId = user.userId || user.id || user.user?.id || '';
    const primary = state.market?.primaryMarketState || {};
    const nowcastBasis = primary.asOfKst ? fmtKst(primary.asOfKst) : fmtDate(primary.dataAsOfDate);
    const titleBasis = nowcastBasis ? `현재 시장국면 진단 · 장중 nowcast 기준 ${nowcastBasis}` : '';

    textNodes().forEach((node) => {
      let value = node.nodeValue || '';
      if (value.includes('HedgeMate User')) value = value.replaceAll('HedgeMate User', displayName);
      if (value.includes('user@hedgemate.io')) value = value.replaceAll('user@hedgemate.io', email || '로그인된 계정');
      if (value.includes('HedgeMate Pro Plan')) value = accountId ? `계정 ID: ${accountId}` : '로그인 계정';
      if (titleBasis && value.includes('현재 시장국면 진단 · 정식 일간 기준')) value = titleBasis;
      if (value.includes('Gemini key 또는 외부 응답이 없어 검증된 fallback 근거를 표시 중입니다.')) {
        value = value.replace('Gemini key 또는 외부 응답이 없어 검증된 fallback 근거를 표시 중입니다.', '검증된 실시간 뉴스가 없어 Top5 뉴스를 표시하지 않습니다.');
      }
      if (value.includes('Hegdemate')) value = value.replaceAll('Hegdemate', 'HedgeMate');
      if (value.includes('hegdemate')) value = value.replaceAll('hegdemate', 'HedgeMate');
      if (value.includes('CCY')) value = value.replaceAll('CCY', '통화');
      if (value !== node.nodeValue) node.nodeValue = value;
    });

    hideElementWithText('현재 데이터 기준:');
    document.querySelectorAll('a[href^="fallback://"]').forEach((a) => {
      const span = document.createElement('span');
      span.className = a.className || 'news-source-chip muted';
      span.textContent = a.textContent || '출처 없음';
      a.replaceWith(span);
    });

    const loadingNodes = [];
    textNodes().forEach((node) => {
      if ((node.nodeValue || '').trim() === '실시간 시장데이터 확인 중') {
        const strip = nearestElement(node)?.closest?.('.status-strip, .analysis-status, .loading-card, div');
        if (strip) loadingNodes.push(strip);
      }
    });
    const unique = [...new Set(loadingNodes)];
    if (unique.length > 1) unique.slice(0, -1).forEach((el) => { el.style.display = 'none'; });
    patchTickerInputs();
  };
  const refreshState = async () => {
    const [user, market] = await Promise.all([api('/api/auth/me'), api('/api/scenario-dashboard'), ensureAssets()]);
    if (user) state.user = user.user || user;
    if (market) state.market = market;
    replaceText();
  };
  const observer = new MutationObserver(() => replaceText());
  if (document.body) observer.observe(document.body, { childList: true, subtree: true, characterData: true });
  window.addEventListener('load', refreshState);
  refreshState();
  const timer = setInterval(() => {
    replaceText();
    if (Date.now() - state.startedAt > 120000) clearInterval(timer);
  }, 800);
})();
