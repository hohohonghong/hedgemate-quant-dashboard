(() => {
  window.__HEDGEMATE_PUBLIC_QA_HOTPATCH__ = true;

  const api = (path) => fetch(path, { credentials: 'include' })
    .then((r) => (r.ok ? r.json() : null))
    .catch(() => null);
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
      timeZone: 'Asia/Seoul',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    }).formatToParts(d).reduce((acc, p) => {
      acc[p.type] = p.value;
      return acc;
    }, {});
    return `${parts.year}.${parts.month}.${parts.day} ${parts.hour}:${parts.minute}`;
  };
  const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (ch) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  }[ch]));
  const textNodes = (root = document.body) => {
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
    group: asset.assetClass || asset.currency || asset.exchange || '',
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

  const ensureHotpatchStyles = () => {
    if (document.getElementById('hm-qa-hotpatch-style')) return;
    const style = document.createElement('style');
    style.id = 'hm-qa-hotpatch-style';
    style.textContent = `
      .hm-qa-market-nowcast{margin:24px 0;padding:22px;border:1px solid rgba(16,24,40,.12);border-radius:8px;background:#fff;box-shadow:0 8px 22px rgba(16,24,40,.06)}
      .hm-qa-market-head{display:flex;gap:16px;align-items:flex-start;justify-content:space-between;flex-wrap:wrap}
      .hm-qa-market-kicker{font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#475467;margin-bottom:6px}
      .hm-qa-market-title{margin:0;font-size:24px;line-height:1.25;color:#101828}
      .hm-qa-market-badge{display:inline-flex;align-items:center;min-height:30px;padding:0 10px;border-radius:999px;background:#fff3cd;color:#7a4d00;font-weight:700}
      .hm-qa-market-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:18px 0}
      .hm-qa-market-stat{padding:14px;border:1px solid rgba(16,24,40,.1);border-radius:8px;background:#f8fafc}
      .hm-qa-market-stat span{display:block;font-size:12px;color:#667085;margin-bottom:4px}
      .hm-qa-market-stat strong{font-size:20px;color:#101828}
      .hm-qa-market-copy{margin:10px 0;color:#344054;line-height:1.6}
      .hm-qa-market-note{margin-top:14px;color:#667085;font-size:13px}
      .hm-qa-news-empty{margin-top:14px;padding:12px 14px;border-radius:8px;background:#f9fafb;color:#475467}
      .hm-qa-news-list{margin:14px 0 0;padding-left:18px}
      .hm-qa-news-list a{color:#155eef}
      @media (max-width:760px){.hm-qa-market-grid{grid-template-columns:1fr}.hm-qa-market-title{font-size:20px}}
    `;
    document.head.appendChild(style);
  };

  const renderMarketStateFallback = () => {
    if (!location.pathname.includes('/market-state')) return;
    const market = state.market;
    const primary = market?.primaryMarketState;
    const main = document.querySelector('main');
    if (!market || !primary || !main) return;

    ensureHotpatchStyles();
    hideElementWithText('시장국면 진단 결과를 불러오는 중입니다.', main);
    hideElementWithText('scenario market-state pipeline', main);
    hideElementWithText('reading raw_market_daily', main);
    hideElementWithText('정식 일간 기준', main);
    hideElementWithText('현재 데이터 기준:', main);

    const basis = primary.asOfKst ? fmtKst(primary.asOfKst) : fmtDate(primary.dataAsOfDate || market.asOfDate);
    const score = Number.isFinite(Number(primary.score)) ? Number(primary.score).toFixed(1) : '-';
    const confidence = Number.isFinite(Number(primary.confidence)) ? `${Number(primary.confidence).toFixed(1)}%` : '-';
    const stateLabel = primary.state || primary.code || '-';
    const title = primary.nameKo || primary.name || primary.code || '현재 시장국면';
    const interpretation = primary.interpretationKo || market.dataFreshnessNote || '장중 nowcast 기준으로 현재 시장 상태를 요약합니다.';
    const news = Array.isArray(market.intradayNewsTop5) ? market.intradayNewsTop5 : [];
    const signature = JSON.stringify([basis, score, confidence, stateLabel, title, news.length]);

    let panel = main.querySelector('.hm-qa-market-nowcast');
    if (!panel) {
      panel = document.createElement('section');
      panel.className = 'hm-qa-market-nowcast';
      const h1 = Array.from(main.querySelectorAll('h1')).find((node) => node.textContent?.includes('현재시장국면'));
      const anchor = h1?.nextElementSibling || h1 || main.firstElementChild;
      if (anchor?.parentElement === main) anchor.insertAdjacentElement('afterend', panel);
      else main.prepend(panel);
    }
    if (panel.dataset.signature === signature) return;
    panel.dataset.signature = signature;

    const newsHtml = news.length
      ? `<ul class="hm-qa-news-list">${news.map((item) => {
        const label = escapeHtml(item.title || item.headline || item.source || '뉴스');
        const href = item.url || item.link;
        if (href && /^https?:\/\//.test(href)) return `<li><a href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer">${label}</a></li>`;
        return `<li>${label}</li>`;
      }).join('')}</ul>`
      : '<div class="hm-qa-news-empty">검증된 실시간 뉴스가 없어 Top5 뉴스를 표시하지 않습니다.</div>';

    panel.innerHTML = `
      <div class="hm-qa-market-head">
        <div>
          <div class="hm-qa-market-kicker">MARKET NOWCAST</div>
          <h2 class="hm-qa-market-title">현재 시장국면 진단 · 장중 nowcast 기준 ${escapeHtml(basis)}</h2>
        </div>
        <span class="hm-qa-market-badge">${escapeHtml(stateLabel)}</span>
      </div>
      <div class="hm-qa-market-grid">
        <div class="hm-qa-market-stat"><span>국면</span><strong>${escapeHtml(title)}</strong></div>
        <div class="hm-qa-market-stat"><span>점수</span><strong>${escapeHtml(score)}</strong></div>
        <div class="hm-qa-market-stat"><span>신뢰도</span><strong>${escapeHtml(confidence)}</strong></div>
      </div>
      <p class="hm-qa-market-copy">${escapeHtml(interpretation)}</p>
      ${newsHtml}
      <p class="hm-qa-market-note">실시간 화면은 장중 nowcast를 우선 표시하며, 정식 일간 데이터는 내부 검증 레이어의 보조 입력으로만 사용합니다.</p>
    `;
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
    if (unique.length > 1) unique.slice(0, -1).forEach((el) => {
      el.style.display = 'none';
    });

    patchTickerInputs();
    renderMarketStateFallback();
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