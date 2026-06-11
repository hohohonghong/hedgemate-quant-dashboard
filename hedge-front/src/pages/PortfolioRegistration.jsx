import React, { useEffect, useState, useRef, useCallback } from 'react';
import { UploadCloud, Trash2, Shield, FileText, Image as ImageIcon, List, Plus, CheckCircle, X, ArrowRight, Briefcase, Loader2, AlertTriangle } from 'lucide-react';
import { Button } from '../components/Button';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { usePortfolios } from '../context/PortfolioContext';
import { getTickerQuote, searchTickers } from '../services/yahooFinance';
import { extractPortfolioFromImage, getAssets, lookupAssetPrice } from '../services/hedgemateApi';
import { debounce, ASSET_DATABASE, isKoreanTicker, normalizeTickerSymbol, searchAssetDatabase } from '../utils/helpers';
import { getConcentrationLabel, getPortfolioConcentrationSummary } from '../utils/portfolioConcentration';
import './PortfolioRegistration.css';

const TICKER_DB = ASSET_DATABASE;
let backendAssetOptionsPromise = null;
const BACKEND_EMPTY_LIST_LIMIT = 160;
const BACKEND_SEARCH_LIMIT = 80;
const LOCAL_FALLBACK_LIMIT = 12;
const OCR_DIRECT_UPLOAD_LIMIT_BYTES = 3.5 * 1024 * 1024;
const OCR_MAX_IMAGE_DIMENSION = 2200;

const readFileAsDataUrl = (file) => new Promise((resolve, reject) => {
  const reader = new FileReader();
  reader.onload = () => resolve(String(reader.result || ''));
  reader.onerror = () => reject(reader.error || new Error('이미지를 읽지 못했습니다.'));
  reader.readAsDataURL(file);
});

const loadImageFromFile = (file) => new Promise((resolve, reject) => {
  const url = URL.createObjectURL(file);
  const image = new Image();
  image.onload = () => {
    URL.revokeObjectURL(url);
    resolve(image);
  };
  image.onerror = () => {
    URL.revokeObjectURL(url);
    reject(new Error('이미지를 열 수 없습니다.'));
  };
  image.src = url;
});

const canvasToBlob = (canvas, type, quality) => new Promise((resolve) => {
  canvas.toBlob((blob) => resolve(blob), type, quality);
});

const prepareImageForOcr = async (file) => {
  const supportedType = /image\/(png|jpeg|jpg|webp|gif)/i.test(file.type || '');
  if (supportedType && file.size <= OCR_DIRECT_UPLOAD_LIMIT_BYTES) {
    return {
      dataUrl: await readFileAsDataUrl(file),
      mimeType: file.type === 'image/jpg' ? 'image/jpeg' : file.type,
    };
  }

  const image = await loadImageFromFile(file);
  const scale = Math.min(
    1,
    OCR_MAX_IMAGE_DIMENSION / Math.max(image.naturalWidth || image.width, image.naturalHeight || image.height)
  );
  const width = Math.max(1, Math.round((image.naturalWidth || image.width) * scale));
  const height = Math.max(1, Math.round((image.naturalHeight || image.height) * scale));
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext('2d');
  if (!context) throw new Error('이미지 변환을 위한 캔버스를 사용할 수 없습니다.');
  context.fillStyle = '#ffffff';
  context.fillRect(0, 0, width, height);
  context.drawImage(image, 0, 0, width, height);
  const blob = await canvasToBlob(canvas, 'image/jpeg', 0.92);
  if (!blob) throw new Error('이미지 변환에 실패했습니다.');
  return {
    dataUrl: await readFileAsDataUrl(blob),
    mimeType: 'image/jpeg',
  };
};

