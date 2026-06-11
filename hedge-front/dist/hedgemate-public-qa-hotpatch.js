(() => {
  const api = (path) => fetch(path, { credentials: 'include' }).then((r) => (r.ok ? r.json() : null)).catch(() => null);
  const state = { user: null, market: null, startedAt: Date.now() };
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
  };
  const refreshState = async () => {
    const [user, market] = await Promise.all([api('/api/auth/me'), api('/api/scenario-dashboard')]);
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
