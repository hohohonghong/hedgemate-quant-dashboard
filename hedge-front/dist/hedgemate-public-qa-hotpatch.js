(() => {
  window.__HEDGEMATE_PUBLIC_QA_HOTPATCH__ = true;

  const nativeFetch = window.fetch.bind(window);
  const state = { user: null, market: null, assets: null, startedAt: Date.now() };

  const isScenarioDashboardUrl = (input) => {
    const url = typeof input === 'string' ? input : input?.url || '';
    return /\/api\/scenario-dashboard(?:\?|$)/.test(url);
  };

  const normalizeMarketDashboard = (payload) => {
    if (!payload || typeof payload !== 'object') return payload;
    const primary = payload.primaryMarketState || {};
    const freshness = payload.marketStateFreshness || {};
    const isFreshNowcast = primary.source === 'intraday_nowcast' && (primary.isFresh !== false) && primary.dataAsOfDate;
    if (!isFreshNowcast) return payload;

    const patched = {
      ...payload,
      dataAsOfDate: primary.dataAsOfDate,
      asOfDate: primary.dataAsOfDate,
      marketStateFreshness: {
        ...freshness,
        displayDate: primary.dataAsOfDate,
        primarySource: 'intraday_nowcast',
        primaryDataAsOfDate: primary.dataAsOfDate,
        primaryAsOfKst: primary.asOfKst || freshness.intradayNowcastAsOfKst,
        intradayFresh: true,
      },
    };
    const primaryRow = {
      scenario_code: primary.code,
      scenario_name: primary.code,
      scenario_name_ko: primary.nameKo,
      lens: primary.lens,
      final_score: primary.score,
      final_confidence: primary.confidence,
      final_display_state: primary.state,
      display_state: primary.state,
      status: primary.state,
      dataAsOfDate: primary.dataAsOfDate,
      market_interpretation_ko: primary.interpretationKo,
      source: 'intraday_nowcast',
    };
    if (primary.code || primary.nameKo) {
      const rest = (payload.topActiveScenarios || []).filter((row) => row.scenario_code !== primary.code);
      patched.topActiveScenarios = [primaryRow, ...rest].slice(0, Math.max(3, rest.length + 1));
    }
    return patched;
  };

  window.fetch = async (...args) => {
    const response = await nativeFetch(...args);
    if (!isScenarioDashboardUrl(args[0])) return response;
    try {
      const originalJson = response.json.bind(response);
      response.json = async () => normalizeMarketDashboard(await originalJson());
    } catch (_) {
      return response;
    }
    return response;
  };

  const api = (path) => nativeFetch(path, { credentials: 'include' })
    .then((r) => (r.ok ? r.json() : null))
    .then((data) => (path.includes('/scenario-dashboard') ? normalizeMarketDashboard(data) : data))
    .catch(() => null);

  const fmtDate = (value) => {
    if (!value) return '';
    const m = String(value).match(/^(\d{4})-(\d{2})-(\d{2})/);
    return m ? `${m[1]}.${m[2]}.${m[3]}` : String(value).replaceAll('-', '.');
  };

  const fmtKst = (value) => {
    if (!value) return '';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return fmtDate(value);
    const parts = new Intl.DateTimeFormat('ko-KR', {
      timeZone: 'Asia/Seoul',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    }).formatToParts(date).reduce((acc, part) => {
      acc[part.type] = part.value;
      return acc;
    }, {});
    return `${parts.year}.${parts.month}.${parts.day} ${parts.hour}:${parts.minute}`;
  };

  const textNodes = (root = document.body) => {
    if (!root) return [];
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    return nodes;
  };

  const nearestElement = (node) => node && (node.nodeType === 1 ? node : node.parentElement);
  const hideElementWithText = (text, root = document.body) => {
    textNodes(root).forEach((node) => {
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
    search: [
      asset.ticker,
      asset.symbol,
      asset.label,
      asset.displayLabel,
      asset.name,
      asset.popularName,
      asset.assetClass,
      asset.searchText,
      ...(asset.aliases || []),
    ].filter(Boolean).join(' ').toLowerCase(),
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
    const assets = normalizedAssets();
    const rows = assets
      .filter((asset) => !q || asset.search.includes(q) || asset.ticker.toLowerCase().includes(qNoSpace))
      .slice(0, q ? 80 : 160);
    panel.innerHTML = '';
    const header = document.createElement('div');
    header.className = 'suggestion-state';
    header.textContent = `${rows.length}개 표시 / HedgeMate 전체 ${assets.length}개 자산`;
    panel.appendChild(header);
    rows.forEach((asset) => {
      const row = document.createElement('div');
      row.className = 'suggestion-item';
      row.innerHTML = '<div class="suggestion-info"><span class="suggestion-ticker"></span><span class="suggestion-name"></span></div><span class="suggestion-exchange">HedgeMate</span>';
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
      input.addEventListener('blur', () => setTimeout(() => {
        input.closest('.ticker-input-container')?.querySelector('.hm-qa-asset-overlay')?.remove();
      }, 220));
    });
  };

  const patchNewsLinks = () => {
    document.querySelectorAll('a[href^="fallback://"]').forEach((link) => {
      const span = document.createElement('span');
      span.className = link.className || 'news-source-chip muted';
      span.textContent = link.textContent || '출처 없음';
      link.replaceWith(span);
    });
  };

  const removeBadMarketFallbacks = () => {
    document.querySelectorAll('.hm-qa-market-nowcast, .hm-qa-market-inline').forEach((el) => el.remove());
    document.querySelectorAll('.market-basis-chip').forEach((el) => {
      el.style.display = 'none';
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
      if (titleBasis && value.trim() === '정식 일간 기준') value = '장중 nowcast 기준';
      if (titleBasis && value.trim() === '정식 일간') value = '장중 nowcast';
      if (value.includes('정식 일간 국면 TOP 3 · 일간 데이터')) value = value.replace(/정식 일간 국면 TOP 3 · 일간 데이터 [0-9.:-]+/g, '정식 일간 국면 TOP 3');
      if (value.includes('현재 데이터 기준:')) value = '';
      if (value.includes('DAILY FINAL SCORE')) value = value.replaceAll('DAILY FINAL SCORE', 'NOWCAST SCORE');
      if (value.includes('Gemini key 또는 외부 응답이 없어 검증된 fallback 근거를 표시 중입니다.')) {
        value = value.replace(
          'Gemini key 또는 외부 응답이 없어 검증된 fallback 근거를 표시 중입니다.',
          '검증된 실시간 뉴스가 없어 Top5 뉴스를 표시하지 않습니다.',
        );
      }
      if (value.includes('Hegdemate')) value = value.replaceAll('Hegdemate', 'HedgeMate');
      if (value.includes('hegdemate')) value = value.replaceAll('hegdemate', 'HedgeMate');
      if (value.includes('CCY')) value = value.replaceAll('CCY', '통화');
      if (value !== node.nodeValue) node.nodeValue = value;
    });

    hideElementWithText('현재 데이터 기준:');
    patchNewsLinks();
    patchTickerInputs();
    removeBadMarketFallbacks();

    const loadingNodes = [];
    textNodes().forEach((node) => {
      if ((node.nodeValue || '').trim() === '실시간 시장데이터 확인 중') {
        const strip = nearestElement(node)?.closest?.('.status-strip, .analysis-status, .loading-card, div');
        if (strip) loadingNodes.push(strip);
      }
    });
    const unique = [...new Set(loadingNodes)];
    if (unique.length > 1) unique.slice(0, -1).forEach((el) => {
      el.style.display = 'none';
    });
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
  window.addEventListener('popstate', () => setTimeout(refreshState, 250));
  refreshState();
  const timer = setInterval(() => {
    replaceText();
    if (Date.now() - state.startedAt > 120000) clearInterval(timer);
  }, 800);
})();