const searchBackendAssetOptions = async (query, limit = BACKEND_SEARCH_LIMIT) => {
  if (!backendAssetOptionsPromise) {
    backendAssetOptionsPromise = getAssets()
      .then((payload) => payload.assets || [])
      .catch((error) => {
        backendAssetOptionsPromise = null;
        throw error;
      });
  }
  const raw = String(query || '').trim().toLowerCase();
  const normalized = normalizeTickerSymbol(query || '').toLowerCase();
  const assets = await backendAssetOptionsPromise;
  return assets
    .filter((asset) => {
      if (!raw) return true;
      const searchText = [
        asset.ticker,
        asset.label,
        asset.displayLabel,
        asset.popularName,
        asset.assetClass,
        asset.searchText,
        ...(asset.aliases || []),
      ].filter(Boolean).join(' ').toLowerCase();
      return searchText.includes(raw) || searchText.includes(normalized);
    })
    .slice(0, limit)
    .map((asset) => ({
      ticker: asset.ticker,
      name: asset.label || asset.displayLabel || asset.ticker,
      exchange: asset.assetClass || '',
      isLocal: true,
      source: 'hedgemate',
    }));
};

export const PortfolioRegistration = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const editPortfolioId = searchParams.get('edit');
  const { portfolios, addPortfolio, updatePortfolio, usdKrwRate } = usePortfolios();
  const editingPortfolio = portfolios.find((p) => p.id === editPortfolioId);
  const fileInputRef = useRef(null);
  const hydratedEditId = useRef(null);

  const [portfolioName, setPortfolioName] = useState('');
  const [purpose, setPurpose] = useState('장기 가치 투자');
  const [rows, setRows] = useState([
    { id: 1, ticker: '', name: '', qty: 0, cost: 0, currency: 'USD' },
  ]);
  const [uploadedFile, setUploadedFile] = useState(null);
  const [showSuccess, setShowSuccess] = useState(false);
  const [createdPortfolio, setCreatedPortfolio] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [isOcrProcessing, setIsOcrProcessing] = useState(false);
  const [ocrProgress, setOcrProgress] = useState(0);
  const [ocrError, setOcrError] = useState('');
  const [ocrWarnings, setOcrWarnings] = useState([]);
  const nextId = useRef(2);
  const [activeRowId, setActiveRowId] = useState(null);
  const [suggestions, setSuggestions] = useState([]);
  const [searchState, setSearchState] = useState({
    rowId: null,
    query: '',
    loading: false,
    error: '',
    hasSearched: false,
  });
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState('');

  const fetchPreferredPrice = async (ticker) => {
    try {
      const price = await lookupAssetPrice({ ticker }, { useLivePrices: true });
      return {
        name: price.displayName,
        price: price.latestPrice,
        currency: price.currency,
      };
    } catch (error) {
      console.warn('HedgeMate price lookup failed, falling back to Yahoo:', error);
      return getTickerQuote(ticker);
    }
  };

  useEffect(() => {
    if (!editPortfolioId || !editingPortfolio || hydratedEditId.current === editPortfolioId) return;
    hydratedEditId.current = editPortfolioId;
    setPortfolioName(editingPortfolio.name || '');
    setPurpose(editingPortfolio.purpose || '장기 가치 투자');
    const editRows = (editingPortfolio.assets || []).map((asset, index) => ({
      id: index + 1,
      ticker: normalizeTickerSymbol(asset.ticker),
      name: asset.name || '',
      qty: asset.qty || asset.quantity || 0,
      cost: asset.cost || asset.price || 0,
      currency: asset.currency || (isKoreanTicker(asset.ticker) ? 'KRW' : 'USD'),
    }));
    setRows(editRows.length > 0 ? editRows : [{ id: 1, ticker: '', name: '', qty: 0, cost: 0, currency: 'USD' }]);
    nextId.current = Math.max(2, editRows.length + 1);
    setUploadedFile(null);
    setShowSuccess(false);
    setCreatedPortfolio(null);
  }, [editPortfolioId, editingPortfolio]);

  const addRow = () => {
    setRows(prev => [...prev, { id: nextId.current++, ticker: '', name: '', qty: 0, cost: 0, currency: 'USD' }]);
  };

  const removeRow = (id) => {
    if (rows.length <= 1) return; // keep at least one row
    setRows(prev => prev.filter(r => r.id !== id));
  };

  // Debounced ticker lookup
  const debouncedLookup = useCallback(
    debounce(async (id, ticker) => {
      const upper = normalizeTickerSymbol(ticker);
      const local = TICKER_DB[upper] || TICKER_DB[ticker.toUpperCase()];
      if (local) {
        setRows(prev => prev.map(r => r.id === id ? { 
          ...r, 
          ticker: upper,
          name: local.name, 
          cost: r.cost,
          currency: local.currency || 'USD'
        } : r));
        const quote = await fetchPreferredPrice(upper);
        if (quote) {
          setRows(prev => prev.map(r => r.id === id ? {
            ...r,
            ticker: upper,
            name: quote.name || local.name,
            cost: quote.price || r.cost,
            currency: quote.currency || local.currency || 'USD'
          } : r));
        }
      } else {
        const quote = await fetchPreferredPrice(upper);
        if (quote) {
          setRows(prev => prev.map(r => {
            if (r.id === id && r.ticker.toUpperCase() === upper) {
              return { ...r, name: quote.name, cost: r.cost || quote.price, currency: quote.currency || 'USD' };
            }
            return r;
          }));
        }
      }
    }, 500),
    []
  );

  // Debounced search for ticker suggestions
  const debouncedSearch = useCallback(
    debounce(async (id, query) => {
      const trimmedQuery = String(query || '').trim();
      let apiError = '';
      if (!query || query.trim().length < 1) {
        let popular = [];
        try {
          popular = await searchBackendAssetOptions('', BACKEND_EMPTY_LIST_LIMIT);
        } catch {
          apiError = 'HedgeMate 자산 목록을 불러오지 못했습니다.';
          popular = searchAssetDatabase('', LOCAL_FALLBACK_LIMIT);
        }
        setSuggestions(popular);
        setSearchState({
          rowId: id,
          query: '',
          loading: false,
          error: apiError,
          hasSearched: true,
        });
        return;
      }

      const localMatches = searchAssetDatabase(query, LOCAL_FALLBACK_LIMIT);
      let backendMatches = [];
      try {
        backendMatches = await searchBackendAssetOptions(query, BACKEND_SEARCH_LIMIT);
      } catch {
        apiError = 'HedgeMate 자산 목록을 불러오지 못했습니다.';
      }
        
      // 2. Search via Yahoo Finance Search API
      let apiMatches = [];
      const shouldUseExternalSearch = query.trim().length >= 2 && /[A-Za-z0-9]/.test(query);
      if (shouldUseExternalSearch) {
        try {
          const apiResults = await searchTickers(query, { throwOnError: true });
          apiMatches = apiResults.map(res => ({
            ticker: res.ticker,
            name: res.name,
            exchange: res.exchange,
            isLocal: false
          }));
        } catch {
          apiError = apiError || '외부 검색 API 응답을 불러오지 못했습니다.';
        }
      }
      
      // Combine results, prioritizing the deployed HedgeMate universe and removing duplicates by ticker
      const combined = [];
      const seen = new Set();

      backendMatches.forEach(match => {
        if (!seen.has(match.ticker)) {
          combined.push(match);
          seen.add(match.ticker);
        }
      });

      localMatches.forEach(match => {
        if (!seen.has(match.ticker)) {
          combined.push(match);
          seen.add(match.ticker);
        }
      });
      
      apiMatches.forEach(match => {
        if (!seen.has(match.ticker)) {
          combined.push(match);
          seen.add(match.ticker);
        }
      });
      
      setSuggestions(combined);
      setSearchState({
        rowId: id,
        query: trimmedQuery,
        loading: false,
        error: apiError,
        hasSearched: true,
      });
    }, 300),
    []
  );

  const handleFocus = (id, query) => {
    setActiveRowId(id);
    setSearchState({
      rowId: id,
      query: String(query || '').trim(),
      loading: true,
      error: '',
      hasSearched: false,
    });
    debouncedSearch(id, query);
  };

  const selectSuggestion = async (id, suggestion) => {
    const ticker = normalizeTickerSymbol(suggestion.ticker);
    let price = 0;
    let currency = 'USD';
    const local = TICKER_DB[ticker] || TICKER_DB[suggestion.ticker];
    if (suggestion.isLocal && local) {
      currency = local.currency || 'USD';
    }
    const quote = await fetchPreferredPrice(ticker);
    if (quote) {
      price = quote.price;
      currency = quote.currency || currency || 'USD';
    }

    setRows(prev => prev.map(r => r.id === id ? {
      ...r,
      ticker,
      name: quote?.name || suggestion.name,
      cost: price || r.cost,
      currency: currency
    } : r));
    
    setSuggestions([]);
    setActiveRowId(null);
    setSearchState((prev) => ({
      ...prev,
      rowId: null,
      loading: false,
    }));
  };

  const updateRow = (id, field, value) => {
    setRows(prev => prev.map(r => {
      if (r.id !== id) return r;
      return { ...r, [field]: value };
    }));

    if (field === 'ticker') {
      setActiveRowId(id);
      setSearchState({
        rowId: id,
        query: String(value || '').trim(),
        loading: true,
        error: '',
        hasSearched: false,
      });
      debouncedSearch(id, value);
      if (value.length >= 2) {
        debouncedLookup(id, value);
      }
    }
  };

  const getValInKRW = (r) => {
    const isUSD = r.currency === 'USD' || (!r.currency && !isKoreanTicker(r.ticker));
    const rate = isUSD ? usdKrwRate : 1;
    return r.qty * r.cost * rate;
  };

  const totalValue = rows.reduce((sum, r) => sum + getValInKRW(r), 0);
  const rowsWithWeight = rows
    .filter((r) => r.ticker.trim())
    .map((r) => {
      const valueKrw = getValInKRW(r);
      const weightPct = totalValue > 0 ? (valueKrw / totalValue) * 100 : 0;
      return {
        ticker: normalizeTickerSymbol(r.ticker),
        name: r.name,
        weightPct,
      };
    });
  const concentrationSummary = getPortfolioConcentrationSummary(rowsWithWeight);
  const concentrationLabel = getConcentrationLabel(concentrationSummary);

  const processOcr = async (file) => {
    setIsOcrProcessing(true);
    setOcrProgress(0);
    setOcrError('');
    setOcrWarnings([]);
    try {
      setOcrProgress(0.08);
      const imagePayload = await prepareImageForOcr(file);
      setOcrProgress(0.32);
      const result = await extractPortfolioFromImage({
        imageBase64: imagePayload.dataUrl,
        fileName: file.name,
        mimeType: imagePayload.mimeType,
      });
      setOcrProgress(0.86);
      const parsedRows = (result.rows || [])
        .filter((row) => row.ticker || row.name)
        .map((row) => {
          const upperTicker = normalizeTickerSymbol(row.ticker || row.name);
          const currency = row.currency || (TICKER_DB[upperTicker]?.currency) || (isKoreanTicker(upperTicker) ? 'KRW' : 'USD');
          return {
            id: nextId.current++,
            ticker: upperTicker,
            name: row.name || TICKER_DB[upperTicker]?.name || '',
            qty: Number(row.quantity ?? row.qty) || 0,
            cost: Number(row.price ?? row.cost) || 0,
            currency,
          };
        });

      if (parsedRows.length > 0) {
        setRows(prev => {
          const isDefault = prev.length === 1 && prev[0].ticker === '';
          return isDefault ? parsedRows : [...prev, ...parsedRows];
        });
        const rowWarnings = (result.rows || [])
          .flatMap((row) => row.warnings || [])
          .filter(Boolean);
        setOcrWarnings([...(result.warnings || []), ...rowWarnings].slice(0, 6));
      } else {
        setOcrWarnings(['이미지에서 자동으로 등록할 수 있는 보유 종목 행을 찾지 못했습니다.']);
      }
      setOcrProgress(1);
    } catch(err) {
      console.error(err);
      const message = err.message || '이미지 분석 중 오류가 발생했습니다.';
      setOcrError(message);
      alert(message);
    } finally {
      setIsOcrProcessing(false);
    }
  };

  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      if (!file.type.startsWith('image/')) {
        alert('이미지 파일만 업로드 가능합니다.');
        return;
      }
      setUploadedFile(file);
      processOcr(file);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file && file.type.startsWith('image/')) {
      setUploadedFile(file);
      processOcr(file);
    } else if (file) {
      alert('이미지 파일만 업로드 가능합니다.');
    }
  };

  const handleSubmit = async () => {
    if (!portfolioName.trim()) {
      alert('포트폴리오 이름을 입력해주세요.');
      return;
    }
    const validRows = rows.filter(r => r.ticker.trim());
    if (validRows.length === 0) {
      alert('최소 1개 이상의 종목을 입력해주세요.');
      return;
    }

    const assets = validRows.map(r => {
      let currency = r.currency;
      if (!currency) {
        const upperTicker = normalizeTickerSymbol(r.ticker);
        if (TICKER_DB[upperTicker]) {
          currency = TICKER_DB[upperTicker].currency;
        } else {
          currency = isKoreanTicker(upperTicker) ? 'KRW' : 'USD';
        }
      }
      return {
        ticker: normalizeTickerSymbol(r.ticker),
        name: r.name,
        qty: r.qty,
        cost: r.cost,
        currency,
      };
    });
    const assetsWithWeight = assets.map((asset) => {
      const sourceRow = validRows.find((row) => normalizeTickerSymbol(row.ticker) === asset.ticker);
      const valueKrw = sourceRow ? getValInKRW(sourceRow) : 0;
      const weightPct = totalValue > 0 ? (valueKrw / totalValue) * 100 : 0;
      return {
        ...asset,
        weight: Math.round(weightPct),
        weightPct: Number(weightPct.toFixed(4)),
      };
    });

    const payload = {
      name: portfolioName,
      purpose,
      assets,
    };

    setIsSaving(true);
    setSaveError('');
    try {
      let savedPortfolio;
      if (editPortfolioId && editingPortfolio) {
        savedPortfolio = await updatePortfolio(editPortfolioId, {
          ...payload,
          totalValue,
          assets: assetsWithWeight,
          status: 'updated',
        });
      } else {
        savedPortfolio = await addPortfolio({
          ...payload,
          totalValue,
          assets: assetsWithWeight,
        });
      }

      setCreatedPortfolio(savedPortfolio);
      setShowSuccess(true);
    } catch (error) {
      setSaveError(error.message || 'Portfolio save failed.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    if (editPortfolioId) {
      navigate('/portfolios');
      return;
    }
    setPortfolioName('');
    setPurpose('장기 가치 투자');
    setRows([{ id: nextId.current++, ticker: '', name: '', qty: 0, cost: 0, currency: 'USD' }]);
    setUploadedFile(null);
    setOcrError('');
    setOcrWarnings([]);
  };

  if (showSuccess && createdPortfolio) {
    return (
      <div className="portfolio-reg" style={{display:'flex',alignItems:'center',justifyContent:'center',minHeight:'60vh'}}>
        <div style={{textAlign:'center', maxWidth: '480px'}}>
          <div className="success-icon-wrapper">
            <CheckCircle size={56} className="text-accent-light" />
          </div>
          <h1 className="mt-4">포트폴리오가 등록되었습니다!</h1>
          <p className="text-secondary mt-2" style={{lineHeight: 1.6}}>
            포트폴리오가 <strong style={{color: 'var(--accent-light)'}}>{editPortfolioId ? '수정' : '내 포트폴리오에 저장'}</strong>되었습니다.<br />
            최신 포트폴리오를 확인하고 분석을 시작하세요.
          </p>
          <div className="success-summary mt-6">
            <div className="card-box" style={{display:'inline-block',padding:'1.5rem 3rem',textAlign:'left'}}>
              <div className="text-sm text-secondary">포트폴리오</div>
              <div className="font-semibold mt-1">{createdPortfolio.name}</div>
              <div className="text-sm text-secondary mt-4">종목 수</div>
              <div className="font-semibold mt-1">{createdPortfolio.assets.length}개</div>
              <div className="text-sm text-secondary mt-4">총 투자금액</div>
              <div className="font-semibold mt-1 text-accent-light">₩{createdPortfolio.totalValue.toLocaleString()}</div>
              <div className="text-sm text-secondary mt-4">상태</div>
              <div className="font-semibold mt-1">
              <span className="status-badge-new">{createdPortfolio.assets?.some((asset) => Number(asset.weightPct ?? asset.weight) > 50) ? 'CONCENTRATED — 비중 확인' : (editPortfolioId ? 'UPDATED — 재분석 권장' : 'NEW — 분석 대기')}</span>
              </div>
            </div>
          </div>
          <div className="success-actions mt-6 flex gap-3 justify-center">
            <Button variant="secondary" onClick={() => {
              if (editPortfolioId) {
                navigate('/portfolios');
                return;
              }
              setShowSuccess(false);
              setCreatedPortfolio(null);
              handleCancel();
            }}>
              <Plus size={16} /> {editPortfolioId ? '목록으로 돌아가기' : '추가 등록'}
            </Button>
            <Button variant="primary" onClick={() => navigate('/portfolios')}>
              <Briefcase size={16} /> 내 포트폴리오 보기 <ArrowRight size={14} />
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="portfolio-reg">
      {/* Flow Breadcrumb */}
      <div className="flow-breadcrumb mb-6">
        <span className="flow-crumb active">
          <span className="crumb-step">1</span> 포트폴리오 등록
        </span>
        <span className="flow-arrow">→</span>
        <span className="flow-crumb">
          <span className="crumb-step">2</span> 내 포트폴리오
        </span>
        <span className="flow-arrow">→</span>
        <span className="flow-crumb">
          <span className="crumb-step">3</span> 분석 리포트
        </span>
      </div>

      <h1 className="mb-2">{editPortfolioId ? '포트폴리오 수정' : '새 포트폴리오 생성'}</h1>
      <p className="text-secondary text-sm mb-8" style={{maxWidth: '600px', lineHeight: 1.6}}>
        {editPortfolioId ? '보유 종목, 수량, 단가를 수정한 뒤 다시 분석해 최신 취약성 결과를 확인하세요.' : 'HedgeMate의 정밀한 데이터 분석을 시작하세요. 자산을 업로드하거나 수동으로 입력하여 맞춤형 인사이트를 확보하십시오.'}
      </p>

      <div className="top-grid mb-6">
        {/* Card 1: Basic Info */}
        <div className="card-box">
          <div className="card-header">
            <span className="icon-wrapper"><Shield size={16}/></span>
            <span className="font-semibold">기본 정보</span>
          </div>
          <div className="form-group mt-6">
            <label>포트폴리오 이름</label>
            <input 
              type="text" 
              placeholder="예: 2024 하이테크 성장 주" 
              value={portfolioName}
              onChange={(e) => setPortfolioName(e.target.value)}
            />
          </div>
          <div className="form-group mt-6">
            <label>운용 목적</label>
            <select value={purpose} onChange={(e) => setPurpose(e.target.value)}>
              <option>장기 가치 투자</option>
              <option>단기 스윙</option>
              <option>리스크 헷지</option>
              <option>배당 수익</option>
              <option>성장주 집중</option>
            </select>
          </div>
          {portfolioName && (
            <div className="portfolio-preview mt-6">
              <div className="text-xs text-secondary">미리보기</div>
              <div className="text-sm font-semibold mt-1">{portfolioName}</div>
              <div className="text-xs text-secondary mt-1">{purpose} · {rows.filter(r=>r.ticker).length}종목</div>
            </div>
          )}
        </div>

        {/* Card 2: File Upload */}
        <div className="card-box">
          <div className="card-header justify-between">
            <div className="flex items-center gap-2">
              <span className="icon-wrapper"><ImageIcon size={16}/></span>
            <span className="font-semibold">이미지 등록 (OCR)</span>
            </div>
            <span className="badge">JPG / PNG SUPPORTED</span>
          </div>

          {uploadedFile ? (
            <div className="uploaded-file mt-6">
              <div className="flex items-center gap-3">
                {isOcrProcessing ? (
                  <Loader2 size={24} className="text-secondary rotate-animation" style={{animation: 'spin 2s linear infinite'}} />
                ) : (
                  <ImageIcon size={24} className="text-accent-light" />
                )}
                <div className="flex-1" style={{minWidth: 0}}>
                  <div className="text-sm font-medium" style={{whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'}}>{uploadedFile.name}</div>
                  <div className="text-xs text-secondary">
                    {isOcrProcessing ? `AI 이미지 스캔 중... ${Math.round(ocrProgress * 100)}%` : `${(uploadedFile.size / 1024).toFixed(1)} KB`}
                  </div>
                </div>
                {!isOcrProcessing && (
                  <button
                    onClick={() => {
                      setUploadedFile(null);
                      setOcrError('');
                      setOcrWarnings([]);
                    }}
                    style={{color:'var(--text-secondary)'}}
                  >
                    <X size={16}/>
                  </button>
                )}
              </div>
              <div className="upload-progress mt-4">
                <div 
                  className={`upload-progress-fill ${ocrError ? 'error' : ''}`}
                  style={{ width: isOcrProcessing ? `${Math.max(10, ocrProgress * 100)}%` : '100%', transition: 'width 0.3s ease' }}
                ></div>
              </div>
              <div className="text-xs mt-2" style={{ color: ocrError ? '#f87171' : isOcrProcessing ? 'var(--text-secondary)' : 'var(--accent-light)' }}>
                {isOcrProcessing
                  ? 'AI가 보유 종목 표를 구조화하는 중입니다...'
                  : ocrError
                    ? `분석 실패: ${ocrError}`
                    : '✓ 추출 완료! 아래 표에서 데이터를 확인/수정하세요.'}
              </div>
              {!isOcrProcessing && ocrWarnings.length > 0 && (
                <ul className="ocr-warning-list">
                  {ocrWarnings.map((warning, index) => (
                    <li key={`${warning}-${index}`}>{warning}</li>
                  ))}
                </ul>
              )}
            </div>
          ) : (
            <div 
              className={`upload-area mt-6 ${dragOver ? 'drag-over' : ''}`}
              onClick={() => fileInputRef.current?.click()}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
            >
              <UploadCloud size={32} className="text-secondary mb-4" />
              <p className="font-medium">이미지를 드래그하거나 클릭하여 선택하세요</p>
              <p className="text-xs text-secondary mt-2">표 형태(티커, 수량, 단가)의 사진을 인식합니다</p>
            </div>
          )}
          <input type="file" ref={fileInputRef} onChange={handleFileUpload} accept="image/*" style={{display:'none'}} />
        </div>
      </div>

      {/* Card 3: Manual Input */}
      <div className="card-box w-full mb-8">
        <div className="card-header justify-between">
          <div className="flex items-center gap-2">
            <span className="icon-wrapper"><List size={16}/></span>
            <span className="font-semibold">종목 수동 입력</span>
          </div>
          <button className="text-accent text-sm font-medium flex items-center gap-1" onClick={addRow}>
            <Plus size={14}/> 행 추가
          </button>
        </div>
        
        <div className={`manual-table-wrapper mt-6 ${activeRowId ? 'has-open-suggestions' : ''}`}>
          <table className="manual-table">
            <thead>
              <tr>
                <th>티커 (TICKER)</th>
                <th>종목명 (선택)</th>
                <th>수량 (QUANTITY)</th>
                <th>
                  평균 단가 (AVG. COST)
                  <span style={{display:'block', fontSize:'0.6rem', fontWeight:400, color:'var(--text-muted)', marginTop:'2px'}}>
                    기준일: {new Date().toLocaleDateString('ko-KR', {year:'numeric', month:'2-digit', day:'2-digit'})}
                  </span>
                </th>
                <th>합계</th>
                <th>작업</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(row => (
                <tr key={row.id}>
                  <td style={{ position: 'relative', overflow: 'visible' }}>
                    <div className="ticker-input-container">
                      <input 
                        type="text" 
                        value={row.ticker}
                        onChange={(e) => updateRow(row.id, 'ticker', e.target.value)}
                        onFocus={() => handleFocus(row.id, row.ticker)}
                        onBlur={() => {
                          // Small delay to allow list click/mousedown events to complete
                          setTimeout(() => {
                            setActiveRowId(null);
                          }, 200);
                        }}
                        placeholder="티커 입력"
                        autoComplete="off"
                      />
                      {activeRowId === row.id && (
                        <div className="suggestions-dropdown">
                          {searchState.rowId === row.id && searchState.loading && (
                            <div className="suggestion-state">
                              <Loader2 size={14} className="rotate-animation" />
                              <span>검색 중입니다.</span>
                            </div>
                          )}
                          {searchState.rowId === row.id && !searchState.loading && searchState.error && (
                            <div className="suggestion-state error">
                              <AlertTriangle size={14} />
                              <span>{searchState.error}</span>
                            </div>
                          )}
                          {searchState.rowId === row.id && !searchState.loading && searchState.hasSearched && suggestions.length === 0 && (
                            <div className="suggestion-state empty">
                              해당 자산을 찾을 수 없습니다.
                            </div>
                          )}
                          {searchState.rowId === row.id && !searchState.loading && suggestions.map(s => (
                            <div 
                              key={s.ticker} 
                              className="suggestion-item"
                              onMouseDown={(e) => {
                                e.preventDefault(); // Prevent blurring the input immediately
                                selectSuggestion(row.id, s);
                              }}
                            >
                              <div className="suggestion-info">
                                <span className="suggestion-ticker">{s.ticker}</span>
                                <span className="suggestion-name">{s.name}</span>
                              </div>
                              {s.isLocal && (
                                <span className="suggestion-exchange">HedgeMate</span>
                              )}
                              {!s.isLocal && s.exchange && (
                                <span className="suggestion-exchange">{s.exchange}</span>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </td>
                  <td>
                    <input 
                      type="text" 
                      value={row.name}
                      onChange={(e) => updateRow(row.id, 'name', e.target.value)}
                      placeholder="종목명"
                    />
                  </td>
                  <td>
                    <input 
                      type="number" 
                      value={row.qty}
                      onChange={(e) => updateRow(row.id, 'qty', parseFloat(e.target.value) || 0)}
                      className="text-center" 
                    />
                  </td>
                  <td>
                    <input 
                      type="number" 
                      value={row.cost}
                      onChange={(e) => updateRow(row.id, 'cost', parseFloat(e.target.value) || 0)}
                      className="text-center" 
                      step="0.01"
                    />
                  </td>
                  <td style={{textAlign:'right', whiteSpace:'nowrap', fontSize:'0.85rem', fontWeight:600}}>
                    {(() => {
                      const isKRW = row.currency === 'KRW';
                      const total = row.qty * row.cost;
                      if (total === 0) return <span style={{color:'var(--text-muted)'}}>—</span>;
                      return <span style={{color:'var(--accent-light)'}}>{isKRW ? '₩' : '$'}{total.toLocaleString(undefined, {maximumFractionDigits: 2})}</span>;
                    })()}
                  </td>
                  <td>
                    <button className="trash-btn" onClick={() => removeRow(row.id)}>
                      <Trash2 size={16}/>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {totalValue > 0 && (
          <div className="total-bar mt-4 flex justify-between items-center">
            <span className="text-sm text-secondary">총 투자금액</span>
            <span className="text-lg font-bold text-accent-light">₩{totalValue.toLocaleString()}</span>
          </div>
        )}
        {concentrationSummary.hasConcentration && (
          <div className={`concentration-warning mt-4 ${concentrationSummary.blocksMultiAssetAnalysis ? 'blocking' : ''}`}>
            <AlertTriangle size={16} />
            <div>
              <strong>
                {concentrationSummary.blocksMultiAssetAnalysis
                  ? '단일 자산 50% 초과로 분석 전 리밸런싱이 필요합니다.'
                  : '단일자산 분석으로 진행 가능한 집중 포트폴리오입니다.'}
              </strong>
              <p>
                {concentrationLabel}
                {concentrationSummary.blocksMultiAssetAnalysis
                  ? ' · 다종목 포트폴리오는 한 종목을 50% 이하로 낮춰야 정식 분석을 실행할 수 있습니다.'
                  : ' · 1종목 포트폴리오는 분석은 가능하지만 결과는 단일 보유자산 기준으로 해석됩니다.'}
              </p>
            </div>
          </div>
        )}
      </div>

      {saveError && (
        <div className="status-strip error mt-4">
          <AlertTriangle size={14} />
          <span>{saveError}</span>
        </div>
      )}

      <div className="actions flex justify-between items-center">
        <div className="text-sm text-secondary">
          {rows.filter(r=>r.ticker.trim()).length}개 종목 등록됨
        </div>
        <div className="flex gap-4 items-center">
          <Button variant="text" onClick={handleCancel}>취소</Button>
          <Button variant="primary" onClick={handleSubmit} disabled={isSaving}>
            {editPortfolioId ? '수정 저장' : '포트폴리오 등록'} <ArrowRight size={14} />
          </Button>
        </div>
      </div>
    </div>
  );
};
