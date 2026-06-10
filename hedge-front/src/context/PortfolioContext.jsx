import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { getTickerQuote } from '../services/yahooFinance';
import {
  createServerPortfolio,
  deleteServerPortfolio,
  getAuthMe,
  listServerPortfolios,
  loginUser,
  logoutUser,
  registerUser,
  updateServerPortfolio,
} from '../services/hedgemateApi';
import { isKoreanTicker, normalizeTickerSymbol } from '../utils/helpers';

const PortfolioContext = createContext();

const isServerPortfolioId = (id) => /^\d+$/.test(String(id || ''));

export const PortfolioProvider = ({ children }) => {
  const [usdKrwRate, setUsdKrwRate] = useState(1380);
  const [currentUser, setCurrentUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [authError, setAuthError] = useState('');
  const [portfolios, setPortfolios] = useState([]);
  const [portfolioLoading, setPortfolioLoading] = useState(false);
  const [portfolioError, setPortfolioError] = useState('');

  useEffect(() => {
    const fetchRate = async () => {
      try {
        const quote = await getTickerQuote('USDKRW=X');
        if (quote && quote.price) {
          setUsdKrwRate(quote.price);
        }
      } catch (error) {
        console.error('Error fetching USDKRW=X rate, using fallback:', error);
      }
    };
    fetchRate();
  }, []);

  const loadPortfolios = async () => {
    setPortfolioLoading(true);
    setPortfolioError('');
    try {
      const payload = await listServerPortfolios();
      const nextPortfolios = Array.isArray(payload?.portfolios) ? payload.portfolios : [];
      setPortfolios(nextPortfolios);
      return nextPortfolios;
    } catch (error) {
      setPortfolioError(error.message || 'Failed to load portfolios.');
      setPortfolios([]);
      return [];
    } finally {
      setPortfolioLoading(false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    const bootstrap = async () => {
      setAuthLoading(true);
      setAuthError('');
      try {
        const payload = await getAuthMe();
        if (cancelled) return;
        if (payload?.authenticated && payload.user) {
          setCurrentUser(payload.user);
          await loadPortfolios();
        } else {
          setCurrentUser(null);
          setPortfolios([]);
        }
      } catch {
        if (!cancelled) {
          setCurrentUser(null);
          setPortfolios([]);
        }
      } finally {
        if (!cancelled) setAuthLoading(false);
      }
    };
    bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  const buildPortfolioRecord = (portfolio, base = {}) => {
    const now = new Date();
    const dateStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;

    const getValInKRW = (asset) => {
      const isUSD = asset.currency === 'USD' || (!asset.currency && !isKoreanTicker(asset.ticker));
      const rate = isUSD ? usdKrwRate : 1;
      return Number(asset.qty || asset.quantity || 0) * Number(asset.cost || asset.price || 0) * rate;
    };

    const assets = Array.isArray(portfolio.assets) ? portfolio.assets : [];
    const totalValue = Number(portfolio.totalValue ?? portfolio.totalValueKrw)
      || assets.reduce((sum, asset) => sum + getValInKRW(asset), 0);
    const assetsWithWeight = assets.map((asset) => {
      const valInKRW = getValInKRW(asset);
      const weightPct = Number(asset.weightPct ?? asset.weight)
        || (totalValue > 0 ? (valInKRW / totalValue) * 100 : 0);
      return {
        ...asset,
        ticker: normalizeTickerSymbol(asset.ticker),
        qty: Number(asset.qty ?? asset.quantity ?? 0),
        cost: Number(asset.cost ?? asset.price ?? 0),
        weight: Math.round(weightPct),
        weightPct: Number(weightPct.toFixed(4)),
      };
    });

    return {
      ...base,
      id: base.id || `portfolio-${Date.now()}`,
      portfolioId: base.portfolioId,
      name: portfolio.name,
      purpose: portfolio.purpose,
      createdAt: base.createdAt || dateStr,
      updatedAt: base.updatedAt,
      totalValue,
      returnRate: portfolio.returnRate ?? base.returnRate ?? 0,
      riskLevel: portfolio.riskLevel || base.riskLevel || 'Moderate',
      status: portfolio.status || base.status || 'new',
      assets: assetsWithWeight,
    };
  };

  const addPortfolio = async (portfolio) => {
    if (!currentUser) {
      throw new Error('Login is required before creating a portfolio.');
    }
    const localRecord = buildPortfolioRecord(portfolio);
    const payload = await createServerPortfolio(localRecord);
    const savedPortfolio = payload?.portfolio || localRecord;
    setPortfolios((prev) => [savedPortfolio, ...prev.filter((item) => item.id !== savedPortfolio.id)]);
    return savedPortfolio;
  };

  const deletePortfolio = async (id) => {
    if (isServerPortfolioId(id)) {
      await deleteServerPortfolio(id);
    }
    setPortfolios((prev) => prev.filter((portfolio) => portfolio.id !== id));
  };

  const updatePortfolio = async (id, updates) => {
    const existing = portfolios.find((portfolio) => portfolio.id === id);
    if (!existing) return null;
    const merged = updates.assets
      ? buildPortfolioRecord({ ...existing, ...updates }, { ...existing, status: updates.status || 'updated' })
      : { ...existing, ...updates };
    if (isServerPortfolioId(id)) {
      const payload = await updateServerPortfolio(id, merged);
      const savedPortfolio = payload?.portfolio || merged;
      setPortfolios((prev) => prev.map((portfolio) => (portfolio.id === id ? savedPortfolio : portfolio)));
      return savedPortfolio;
    }
    setPortfolios((prev) => prev.map((portfolio) => (portfolio.id === id ? merged : portfolio)));
    return merged;
  };

  const getPortfolioById = (id) => portfolios.find((portfolio) => portfolio.id === id);

  const login = async ({ email, password }) => {
    setAuthError('');
    const payload = await loginUser({ email, password });
    setCurrentUser(payload.user);
    await loadPortfolios();
    return payload.user;
  };

  const register = async ({ email, password, displayName }) => {
    setAuthError('');
    const payload = await registerUser({ email, password, displayName });
    setCurrentUser(payload.user);
    await loadPortfolios();
    return payload.user;
  };

  const logout = async () => {
    await logoutUser().catch(() => null);
    setCurrentUser(null);
    setPortfolios([]);
  };

  const value = useMemo(() => ({
    portfolios,
    addPortfolio,
    deletePortfolio,
    updatePortfolio,
    getPortfolioById,
    refreshPortfolios: loadPortfolios,
    usdKrwRate,
    currentUser,
    authLoading,
    authError,
    portfolioLoading,
    portfolioError,
    login,
    register,
    logout,
  }), [portfolios, usdKrwRate, currentUser, authLoading, authError, portfolioLoading, portfolioError]);

  return (
    <PortfolioContext.Provider value={value}>
      {children}
    </PortfolioContext.Provider>
  );
};

export const usePortfolios = () => {
  const context = useContext(PortfolioContext);
  if (!context) {
    throw new Error('usePortfolios must be used within a PortfolioProvider');
  }
  return context;
};
