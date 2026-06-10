#!/usr/bin/env python3
import argparse
import csv
import hmac
import hashlib
import ipaddress
import json
import math
import mimetypes
import os
import re
import secrets
import shutil
import subprocess
import sys
import threading
import uuid
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PureWindowsPath
from urllib.parse import parse_qs, unquote, urlparse
from zoneinfo import ZoneInfo

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from market_data_cache import (
    expected_latest_market_date,
    incremental_update_raw_market_data,
    latest_raw_market_manifest,
    read_raw_market_rows,
    write_text_atomic,
)
from server_persistence import (
    DuplicateEmailError,
    DuplicateRefreshJobError,
    PersistenceStore,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = ROOT
WEB_DIR = ROOT / "web"
INPUT_DIR = ROOT / "inputs"
UNIVERSE_META_PATH = INPUT_DIR / "hedge_universe_150.csv"
OUTPUT_RAW_DIR = ROOT / "outputs" / "raw"
OUTPUT_PROCESSED_DIR = ROOT / "outputs" / "processed"
OUTPUT_REPORT_DIR = ROOT / "outputs" / "reports"
DOC_RESULT_DIR = ROOT / "docs" / "STEP_1" / "04_실행결과"
SCENARIO_RESEARCH_ROOT = ROOT.parent / "scenario_research"
SCENARIO_OUTPUT_DIR = SCENARIO_RESEARCH_ROOT / "outputs"
SCENARIO_FINAL_DIR = SCENARIO_OUTPUT_DIR / "final"
SCENARIO_PROCESSED_DIR = SCENARIO_OUTPUT_DIR / "processed"
SCENARIO_REPORT_DIR = SCENARIO_OUTPUT_DIR / "reports"
SCENARIO_VECTOR_DIR = SCENARIO_OUTPUT_DIR / "scenario_vectors"
SCENARIO_NOWCAST_DIR = SCENARIO_OUTPUT_DIR / "nowcast_vectors"
SCENARIO_EVENT_DIR = SCENARIO_OUTPUT_DIR / "events"
SCENARIO_NEWS_INTRADAY_DIR = SCENARIO_OUTPUT_DIR / "news_intraday"
SCENARIO_VALIDATION_DIR = SCENARIO_OUTPUT_DIR / "validation"
SCENARIO_MANIFEST_PATH = SCENARIO_OUTPUT_DIR / "latest_manifest.json"
HEDGEMATE_MANIFEST_PATH = ROOT / "outputs" / "latest_manifest.json"
OUTPUT_VALIDATION_DIR = ROOT / "outputs" / "validation"
PRICE_CACHE_DIR = ROOT / "outputs" / "price_cache"
ANALYSIS_CACHE_DIR = ROOT / "outputs" / "analysis_cache"
ANALYSIS_CACHE_INDEX_PATH = ANALYSIS_CACHE_DIR / "index.json"
LOCALHOST_CLIENTS = {"127.0.0.1", "::1", "::ffff:127.0.0.1"}
MAX_JSON_BODY_BYTES = 2 * 1024 * 1024
RUN_INPUT_DIR = ROOT / "outputs" / "run_inputs"
FRONTEND_UI_BASE = "http://127.0.0.1:5173"
MARKET_DATA_FRESH_COVERAGE_THRESHOLD = 0.90
ANALYSIS_ENGINE_VERSION = "hedgemate_action_contract_v5"
DEFAULT_EVENT_OVERLAY_STATUS = {
    "mode": "reviewed_fixture",
    "live_gemini_extraction": "implemented_api_key_required",
    "recommendation_usage": "fixture_context_only",
    "trade_gate_usage": "disabled_for_fixture",
}
PORTFOLIO_FINGERPRINT_DIGITS = 4
DASHBOARD_BACKTEST_CANDIDATE_LIMIT = 12
DASHBOARD_ACTION_BOOTSTRAP_ITERATIONS = 60
REQUIRED_PRODUCT_ARTIFACT_KEYS = (
    "finalMarketState",
    "scenarioConfidence",
    "topActiveScenarios",
    "scenarioVector",
    "finalScenarioVector",
    "features",
    "assetScenarioSensitivity",
    "portfolio1to1",
    "portfolioMulti",
    "recommendationStatusQa",
    "backtestCsv",
    "backtestSummary",
    "backtestGateSummary",
    "formalGateAuditCsv",
    "formalGateAuditSummary",
    "portfolioVulnerabilityAttribution",
    "portfolioVulnerabilitySummary",
    "hedgeActionCandidates",
    "hedgeActionPlan",
    "hedgeActionPlanSummary",
)
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self'; "
    "img-src 'self' data:; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "frame-ancestors 'none'"
)
YAHOO_FINANCE_BASE_URL = "https://query1.finance.yahoo.com"
YAHOO_PROXY_TIMEOUT_SECONDS = 12

TICKER_LABELS = {
    "__CASH__": "현금",
    "005930.KS": "삼성전자",
    "000660.KS": "SK하이닉스",
    "005380.KS": "현대차",
    "000270.KS": "기아",
    "035420.KS": "NAVER",
    "035720.KS": "카카오",
    "207940.KS": "삼성바이오로직스",
    "068270.KS": "셀트리온",
    "051910.KS": "LG화학",
    "006400.KS": "삼성SDI",
    "066570.KS": "LG전자",
    "105560.KS": "KB금융",
    "055550.KS": "신한지주",
    "005490.KS": "POSCO홀딩스",
    "032830.KS": "삼성생명",
    "034020.KS": "두산에너빌리티",
    "003670.KS": "포스코퓨처엠",
    "011200.KS": "HMM",
    "017670.KS": "SK텔레콤",
    "000810.KS": "삼성화재",
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "NVDA": "NVIDIA",
    "AMZN": "Amazon",
    "GOOGL": "Alphabet",
    "META": "Meta",
    "TSLA": "Tesla",
    "BRK-B": "Berkshire Hathaway B",
    "JPM": "JPMorgan Chase",
    "V": "Visa",
    "MA": "Mastercard",
    "XOM": "Exxon Mobil",
    "JNJ": "Johnson & Johnson",
    "UNH": "UnitedHealth",
    "PG": "Procter & Gamble",
    "KO": "Coca-Cola",
    "HD": "Home Depot",
    "AVGO": "Broadcom",
    "COST": "Costco",
    "PFE": "Pfizer",
    "SPY": "S&P500 ETF",
    "QQQ": "Nasdaq 100 ETF",
    "DIA": "Dow ETF",
    "IWM": "Russell 2000 ETF",
    "VTI": "미국 전체주식 ETF",
    "VXUS": "미국 제외 글로벌 ETF",
    "EWY": "코리아 ETF",
    "EFA": "선진국 ETF",
    "TLT": "장기 미국국채 ETF",
    "IEF": "중기 미국국채 ETF",
    "SHY": "단기 미국국채 ETF",
    "LQD": "우량회사채 ETF",
    "HYG": "하이일드채권 ETF",
    "TIP": "물가연동채 ETF",
    "GLD": "금 ETF",
    "IAU": "금 ETF",
    "DBC": "원자재 ETF",
    "USO": "원유 ETF",
    "XLE": "에너지 섹터 ETF",
    "XLP": "필수소비재 ETF",
    "XLU": "유틸리티 ETF",
    "XLV": "헬스케어 ETF",
    "ITA": "방산 ETF",
    "PPA": "방산 ETF",
    "VNQ": "리츠 ETF",
    "BTC-USD": "비트코인",
    "ETH-USD": "이더리움",
    "BNB-USD": "BNB",
    "SOL-USD": "솔라나",
    "XRP-USD": "리플",
    "^KS200": "KOSPI200",
    "^KS11": "코스피",
}

RUN_JOBS = {}
RUN_JOBS_LOCK = threading.Lock()
_MARKET_PRICE_CACHE = {}
_FX_PRICE_CACHE = {}
_UNIVERSE_ASSET_CACHE = None
JOB_TIMEOUT_SECONDS = 15 * 60
JOB_HEARTBEAT_SECONDS = 20
DIAGNOSTIC_TEXT_LIMIT = 4000
DIAGNOSTIC_LINE_LIMIT = 40
MARKET_REFRESH_JOB_TYPE = "market_data_refresh"
INTRADAY_NEWS_JOB_TYPE = "intraday_news_overlay"
MARKET_REFRESH_MODES = {"market_data_only", "portfolio_reanalysis", "full_rebuild", "intraday_nowcast"}
INTRADAY_NEWS_REFRESH_HOURS_KST = (9, 15, 21)
KST = ZoneInfo("Asia/Seoul")
SESSION_COOKIE_NAME = "hedgemate_session"
SESSION_TTL_DAYS = 14
PBKDF2_ITERATIONS = 260_000
PRODUCT_STATUS_VALUES = {"READY", "NEEDS_ANALYSIS", "REFRESHING", "STALE", "ERROR", "REVIEW_ONLY"}
REFRESH_JOB_TYPE_MARKET_DATA = "market_data_only"
REFRESH_JOB_TYPE_INTRADAY_NOWCAST = "intraday_nowcast"
REFRESH_JOB_TYPE_NEWS_OVERLAY = "news_overlay"
SCHEDULER_INTERVAL_SECONDS = 3 * 60 * 60
SCHEDULER_STATE = {
    "enabled": False,
    "running": False,
    "lastStartedAt": None,
    "lastCycleAt": None,
    "lastError": None,
}
TRUTHY_ENV_VALUES = {"1", "true", "yes", "on"}
_PERSISTENCE_STORE = None
_PERSISTENCE_LOCK = threading.RLock()
_EPHEMERAL_SESSION_SECRET = secrets.token_hex(32)
STAGE_DETAILS = {
    "queued": ("대기 중", "작업 순서를 기다리고 있습니다."),
    "running HedgeMate analysis": ("특징량 생성 중", "가격 데이터 기반 특징량, 취약성, 헷지 후보를 계산합니다."),
    "running scenario backtest": ("과거 검증 중", "walk-forward/backtest와 stress 검증을 실행합니다."),
    "applying backtest gate": ("gate 검증 중", "backtest 결과를 추천 상태에 반영합니다."),
    "updating active dashboard bundle": ("백엔드 최신 분석 결과 갱신 중", "선택 포트폴리오 기준 산출물을 active bundle에 연결합니다."),
    "refreshing": ("시장데이터 갱신 중", "시장데이터와 시나리오 산출물을 최신화합니다."),
    "running refresh pipeline": ("시장데이터 갱신 중", "raw market data와 final market state를 재생성합니다."),
    "intraday news overlay": ("뉴스 오버레이 갱신 중", "시장국면 보조 설명용 Top5 뉴스 리스크를 갱신합니다."),
    "skipped_latest": ("최신 데이터 확인 완료", "이미 오늘 기준 최신 데이터입니다."),
    "blocked_by_existing_job": ("시장데이터 확인 대기", "다른 시장데이터 작업이 진행 중입니다."),
    "complete": ("완료", "작업이 완료되었습니다."),
    "completed": ("완료", "작업이 완료되었습니다."),
    "failed": ("실패", "작업이 실패했습니다. 오류 메시지를 확인하세요."),
}

def _utc_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def persistence_store():
    global _PERSISTENCE_STORE
    with _PERSISTENCE_LOCK:
        if _PERSISTENCE_STORE is None:
            _PERSISTENCE_STORE = PersistenceStore()
        return _PERSISTENCE_STORE


def server_safe_mode():
    return os.environ.get("HEDGEMATE_SERVER_SAFE_MODE", "").strip().lower() in TRUTHY_ENV_VALUES


def server_safe_skip_refresh_job(job_id, job_type, mode, trigger_type, payload=None, status_payload=None):
    payload = payload or {}
    status_payload = status_payload or {}
    started_at = _now_iso()
    reason = (
        "Server safe mode skipped this refresh to keep the deployed API responsive. "
        "Run the heavy refresh from an offline worker or local machine, then redeploy the generated artifacts."
    )
    with RUN_JOBS_LOCK:
        RUN_JOBS[job_id] = {
            "jobId": job_id,
            "jobType": MARKET_REFRESH_JOB_TYPE if job_type != REFRESH_JOB_TYPE_NEWS_OVERLAY else INTRADAY_NEWS_JOB_TYPE,
            "mode": mode,
            "startupRefresh": bool(payload.get("startupRefresh")),
            "status": "skipped_latest",
            "stage": "server_safe_mode",
            "currentStep": "server safe mode skipped heavy refresh",
            "estimatedRemainingMessage": "",
            "lastHeartbeatAt": started_at,
            "elapsedSeconds": 0,
            "timeoutSeconds": JOB_TIMEOUT_SECONDS,
            "runId": None,
            "error": None,
            "result": {
                "ok": True,
                "skipped": True,
                "serverSafeMode": True,
                "mode": mode,
                "reason": reason,
                **status_payload,
            },
            "freshness": status_payload.get("freshness") or {},
            "intradayNowcast": status_payload.get("intradayNowcast"),
            "intradayNewsOverlay": status_payload.get("intradayNewsOverlay"),
            "startedAt": started_at,
            "completedAt": started_at,
        }
    create_refresh_job_record(job_id, job_type, trigger_type, status="PENDING")
    update_refresh_job_record(job_id, "SKIPPED_SERVER_SAFE_MODE", finished=True)
    record_data_snapshot_for_refresh(job_type, "SKIPPED_SERVER_SAFE_MODE", payload=payload, result=_snapshot_run_job(job_id))
    return _snapshot_run_job(job_id)


def reset_persistence_for_tests(database_url=None, sqlite_path=None):
    global _PERSISTENCE_STORE
    with _PERSISTENCE_LOCK:
        _PERSISTENCE_STORE = PersistenceStore(database_url=database_url, sqlite_path=sqlite_path)
        _PERSISTENCE_STORE.init_db()
        return _PERSISTENCE_STORE


def database_health():
    return persistence_store().health()


def session_secret():
    return os.environ.get("SESSION_SECRET") or _EPHEMERAL_SESSION_SECRET


def hash_password(password):
    raw = str(password or "")
    if len(raw) < 8:
        raise ValueError("Password must be at least 8 characters.")
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", raw.encode("utf-8"), salt.encode("ascii"), PBKDF2_ITERATIONS).hex()
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest}"


def verify_password(password, stored_hash):
    try:
        algorithm, iterations, salt, expected = str(stored_hash or "").split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            str(password or "").encode("utf-8"),
            salt.encode("ascii"),
            int(iterations),
        ).hex()
        return hmac.compare_digest(digest, expected)
    except Exception:
        return False


def sign_session_id(session_id):
    return hmac.new(session_secret().encode("utf-8"), str(session_id).encode("ascii"), hashlib.sha256).hexdigest()


def encode_session_cookie(session_id):
    return str(session_id)


def decode_session_cookie(value):
    raw = str(value or "").strip()
    session_id, signature = raw.split(".", 1) if "." in raw else (raw, "")
    if not re.fullmatch(r"[0-9a-f]{64}", session_id):
        return None
    if signature and hmac.compare_digest(sign_session_id(session_id), signature):
        return session_id
    return session_id


def parse_cookie_header(header):
    cookies = {}
    for part in str(header or "").split(";"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        cookies[key.strip()] = urllib.parse.unquote(value.strip())
    return cookies


def session_cookie_header(session_id, expires_at=None):
    max_age = SESSION_TTL_DAYS * 24 * 60 * 60
    parts = [
        f"{SESSION_COOKIE_NAME}={urllib.parse.quote(encode_session_cookie(session_id))}",
        "Path=/",
        "HttpOnly",
        "SameSite=Lax",
        f"Max-Age={max_age}",
    ]
    if os.environ.get("HEDGEMATE_COOKIE_SECURE", "").strip().lower() in {"1", "true", "yes", "on"}:
        parts.append("Secure")
    if expires_at:
        parts.append(f"Expires={expires_at}")
    return "; ".join(parts)


def clear_session_cookie_header():
    return f"{SESSION_COOKIE_NAME}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0; Expires=Thu, 01 Jan 1970 00:00:00 GMT"


def public_user(user):
    if not user:
        return None
    return {
        "id": str(user.get("id") or user.get("user_id")),
        "userId": int(user.get("id") or user.get("user_id")),
        "email": user.get("email"),
        "displayName": user.get("display_name") or user.get("displayName") or user.get("email"),
    }


def current_user_from_headers(headers):
    cookies = parse_cookie_header(headers.get("Cookie") if headers else "")
    session_id = decode_session_cookie(cookies.get(SESSION_COOKIE_NAME))
    if not session_id:
        return None
    session = persistence_store().get_session(session_id)
    if not session:
        return None
    return {
        "id": session.get("user_id"),
        "user_id": session.get("user_id"),
        "email": session.get("email"),
        "display_name": session.get("display_name"),
        "session_id": session_id,
    }


def create_login_session(user_id):
    session_id = secrets.token_hex(32)
    expires_at = (
        datetime.now(timezone.utc) + timedelta(days=SESSION_TTL_DAYS)
    ).replace(tzinfo=None, microsecond=0).isoformat(sep=" ")
    persistence_store().create_session(session_id, int(user_id), expires_at)
    return session_id, expires_at


def auth_register(payload):
    email = str((payload or {}).get("email") or "").strip().lower()
    password = str((payload or {}).get("password") or "")
    display_name = str((payload or {}).get("displayName") or (payload or {}).get("display_name") or "").strip() or None
    if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        raise ValueError("A valid email address is required.")
    password_hash = hash_password(password)
    user = persistence_store().create_user(email, password_hash, display_name)
    session_id, _ = create_login_session(user["id"])
    return {"authenticated": True, "user": public_user(user)}, session_cookie_header(session_id)


def auth_login(payload):
    email = str((payload or {}).get("email") or "").strip().lower()
    password = str((payload or {}).get("password") or "")
    user = persistence_store().get_user_by_email(email)
    if not user or not verify_password(password, user.get("password_hash")):
        raise PermissionError("Invalid email or password.")
    session_id, _ = create_login_session(user["id"])
    return {"authenticated": True, "user": public_user(user)}, session_cookie_header(session_id)


def auth_logout(headers):
    user = current_user_from_headers(headers)
    if user and user.get("session_id"):
        persistence_store().delete_session(user["session_id"])
    return {"ok": True, "authenticated": False}, clear_session_cookie_header()


ASSET_ALIASES = {
    "삼성전자": "005930.KS",
    "삼성": "005930.KS",
    "samsung": "005930.KS",
    "samsungelec": "005930.KS",
    "samsung electronics": "005930.KS",
    "005930": "005930.KS",
    "sk하이닉스": "000660.KS",
    "하이닉스": "000660.KS",
    "현대차": "005380.KS",
    "현대자동차": "005380.KS",
    "기아": "000270.KS",
    "kia": "000270.KS",
    "000270": "000270.KS",
    "네이버": "035420.KS",
    "naver": "035420.KS",
    "카카오": "035720.KS",
    "셀트리온": "068270.KS",
    "애플": "AAPL",
    "apple": "AAPL",
    "마이크로소프트": "MSFT",
    "microsoft": "MSFT",
    "엔비디아": "NVDA",
    "nvidia": "NVDA",
    "테슬라": "TSLA",
    "tesla": "TSLA",
    "금 etf": "GLD",
    "금etf": "GLD",
    "금": "GLD",
    "gold": "GLD",
    "gld": "GLD",
    "장기국채 etf": "TLT",
    "장기국채etf": "TLT",
    "장기국채": "TLT",
    "장기 미국국채": "TLT",
    "중기국채 etf": "IEF",
    "중기국채etf": "IEF",
    "중기국채": "IEF",
    "중기 미국국채": "IEF",
    "단기국채 etf": "SHY",
    "단기국채etf": "SHY",
    "단기국채": "SHY",
    "단기 미국국채": "SHY",
    "s&p500 etf": "SPY",
    "s&p 500 etf": "SPY",
    "sp500 etf": "SPY",
    "sp500": "SPY",
    "s&p500": "SPY",
    "나스닥 etf": "QQQ",
    "나스닥": "QQQ",
    "현금": "__CASH__",
    "cash": "__CASH__",
}


def normalize_asset_query(value):
    return re.sub(r"[^0-9A-Za-z가-힣&+.^-]+", "", str(value or "").strip()).lower()


def universe_asset_rows():
    global _UNIVERSE_ASSET_CACHE
    if _UNIVERSE_ASSET_CACHE is not None:
        return _UNIVERSE_ASSET_CACHE
    rows = []
    if UNIVERSE_META_PATH.exists():
        with UNIVERSE_META_PATH.open("r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                ticker = str(row.get("ticker") or "").strip()
                if ticker:
                    rows.append(row)
    _UNIVERSE_ASSET_CACHE = rows
    return rows


def universe_label_map():
    labels = {}
    for row in universe_asset_rows():
        ticker = str(row.get("ticker") or "").strip()
        label = str(row.get("display_name") or "").strip()
        if ticker and label:
            labels[ticker] = label
    return labels


def all_asset_labels():
    labels = universe_label_map()
    labels.update(TICKER_LABELS)
    return labels


def universe_meta_by_ticker():
    return {
        str(row.get("ticker") or "").strip(): row
        for row in universe_asset_rows()
        if str(row.get("ticker") or "").strip()
    }


def aliases_by_ticker():
    rows = {}
    for alias, ticker in ASSET_ALIASES.items():
        rows.setdefault(ticker, set()).add(alias)
    return {ticker: sorted(values) for ticker, values in rows.items()}


def asset_class_label(ticker):
    ticker = str(ticker or "")
    if ticker == "__CASH__":
        return "현금"
    if ticker.endswith(".KS"):
        return "국내주식"
    if ticker.endswith("-USD"):
        return "암호자산"
    if ticker.startswith("^"):
        return "시장지수"
    label = display_name(ticker)
    if "ETF" in label or ticker in {"SPY", "QQQ", "DIA", "IWM", "VTI", "VXUS", "EWY", "EFA", "TLT", "IEF", "SHY", "LQD", "HYG", "TIP", "GLD", "IAU", "DBC", "USO", "XLE", "XLP", "XLU", "XLV", "ITA", "PPA", "VNQ"}:
        return "ETF"
    return "미국주식"


def display_label(ticker):
    ticker = str(ticker or "")
    label = display_name(ticker)
    if not ticker or ticker == "__CASH__":
        return label
    return f"{label} ({ticker})"


def asset_options():
    aliases = aliases_by_ticker()
    labels = all_asset_labels()
    universe_meta = universe_meta_by_ticker()
    rows = []
    for ticker, label in sorted(labels.items(), key=lambda item: (item[1], item[0])):
        if ticker == "__CASH__":
            continue
        meta = universe_meta.get(ticker, {})
        ticker_aliases = aliases.get(ticker, [])
        search_parts = [
            label,
            ticker,
            display_label(ticker),
            meta.get("display_name"),
            meta.get("asset_class"),
            meta.get("risk_sleeves"),
            meta.get("primary_vulnerability_tags"),
            meta.get("notes_ko"),
            *ticker_aliases,
        ]
        rows.append(
            {
                "ticker": ticker,
                "label": label,
                "displayLabel": display_label(ticker),
                "popularName": label,
                "assetClass": asset_class_label(ticker),
                "aliases": ticker_aliases,
                "searchText": " ".join(str(part) for part in search_parts if part),
            }
        )
    return rows


def resolve_asset_query(query):
    raw = str(query or "").strip()
    if not raw:
        raise ValueError("자산명이 비어 있습니다.")

    upper = raw.upper()
    labels = all_asset_labels()
    if upper in labels:
        return upper

    normalized = normalize_asset_query(raw)
    alias_key = re.sub(r"\s+", " ", raw.lower()).strip()
    if alias_key in ASSET_ALIASES:
        return ASSET_ALIASES[alias_key]
    if normalized in ASSET_ALIASES:
        return ASSET_ALIASES[normalized]

    exact = [ticker for ticker, label in labels.items() if normalize_asset_query(label) == normalized]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        raise ValueError("동일 이름 자산이 여러 개입니다. 티커를 직접 입력해 주세요.")

    alias_rows = aliases_by_ticker()
    prefix = []
    for ticker, label in labels.items():
        candidates = [label, ticker, display_label(ticker), *alias_rows.get(ticker, [])]
        if normalized and any(normalize_asset_query(candidate).startswith(normalized) for candidate in candidates):
            prefix.append(ticker)
    if len(prefix) == 1:
        return prefix[0]

    partial = []
    for ticker, label in labels.items():
        candidates = [label, ticker, display_label(ticker), *alias_rows.get(ticker, [])]
        if normalized and any(normalized in normalize_asset_query(candidate) for candidate in candidates):
            partial.append(ticker)
    if len(partial) == 1:
        return partial[0]
    if len(partial) > 1:
        raise ValueError("검색 결과가 여러 개입니다. 더 정확한 자산명 또는 티커를 입력해 주세요.")

    raise ValueError("지원하지 않는 자산입니다. 목록에서 정확한 자산을 선택해 주세요.")


def parse_float(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return value


def build_run_id():
    return datetime.now().strftime("%Y%m%dT%H%M%S%f") + f"-{uuid.uuid4().hex[:8]}"


def parse_max_combo_size(value):
    try:
        parsed = int(value if value not in (None, "") else 4)
    except (TypeError, ValueError) as exc:
        raise ValueError("최대 조합 수는 숫자여야 합니다.") from exc
    return max(1, min(parsed, 4))


def display_name(ticker):
    ticker = str(ticker or "")
    return all_asset_labels().get(ticker, ticker)


def humanize_combo(label):
    return " + ".join(display_label(part.strip()) for part in str(label or "").split(" + ") if part.strip())


def humanize_scenario(scenario):
    scenario = str(scenario or "")
    if scenario.startswith("기존 포트폴리오"):
        return scenario
    for prefix in ["제안(1:1) - ", "참고안(1:1) - ", "차선후보(1:1) - "]:
        if scenario.startswith(prefix):
            ticker = scenario[len(prefix):].strip()
            return f"{prefix}{display_label(ticker)}"
    for prefix in ["제안(다자산) - ", "참고안(다자산) - ", "차선후보(다자산) - "]:
        if scenario.startswith(prefix):
            combo = scenario[len(prefix):].strip()
            return f"{prefix}{humanize_combo(combo)}"
    m = re.match(r"기준\((.+?) 100%\)", scenario)
    if m:
        return f"기준({display_label(m.group(1))} 100%)"
    return scenario


def read_csv_rows(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = []
        for row in csv.DictReader(f):
            rows.append({k: parse_float(v) for k, v in row.items()})
        return rows


def read_json(path, fallback=None):
    if not path.exists():
        return fallback
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_json_or_csv_rows(path):
    if not path:
        return []
    if Path(path).suffix.lower() == ".csv":
        return read_csv_rows(Path(path))
    return read_json(Path(path), []) or []


def file_sha256(path):
    if not path or not Path(path).exists():
        return None
    digest = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def active_analysis_cache_dir():
    base = Path(ANALYSIS_CACHE_DIR)
    if base == DEFAULT_ROOT / "outputs" / "analysis_cache":
        base = ROOT / "outputs" / "analysis_cache"
    return base


def analysis_cache_index_path():
    return active_analysis_cache_dir() / "index.json"


def stable_number_text(value, digits=6):
    number = parse_float(value)
    if number is None:
        return ""
    return f"{number:.{digits}f}".rstrip("0").rstrip(".")


def portfolio_request_fingerprint(payload):
    rows = (payload or {}).get("portfolioRows") or []
    parts = []
    tickers = []
    for row in rows:
        ticker = resolve_asset_query(row.get("ticker") or row.get("asset") or row.get("symbol") or row.get("name"))
        if not ticker:
            continue
        tickers.append(ticker)
        quantity = stable_number_text(row.get("quantity"), digits=8)
        amount = stable_number_text(row.get("amountKrw"), digits=2)
        if quantity:
            measure = f"q:{quantity}"
        elif amount:
            measure = f"a:{amount}"
        else:
            measure = "unspecified"
        parts.append(f"{ticker}:{measure}")
    canonical = "|".join(sorted(parts))
    if not canonical:
        return None
    return {
        "hash": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "canonical": canonical,
        "tickers": normalize_ticker_list(tickers),
    }


def analysis_cache_key(payload, data_version=None, scenario_vector=None):
    request_fp = portfolio_request_fingerprint(payload)
    if not request_fp:
        return None
    scenario_path = Path(scenario_vector) if scenario_vector else resolve_product_artifact(read_product_manifest(), "finalScenarioVector", default_dir=SCENARIO_VECTOR_DIR)
    key_payload = {
        "engineVersion": ANALYSIS_ENGINE_VERSION,
        "portfolioRequestHash": request_fp["hash"],
        "hedgeBudgetKrw": stable_number_text((payload or {}).get("hedgeBudgetKrw"), digits=2),
        "hedgeBudgets": str((payload or {}).get("hedgeBudgets") or ""),
        "maxComboSize": str(parse_max_combo_size((payload or {}).get("maxComboSize"))),
        "dataVersion": str(data_version or (payload or {}).get("dataVersion") or active_data_version() or ""),
        "scenarioVectorSha256": file_sha256(scenario_path),
        "universeSha256": file_sha256(UNIVERSE_META_PATH),
    }
    canonical = json.dumps(key_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "hash": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "payload": key_payload,
        "portfolioRequestFingerprint": request_fp,
    }


def read_analysis_cache_index():
    path = analysis_cache_index_path()
    payload = read_json(path, {}) if path.exists() else {}
    if not isinstance(payload, dict):
        payload = {}
    payload.setdefault("version", "analysis_cache_v1")
    payload.setdefault("entries", {})
    return payload


def write_analysis_cache_index(index):
    path = analysis_cache_index_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def cache_manifest_path(run_id):
    return active_analysis_cache_dir() / f"{safe_run_id_fragment(run_id)}.json"


def read_product_manifest():
    manifest_path = ROOT / "outputs" / "latest_manifest.json"
    payload = read_json(manifest_path, {}) if manifest_path.exists() else {}
    return payload if isinstance(payload, dict) else {}


def read_active_manifest():
    manifest_path = SCENARIO_OUTPUT_DIR / "latest_manifest.json"
    payload = read_json(manifest_path, {}) if manifest_path.exists() else {}
    return payload if isinstance(payload, dict) else {}


def resolve_any_artifact(raw_path, default_dir=None):
    if not raw_path:
        return None
    candidate = Path(str(raw_path))
    candidates = []
    if default_dir:
        fallback_names = []
        for name in (candidate.name, PureWindowsPath(str(raw_path)).name):
            if name and name not in fallback_names:
                fallback_names.append(name)
        for name in fallback_names:
            candidates.append(Path(default_dir) / name)
    if candidate.is_absolute():
        candidates.append(candidate)
    else:
        candidates.extend(
            [
                ROOT / candidate,
                ROOT.parent / candidate,
                SCENARIO_OUTPUT_DIR / candidate,
            ]
        )
        if default_dir:
            candidates.append(Path(default_dir) / candidate)
    for path in candidates:
        if path.exists():
            return path
    return None


def resolve_product_artifact(manifest, key, default_dir=None):
    artifacts = manifest.get("artifacts", {}) if isinstance(manifest, dict) else {}
    raw_path = artifacts.get(key) if isinstance(artifacts, dict) else None
    raw_path = raw_path or manifest.get(f"{key}_path") or manifest.get(key)
    return resolve_any_artifact(raw_path, default_dir=default_dir)


def resolve_scenario_manifest_artifact(manifest, key, default_dir=None):
    raw_path = None
    if isinstance(manifest, dict):
        raw_path = manifest.get(f"{key}_path") or manifest.get(key)
    return resolve_any_artifact(raw_path, default_dir=default_dir)


def existing_artifact(path):
    if not path:
        return None
    candidate = Path(path)
    return candidate if candidate.exists() else None


def data_version_from_run_id(run_id):
    matches = re.findall(r"\d{8}", str(run_id or ""))
    return matches[-1] if matches else None


def resolve_active_gated_recommendation_artifact(manifest, key):
    path = resolve_product_artifact(manifest, key, default_dir=OUTPUT_REPORT_DIR)
    if not path:
        return None, f"missing active gated recommendation artifact: {key}"
    if "_backtest_gated" not in path.name:
        return None, f"active recommendation artifact is not backtest-gated: {key}={path.name}"
    return path, ""


def active_bundle(manifest=None):
    manifest = manifest or read_product_manifest()
    bundle = manifest.get("active_bundle", {}) if isinstance(manifest, dict) else {}
    return bundle if isinstance(bundle, dict) else {}


def normalized_event_overlay_status(raw_status=None):
    status = dict(DEFAULT_EVENT_OVERLAY_STATUS)
    if isinstance(raw_status, dict):
        status.update({key: value for key, value in raw_status.items() if value not in (None, "")})
    return status


def active_data_version(manifest=None):
    manifest = manifest or read_product_manifest()
    bundle = active_bundle(manifest)
    return str(bundle.get("data_version") or manifest.get("data_version") or "").strip()


def parse_money_value(value):
    if value in (None, ""):
        return None
    try:
        parsed = float(str(value).replace(",", "").strip())
    except (TypeError, ValueError) as exc:
        raise ValueError("금액 또는 수량을 숫자로 해석할 수 없습니다.") from exc
    return parsed


def ticker_currency(ticker):
    if ticker == "__CASH__":
        return "KRW"
    if str(ticker).endswith(".KS") or str(ticker).startswith("^KS"):
        return "KRW"
    return "USD"


def raw_market_path_for_data_version(data_version=None):
    if data_version:
        candidate = OUTPUT_RAW_DIR / f"raw_market_daily_{data_version}.csv"
        if candidate.exists():
            return candidate
    return latest_path(OUTPUT_RAW_DIR, "raw_market_daily_*.csv")


def raw_fx_path_for_data_version(data_version=None):
    if data_version:
        candidate = OUTPUT_RAW_DIR / f"raw_fx_daily_{data_version}.csv"
        if candidate.exists():
            return candidate
    return latest_path(OUTPUT_RAW_DIR, "raw_fx_daily_*.csv")


def latest_market_price_map(data_version=None):
    path = raw_market_path_for_data_version(data_version)
    if not path:
        return {}, None
    cache_key = (str(path.resolve()), path.stat().st_mtime_ns)
    if cache_key in _MARKET_PRICE_CACHE:
        return _MARKET_PRICE_CACHE[cache_key], path

    latest = {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            ticker = str(row.get("ticker") or "").strip()
            if not ticker:
                continue
            date_value = str(row.get("date") or "")
            price = parse_float(row.get("adj_close") or row.get("close"))
            if not isinstance(price, (int, float)):
                continue
            previous = latest.get(ticker)
            if previous and str(previous.get("asOfDate") or "") > date_value:
                continue
            latest[ticker] = {
                "ticker": ticker,
                "latestPrice": float(price),
                "currency": row.get("currency") or ticker_currency(ticker),
                "asOfDate": date_value,
                "source": row.get("source") or "raw_market_cache",
                "assetClass": row.get("asset_class"),
                "ingestedAt": row.get("ingested_at"),
                "dataMode": "cache",
            }
    _MARKET_PRICE_CACHE.clear()
    _MARKET_PRICE_CACHE[cache_key] = latest
    return latest, path


def latest_fx_quote(data_version=None):
    path = raw_fx_path_for_data_version(data_version)
    if not path:
        return {
            "pair": "USD/KRW",
            "rate": None,
            "asOfDate": None,
            "source": None,
            "dataMode": "unavailable",
            "error": "USD/KRW 환율 캐시 파일을 찾지 못했습니다.",
        }
    cache_key = (str(path.resolve()), path.stat().st_mtime_ns)
    if cache_key in _FX_PRICE_CACHE:
        return _FX_PRICE_CACHE[cache_key]

    latest = None
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            rate = parse_float(row.get("close"))
            if not isinstance(rate, (int, float)):
                continue
            date_value = str(row.get("date") or "")
            if latest and str(latest.get("asOfDate") or "") > date_value:
                continue
            latest = {
                "pair": "USD/KRW",
                "rate": float(rate),
                "asOfDate": date_value,
                "source": row.get("source") or "raw_fx_cache",
                "ingestedAt": row.get("ingested_at"),
                "dataMode": "cache",
            }
    if latest is None:
        latest = {
            "pair": "USD/KRW",
            "rate": None,
            "asOfDate": None,
            "source": "raw_fx_cache",
            "dataMode": "unavailable",
            "error": "USD/KRW 환율 행을 찾지 못했습니다.",
        }
    _FX_PRICE_CACHE.clear()
    _FX_PRICE_CACHE[cache_key] = latest
    return latest


def yahoo_symbol_for_ticker(ticker):
    if ticker == "KRW=X":
        return "KRW=X"
    return ticker


def fetch_yahoo_quote(ticker, timeout=4):
    symbol = yahoo_symbol_for_ticker(ticker)
    query = urllib.parse.urlencode({"symbols": symbol})
    url = f"https://query1.finance.yahoo.com/v7/finance/quote?{query}"
    request = urllib.request.Request(url, headers={"User-Agent": "HedgeMate/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        results = payload.get("quoteResponse", {}).get("result", [])
        if not results:
            raise RuntimeError(f"Yahoo quote result is empty for {ticker}")
        row = results[0]
        price = row.get("regularMarketPrice") or row.get("postMarketPrice") or row.get("preMarketPrice")
        if price is None:
            raise RuntimeError(f"Yahoo quote price is missing for {ticker}")
        market_time = row.get("regularMarketTime")
        as_of = datetime.fromtimestamp(market_time).isoformat(timespec="seconds") if market_time else datetime.now().isoformat(timespec="seconds")
        return {
            "ticker": ticker,
            "latestPrice": float(price),
            "currency": row.get("currency") or ticker_currency(ticker),
            "asOfDate": as_of,
            "source": "yahoo_quote",
            "assetClass": None,
            "dataMode": "live",
        }
    except Exception as exc:
        return fetch_yahoo_chart_quote(ticker, timeout=timeout, quote_error=exc)


def fetch_yahoo_chart_quote(ticker, timeout=4, quote_error=None):
    symbol = yahoo_symbol_for_ticker(ticker)
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}?range=5d&interval=1d"
    request = urllib.request.Request(url, headers={"User-Agent": "HedgeMate/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    results = payload.get("chart", {}).get("result", [])
    if not results:
        suffix = f" after quote endpoint failed: {quote_error}" if quote_error else ""
        raise RuntimeError(f"Yahoo chart result is empty for {ticker}{suffix}")
    result = results[0]
    meta = result.get("meta", {})
    quote = (result.get("indicators", {}).get("quote") or [{}])[0]
    closes = [value for value in (quote.get("close") or []) if isinstance(value, (int, float))]
    price = meta.get("regularMarketPrice") or (closes[-1] if closes else None)
    if price is None:
        suffix = f" after quote endpoint failed: {quote_error}" if quote_error else ""
        raise RuntimeError(f"Yahoo chart price is missing for {ticker}{suffix}")
    timestamps = result.get("timestamp") or []
    market_time = meta.get("regularMarketTime") or (timestamps[-1] if timestamps else None)
    as_of = datetime.fromtimestamp(market_time).isoformat(timespec="seconds") if market_time else datetime.now().isoformat(timespec="seconds")
    return {
        "ticker": ticker,
        "latestPrice": float(price),
        "currency": meta.get("currency") or ticker_currency(ticker),
        "asOfDate": as_of,
        "source": "yahoo_chart",
        "assetClass": None,
        "dataMode": "live",
    }


def lookup_price(asset, quantity=None, amount_krw=None, use_live=False, data_version=None):
    ticker = resolve_asset_query(asset)
    warnings = []
    errors = []
    amount_value = parse_money_value(amount_krw)
    quantity_value = parse_money_value(quantity)
    if amount_value is not None and amount_value <= 0:
        errors.append("KRW 금액은 0보다 커야 합니다.")
    if quantity_value is not None and quantity_value <= 0:
        errors.append("수량은 0보다 커야 합니다.")

    if ticker == "__CASH__":
        krw_value = amount_value if amount_value is not None else quantity_value
        if krw_value is None:
            errors.append("현금은 KRW 금액을 입력해야 합니다.")
            krw_value = 0.0
        return {
            "input": asset,
            "resolvedTicker": ticker,
            "displayName": "현금",
            "displayLabel": "현금",
            "assetClass": "cash",
            "currency": "KRW",
            "latestPrice": 1.0,
            "unitPriceKrw": 1.0,
            "priceAsOf": display_reference_date(),
            "fxRate": 1.0,
            "fxAsOf": display_reference_date(),
            "quantity": quantity_value,
            "amountKrw": amount_value,
            "marketValueKrw": float(krw_value or 0.0),
            "impliedQuantity": float(krw_value or 0.0),
            "valuationBasis": "amount" if amount_value is not None else "cash",
            "dataMode": "cash",
            "warnings": warnings,
            "errors": errors,
        }

    price_payload = None
    if use_live:
        try:
            price_payload = fetch_yahoo_quote(ticker)
        except Exception as exc:
            warnings.append(f"실시간 가격 조회 실패, 캐시 사용 시도: {exc}")

    if price_payload is None:
        price_map, raw_path = latest_market_price_map(data_version or active_data_version())
        price_payload = price_map.get(ticker)
        if price_payload:
            warnings.append(f"실시간 가격이 아니라 로컬 캐시를 사용했습니다: {raw_path.name if raw_path else 'unknown'}")

    if price_payload is None:
        message = f"{ticker} 가격 데이터를 찾지 못했습니다."
        if amount_value is None:
            errors.append(message)
        else:
            warnings.append(message + " KRW 금액 입력값으로 평가액을 계산했습니다.")
        price_payload = {
            "ticker": ticker,
            "latestPrice": None,
            "currency": ticker_currency(ticker),
            "asOfDate": None,
            "source": None,
            "assetClass": None,
            "dataMode": "unavailable",
        }

    currency = price_payload.get("currency") or ticker_currency(ticker)
    fx_payload = {"rate": 1.0, "asOfDate": price_payload.get("asOfDate"), "dataMode": "not_required", "source": "KRW"}
    if currency != "KRW":
        fx_payload = latest_fx_quote(data_version or active_data_version())
        if fx_payload.get("rate") is None:
            if amount_value is None:
                errors.append(f"{currency}/KRW 환율 데이터를 찾지 못했습니다.")
            else:
                warnings.append(f"{currency}/KRW 환율 데이터를 찾지 못했습니다. KRW 금액 입력값으로 평가액을 계산했습니다.")
        elif fx_payload.get("dataMode") == "cache":
            warnings.append("해외자산 KRW 환산에 USD/KRW 로컬 캐시를 사용했습니다.")

    latest_price = price_payload.get("latestPrice")
    fx_rate = fx_payload.get("rate") if currency != "KRW" else 1.0
    unit_price_krw = float(latest_price) * float(fx_rate) if latest_price is not None and fx_rate is not None else None
    valuation_basis = "quantity" if quantity_value is not None else "amount" if amount_value is not None else None
    market_value_krw = None
    implied_quantity = None
    if quantity_value is not None and latest_price and fx_rate:
        market_value_krw = quantity_value * float(latest_price) * float(fx_rate)
        if amount_value is not None:
            warnings.append("수량과 금액이 모두 입력되어 최신 가격×수량 기준으로 평가했습니다.")
    elif amount_value is not None:
        market_value_krw = amount_value
        if latest_price and fx_rate:
            implied_quantity = amount_value / (float(latest_price) * float(fx_rate))
    elif quantity_value is None:
        errors.append("KRW 금액 또는 보유 수량 중 하나는 입력해야 합니다.")

    return {
        "input": asset,
        "resolvedTicker": ticker,
        "displayName": display_name(ticker),
        "displayLabel": display_label(ticker),
        "assetClass": price_payload.get("assetClass"),
        "currency": currency,
        "latestPrice": latest_price,
        "unitPriceKrw": unit_price_krw,
        "priceAsOf": price_payload.get("asOfDate"),
        "priceSource": price_payload.get("source"),
        "fxRate": fx_rate,
        "fxAsOf": fx_payload.get("asOfDate"),
        "fxSource": fx_payload.get("source"),
        "quantity": quantity_value,
        "amountKrw": amount_value,
        "marketValueKrw": market_value_krw,
        "impliedQuantity": implied_quantity,
        "valuationBasis": valuation_basis,
        "dataMode": price_payload.get("dataMode"),
        "warnings": warnings,
        "errors": errors,
    }


def preview_portfolio(payload):
    raw_rows = (payload or {}).get("portfolioRows") or []
    if not isinstance(raw_rows, list) or not raw_rows:
        raise ValueError("포트폴리오 자산 행이 필요합니다.")
    use_live = bool((payload or {}).get("useLivePrices"))
    data_version = (payload or {}).get("dataVersion") or active_data_version()
    rows = []
    errors = []
    warnings = []
    seen = {}
    total_value = 0.0
    for index, item in enumerate(raw_rows):
        asset = (item or {}).get("asset") or (item or {}).get("ticker")
        try:
            row = lookup_price(
                asset,
                quantity=(item or {}).get("quantity"),
                amount_krw=(item or {}).get("amountKrw"),
                use_live=use_live,
                data_version=data_version,
            )
        except ValueError as exc:
            row = {
                "input": asset,
                "resolvedTicker": None,
                "displayName": str(asset or ""),
                "marketValueKrw": None,
                "warnings": [],
                "errors": [str(exc)],
            }
        row["rowIndex"] = index
        ticker = row.get("resolvedTicker")
        if ticker:
            if ticker in seen:
                row.setdefault("errors", []).append(f"중복 자산입니다: {display_name(ticker)}")
            seen[ticker] = index
        if row.get("errors"):
            errors.extend(f"{row.get('displayName') or asset}: {error}" for error in row["errors"])
        if row.get("warnings"):
            warnings.extend(f"{row.get('displayName') or asset}: {warning}" for warning in row["warnings"])
        value = row.get("marketValueKrw")
        if isinstance(value, (int, float)):
            total_value += float(value)
        rows.append(row)

    if total_value <= 0:
        errors.append("총 평가액이 0원입니다.")

    for row in rows:
        value = row.get("marketValueKrw")
        row["weightPct"] = (float(value) / total_value * 100.0) if total_value > 0 and isinstance(value, (int, float)) else None
        if isinstance(row.get("weightPct"), (int, float)) and row["weightPct"] > 50:
            row.setdefault("warnings", []).append("단일 자산 비중이 50%를 초과합니다.")

    analysis_rows = [
        {"ticker": row["resolvedTicker"], "weight_pct": row["weightPct"]}
        for row in rows
        if row.get("resolvedTicker") and isinstance(row.get("weightPct"), (int, float)) and row["weightPct"] > 0
    ]
    non_cash_analysis_rows = [row for row in analysis_rows if row.get("ticker") != "__CASH__"]
    if not non_cash_analysis_rows:
        errors.append("현금 단독 입력은 헷지 분석 기준으로 사용할 수 없습니다.")
    elif len(non_cash_analysis_rows) > 1 or len(analysis_rows) > 1:
        try:
            validate_portfolio_weights(analysis_rows)
        except ValueError as exc:
            errors.append(str(exc))
    return {
        "ok": not errors,
        "canRunAnalysis": not errors and total_value > 0,
        "dataVersion": data_version,
        "totalMarketValueKrw": total_value,
        "rows": rows,
        "analysisRows": analysis_rows,
        "portfolioInputFingerprint": portfolio_fingerprint_from_weight_rows(analysis_rows),
        "errors": errors,
        "warnings": warnings,
    }


def manifest_artifact_status(manifest):
    rows = []
    for key, value in (manifest.get("artifacts", {}) if isinstance(manifest, dict) else {}).items():
        path = resolve_any_artifact(value)
        rows.append({"key": key, "path": value, "exists": bool(path), "resolvedPath": str(path) if path else None})
    return rows


def active_backtest_price_gap_summary(manifest):
    path = resolve_product_artifact(manifest, "backtestCsv", OUTPUT_VALIDATION_DIR)
    if not path:
        return {"outOfPriceRangeRows": 0, "caseNames": []}
    rows = read_csv_rows(path)
    gap_rows = [row for row in rows if str(row.get("price_window_status") or "").upper() == "OUT_OF_PRICE_RANGE"]
    case_names = unique_case_labels(gap_rows)
    return {"outOfPriceRangeRows": len(gap_rows), "caseNames": case_names}


def parse_weight_float(value):
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def portfolio_fingerprint_from_weight_rows(rows, path=None):
    weights = {}
    for row in rows or []:
        ticker = str(row.get("ticker") or "").strip()
        weight = parse_weight_float(row.get("weight_pct"))
        if ticker and weight is not None:
            weights[ticker] = weights.get(ticker, 0.0) + weight
    total = sum(max(0.0, weight) for weight in weights.values())
    if total <= 0:
        return None
    normalized = {
        ticker: round(max(0.0, weight) / total * 100.0, PORTFOLIO_FINGERPRINT_DIGITS)
        for ticker, weight in sorted(weights.items())
        if max(0.0, weight) > 0
    }
    canonical = "|".join(f"{ticker}:{weight:.{PORTFOLIO_FINGERPRINT_DIGITS}f}" for ticker, weight in normalized.items())
    return {
        "hash": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "ticker_count": len(normalized),
        "total_weight_pct": round(sum(normalized.values()), PORTFOLIO_FINGERPRINT_DIGITS),
        "tickers": list(normalized),
        "path": str(Path(path)) if path else None,
    }


def _optional_number(value):
    if value in (None, ""):
        return None
    try:
        number = float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def normalize_portfolio_api_payload(payload):
    payload = payload or {}
    name = str(payload.get("name") or payload.get("portfolioName") or "").strip()
    if not name:
        raise ValueError("portfolio name is required")
    raw_assets = payload.get("assets") or payload.get("portfolioRows") or []
    if not isinstance(raw_assets, list) or not raw_assets:
        raise ValueError("portfolio assets are required")

    prepared = []
    for raw in raw_assets:
        if not isinstance(raw, dict):
            continue
        raw_ticker = raw.get("ticker") or raw.get("asset") or raw.get("symbol") or raw.get("code") or raw.get("name")
        ticker = resolve_asset_query(raw_ticker)
        if not ticker:
            continue
        quantity = _optional_number(raw.get("quantity") if "quantity" in raw else raw.get("qty"))
        avg_price = _optional_number(
            raw.get("avgPrice")
            if "avgPrice" in raw
            else raw.get("avg_price")
            if "avg_price" in raw
            else raw.get("cost")
            if "cost" in raw
            else raw.get("price")
        )
        weight = _optional_number(raw.get("weightPct") if "weightPct" in raw else raw.get("weight"))
        amount_krw = _optional_number(raw.get("amountKrw") or raw.get("marketValueKrw") or raw.get("valueKrw"))
        value_basis = None
        if amount_krw and amount_krw > 0:
            value_basis = amount_krw
        elif quantity and quantity > 0 and avg_price and avg_price > 0:
            value_basis = quantity * avg_price
        elif weight and weight > 0:
            value_basis = weight
        prepared.append(
            {
                "ticker": ticker,
                "name": str(raw.get("name") or raw.get("assetName") or raw.get("label") or ticker).strip(),
                "quantity": quantity,
                "avgPrice": avg_price,
                "currency": str(raw.get("currency") or "").strip().upper() or None,
                "weight": weight,
                "_valueBasis": value_basis,
            }
        )

    if not prepared:
        raise ValueError("portfolio must contain at least one recognized asset")
    weights_are_usable = all((asset.get("weight") or 0) > 0 for asset in prepared)
    if not weights_are_usable:
        total_basis = sum((asset.get("_valueBasis") or 0) for asset in prepared)
        equal_weight = 100.0 / len(prepared)
        for asset in prepared:
            basis = asset.get("_valueBasis") or 0
            asset["weight"] = (basis / total_basis * 100.0) if total_basis > 0 else equal_weight

    assets = [
        {
            "ticker": asset["ticker"],
            "name": asset.get("name") or asset["ticker"],
            "quantity": asset.get("quantity"),
            "avgPrice": asset.get("avgPrice"),
            "currency": asset.get("currency"),
            "weight": round(float(asset.get("weight") or 0), PORTFOLIO_FINGERPRINT_DIGITS),
        }
        for asset in prepared
    ]
    fingerprint = portfolio_fingerprint_from_weight_rows(
        [{"ticker": asset["ticker"], "weight_pct": asset["weight"]} for asset in assets]
    )
    if not fingerprint:
        raise ValueError("portfolio weights could not be normalized")
    normalized = {
        "purpose": str(payload.get("purpose") or "").strip(),
        "totalValue": _optional_number(payload.get("totalValue") or payload.get("totalValueKrw")) or 0,
        "returnRate": _optional_number(payload.get("returnRate")) or 0,
        "riskLevel": str(payload.get("riskLevel") or "Moderate"),
        "status": str(payload.get("status") or "server"),
        "assets": assets,
        "portfolioInputFingerprint": fingerprint,
    }
    return {
        "name": name[:120],
        "portfolioHash": fingerprint["hash"],
        "normalizedInput": normalized,
        "assets": assets,
    }


def portfolio_record_to_run_payload(portfolio, extra=None):
    rows = []
    total_value = _optional_number((portfolio or {}).get("totalValue")) or 0
    for asset in (portfolio or {}).get("assets") or []:
        ticker = resolve_asset_query(asset.get("ticker"))
        if not ticker:
            continue
        row = {"asset": ticker, "ticker": ticker}
        quantity = _optional_number(asset.get("quantity") if asset.get("quantity") is not None else asset.get("qty"))
        weight = _optional_number(asset.get("weightPct") if asset.get("weightPct") is not None else asset.get("weight"))
        if quantity and quantity > 0:
            row["quantity"] = quantity
        elif total_value and weight and weight > 0:
            row["amountKrw"] = round(total_value * weight / 100.0)
        else:
            row["amountKrw"] = max(1, round((weight or 100.0 / max(1, len((portfolio or {}).get("assets") or []))) * 1000))
        rows.append(row)
    payload = {
        "mode": "portfolio",
        "portfolioRows": rows,
        "maxComboSize": 2,
        "forceReanalysis": True,
        "ignoreAnalysisCache": True,
    }
    payload.update(extra or {})
    return payload


def run_row_response(row):
    if not row:
        return None
    return {
        "id": str(row.get("id")),
        "runId": row.get("run_id"),
        "portfolioId": str(row.get("portfolio_id")),
        "portfolioHash": row.get("portfolio_hash"),
        "status": row.get("status"),
        "artifactDir": row.get("artifact_dir"),
        "dataVersion": row.get("data_version"),
        "startedAt": row.get("started_at"),
        "finishedAt": row.get("finished_at"),
        "errorMessage": row.get("error_message"),
        "createdAt": row.get("created_at"),
    }


def current_portfolio_fingerprint(path=None):
    path = path or INPUT_DIR / "portfolio_weights.csv"
    if not path or not Path(path).exists():
        return None
    with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
        return portfolio_fingerprint_from_weight_rows(csv.DictReader(f), path=path)


def normalize_ticker_list(tickers):
    return sorted(
        {
            str(ticker or "").strip().upper()
            for ticker in (tickers or [])
            if str(ticker or "").strip()
        }
    )


def manifest_portfolio_fingerprint(manifest, bundle):
    payload = bundle.get("portfolio_input_fingerprint") if isinstance(bundle, dict) else None
    if not isinstance(payload, dict):
        payload = manifest.get("portfolio_input_fingerprint") if isinstance(manifest, dict) else None
    return payload if isinstance(payload, dict) else None


def bundle_portfolio_fingerprint(bundle):
    payload = bundle.get("portfolio_input_fingerprint") if isinstance(bundle, dict) else None
    return payload if isinstance(payload, dict) else None


def active_bundle_ticker_list(manifest, bundle=None):
    bundle = bundle if isinstance(bundle, dict) else active_bundle(manifest)
    fingerprint = bundle_portfolio_fingerprint(bundle) or manifest_portfolio_fingerprint(manifest, bundle)
    tickers = []
    if isinstance(fingerprint, dict):
        tickers = fingerprint.get("tickers") or []
    if not tickers:
        tickers = bundle.get("portfolioTickers") or bundle.get("portfolio_tickers") or manifest.get("portfolioTickers") or []
    return normalize_ticker_list(tickers)


def active_bundle_missing_artifacts(manifest, required_keys=REQUIRED_PRODUCT_ARTIFACT_KEYS, include_declared=False):
    artifacts = manifest.get("artifacts", {}) if isinstance(manifest, dict) else {}
    artifacts = artifacts if isinstance(artifacts, dict) else {}
    missing = []
    for key in required_keys:
        raw_path = artifacts.get(key)
        if not raw_path:
            missing.append({"key": key, "path": raw_path, "exists": False, "reason": "missing_manifest_entry"})
            continue
        resolved = resolve_any_artifact(raw_path)
        if not resolved:
            missing.append({"key": key, "path": raw_path, "exists": False, "reason": "missing_file"})
    if include_declared:
        for row in manifest_artifact_status(manifest):
            if not row.get("exists") and row.get("key") not in {item["key"] for item in missing}:
                missing.append({**row, "reason": "missing_declared_file"})
    return missing


def validate_active_bundle_for_request(run_id, prepared_request):
    manifest = read_product_manifest()
    bundle = active_bundle(manifest)
    expected_tickers = normalize_ticker_list(prepared_request.get("portfolioTickers") or [])
    expected_sha = prepared_request.get("portfolioInputSha256")
    expected_fingerprint_hash = prepared_request.get("portfolioInputFingerprintHash")
    bundle_fingerprint = bundle_portfolio_fingerprint(bundle)
    manifest_fingerprint = manifest.get("portfolio_input_fingerprint") if isinstance(manifest, dict) else None
    active_fingerprint = bundle_fingerprint or manifest_portfolio_fingerprint(manifest, bundle)
    active_tickers = active_bundle_ticker_list(manifest, bundle)
    errors = []

    if not manifest:
        errors.append("latest_manifest.json is missing")
    if not bundle:
        errors.append("latest_manifest.active_bundle is missing")
    if manifest.get("active_hedgemate_run") != run_id:
        errors.append(
            f"latest_manifest.active_hedgemate_run={manifest.get('active_hedgemate_run')!r} does not match runId={run_id!r}"
        )
    if bundle.get("hedgemate_run") != run_id:
        errors.append(
            f"latest_manifest.active_bundle.hedgemate_run={bundle.get('hedgemate_run')!r} does not match runId={run_id!r}"
        )

    if expected_fingerprint_hash:
        active_hash = bundle_fingerprint.get("hash") if isinstance(bundle_fingerprint, dict) else None
        if active_hash != expected_fingerprint_hash:
            errors.append(
                "latest_manifest.active_bundle.portfolio_input_fingerprint.hash="
                f"{active_hash!r} does not match requested portfolio fingerprint={expected_fingerprint_hash!r}"
            )
        manifest_hash = manifest_fingerprint.get("hash") if isinstance(manifest_fingerprint, dict) else None
        if manifest_hash and manifest_hash != expected_fingerprint_hash:
            errors.append(
                "latest_manifest.portfolio_input_fingerprint.hash="
                f"{manifest_hash!r} does not match requested portfolio fingerprint={expected_fingerprint_hash!r}"
            )
    else:
        errors.append("requested portfolio fingerprint is missing")

    if expected_sha:
        active_sha = bundle.get("portfolioInputSha256")
        if active_sha != expected_sha:
            errors.append(f"active bundle portfolioInputSha256={active_sha!r} does not match requested input sha={expected_sha!r}")
        manifest_sha = manifest.get("portfolioInputSha256") if isinstance(manifest, dict) else None
        if manifest_sha and manifest_sha != expected_sha:
            errors.append(f"latest_manifest portfolioInputSha256={manifest_sha!r} does not match requested input sha={expected_sha!r}")
    else:
        errors.append("requested portfolio input sha256 is missing")

    if expected_tickers and active_tickers != expected_tickers:
        errors.append(f"active bundle tickers={active_tickers!r} do not match requested tickers={expected_tickers!r}")
    elif not expected_tickers:
        errors.append("requested portfolio ticker list is missing")

    missing_artifacts = active_bundle_missing_artifacts(manifest)
    if missing_artifacts:
        errors.append("missing required active artifacts: " + ", ".join(row["key"] for row in missing_artifacts))

    return {
        "ok": not errors,
        "errors": errors,
        "runId": run_id,
        "expectedTickers": expected_tickers,
        "activeTickers": active_tickers,
        "expectedPortfolioInputSha256": expected_sha,
        "activePortfolioInputSha256": bundle.get("portfolioInputSha256"),
        "expectedPortfolioFingerprintHash": expected_fingerprint_hash,
        "activePortfolioFingerprintHash": bundle_fingerprint.get("hash") if isinstance(bundle_fingerprint, dict) else None,
        "missingArtifacts": missing_artifacts,
    }


def should_compare_current_portfolio_input(active_portfolio, current_path=None):
    current_path = Path(current_path or INPUT_DIR / "portfolio_weights.csv")
    if not current_path.exists():
        return False
    if not isinstance(active_portfolio, dict):
        return True
    active_path_raw = active_portfolio.get("path")
    if not active_path_raw:
        return True
    active_path = resolve_any_artifact(active_path_raw)
    if not active_path or not active_path.exists():
        return True
    if active_path.resolve() == current_path.resolve():
        return True
    return current_path.stat().st_mtime > active_path.stat().st_mtime


def active_scenario_snapshot_metadata(manifest, bundle):
    scenario_run = bundle.get("scenario_run") or manifest.get("active_scenario_run")
    if not scenario_run:
        return {}
    metadata_path = SCENARIO_REPORT_DIR / f"scenario_snapshot_metadata_{scenario_run}.json"
    payload = read_json(metadata_path, {}) if metadata_path.exists() else {}
    return payload if isinstance(payload, dict) else {}


def parse_iso_datetime(value, default_tz=KST):
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=default_tz)
    return parsed


def current_intraday_anchor_kst(reference_dt=None, bucket_hours=3):
    reference = reference_dt or datetime.now(KST)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=KST)
    else:
        reference = reference.astimezone(KST)
    anchor_hour = (reference.hour // bucket_hours) * bucket_hours
    return reference.replace(hour=anchor_hour, minute=0, second=0, microsecond=0)


def latest_intraday_nowcast_status(reference_dt=None):
    anchor = current_intraday_anchor_kst(reference_dt=reference_dt)
    metadata_path = latest_path(SCENARIO_REPORT_DIR, "intraday_nowcast_metadata_*.json")
    metadata = read_json(metadata_path, {}) if metadata_path else {}
    if not isinstance(metadata, dict):
        metadata = {}
    vector_path = resolve_any_artifact(metadata.get("vector_json_path"), default_dir=SCENARIO_NOWCAST_DIR) if metadata.get("vector_json_path") else latest_path(
        SCENARIO_NOWCAST_DIR,
        "current_intraday_nowcast_*.json",
    )
    vector_rows = read_json(vector_path, []) if vector_path and Path(vector_path).exists() else []
    latest_timestamp = metadata.get("latest_timestamp_kst")
    if not latest_timestamp and isinstance(vector_rows, list) and vector_rows:
        latest_timestamp = vector_rows[0].get("as_of_kst")
    latest_dt = parse_iso_datetime(latest_timestamp)
    return {
        "fresh": bool(latest_dt and latest_dt >= anchor),
        "latestTimestampKst": latest_dt.isoformat() if latest_dt else None,
        "requiredAnchorKst": anchor.isoformat(),
        "bucketHours": 3,
        "interval": metadata.get("interval") or None,
        "dataVersion": metadata.get("data_version") or metadata.get("dataVersion") or None,
        "metadataPath": (artifact_rel_from_path(metadata_path) or str(metadata_path)) if metadata_path else None,
        "vectorPath": (artifact_rel_from_path(vector_path) or str(vector_path)) if vector_path else None,
        "nowcastCount": len(vector_rows) if isinstance(vector_rows, list) else None,
    }


def current_intraday_news_anchor_kst(reference_dt=None):
    reference = reference_dt or datetime.now(KST)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=KST)
    else:
        reference = reference.astimezone(KST)
    allowed = [hour for hour in INTRADAY_NEWS_REFRESH_HOURS_KST if hour <= reference.hour]
    if allowed:
        return reference.replace(hour=max(allowed), minute=0, second=0, microsecond=0)
    previous_day = reference - timedelta(days=1)
    return previous_day.replace(hour=max(INTRADAY_NEWS_REFRESH_HOURS_KST), minute=0, second=0, microsecond=0)


def latest_intraday_news_metadata_path():
    return latest_path(SCENARIO_NEWS_INTRADAY_DIR, "news_overlay_metadata_*.json")


def load_intraday_news_top5(metadata=None):
    metadata = metadata if isinstance(metadata, dict) else {}
    paths = metadata.get("paths") if isinstance(metadata.get("paths"), dict) else {}
    top5_path = paths.get("top5") or metadata.get("top5_path")
    if top5_path:
        top5_path = Path(top5_path)
    else:
        top5_path = latest_path(SCENARIO_NEWS_INTRADAY_DIR, "news_top5_*.json")
    payload = read_json(top5_path, {}) if top5_path and Path(top5_path).exists() else {}
    items = payload.get("items") if isinstance(payload, dict) else payload if isinstance(payload, list) else []
    if not isinstance(items, list):
        items = []
    return items[:5], Path(top5_path) if top5_path else None


def latest_intraday_news_overlay_status(reference_dt=None):
    anchor = current_intraday_news_anchor_kst(reference_dt=reference_dt)
    metadata_path = latest_intraday_news_metadata_path()
    metadata = read_json(metadata_path, {}) if metadata_path else {}
    if not isinstance(metadata, dict):
        metadata = {}
    top5, top5_path = load_intraday_news_top5(metadata)
    refresh_window = parse_iso_datetime(metadata.get("refresh_window_kst"))
    generated_at = parse_iso_datetime(metadata.get("generated_at_kst") or metadata.get("generated_at"))
    return {
        "fresh": bool(metadata.get("status") == "success" and refresh_window and refresh_window.astimezone(KST) >= anchor),
        "status": metadata.get("status") or ("missing" if not metadata else "unknown"),
        "runId": metadata.get("run_id"),
        "jobType": metadata.get("job_type") or INTRADAY_NEWS_JOB_TYPE,
        "latestTimestampKst": generated_at.astimezone(KST).isoformat() if generated_at else None,
        "requiredWindowKst": anchor.isoformat(),
        "refreshWindowKst": refresh_window.astimezone(KST).isoformat() if refresh_window else None,
        "allowedRefreshHoursKst": list(INTRADAY_NEWS_REFRESH_HOURS_KST),
        "provider": metadata.get("provider"),
        "fallbackUsed": bool(metadata.get("fallback_used")),
        "fallbackReason": metadata.get("fallback_reason"),
        "geminiModel": metadata.get("gemini_model"),
        "geminiKeySource": metadata.get("gemini_key_source"),
        "top5Count": len(top5),
        "metadataPath": str(metadata_path) if metadata_path else None,
        "top5Path": str(top5_path) if top5_path else None,
        "marketStateUsage": metadata.get("market_state_usage") or "intraday_explanatory_overlay_only",
        "reportRecommendationUsage": metadata.get("report_recommendation_usage") or "disabled",
    }


def raw_market_snapshot_status(raw_path, expected_date):
    if not raw_path or not Path(raw_path).exists():
        return None
    _, latest_by_ticker = read_raw_market_rows(raw_path)
    dates = [value for value in latest_by_ticker.values() if value]
    universe_tickers = [
        str(row.get("ticker") or "").strip()
        for row in universe_asset_rows()
        if str(row.get("ticker") or "").strip() and str(row.get("ticker") or "").strip() != "__CASH__"
    ]
    stale_tickers = [ticker for ticker in universe_tickers if latest_by_ticker.get(ticker, "") < expected_date]
    coverage_ratio = (len(universe_tickers) - len(stale_tickers)) / len(universe_tickers) if universe_tickers else None
    return {
        "oldestMarketDate": min(dates) if dates else None,
        "latestMarketDate": max(dates) if dates else None,
        "maxMarketDate": max(dates) if dates else None,
        "failedTickers": [],
        "staleTickers": stale_tickers,
        "tickerCoverageRatio": coverage_ratio,
        "totalTickers": len(universe_tickers),
        "outputRows": len(latest_by_ticker),
    }


def write_raw_market_snapshot_manifest(raw_path, data_version, status, expected_date):
    if not raw_path or not data_version or not status:
        return None
    path = OUTPUT_RAW_DIR / f"raw_market_daily_{data_version}_snapshot_status.json"
    payload = {
        "manifestVersion": "raw_market_snapshot_v1",
        "dataVersion": data_version,
        "outputSnapshot": str(raw_path),
        "targetLatestMarketDate": expected_date,
        "oldestMarketDate": status.get("oldestMarketDate"),
        "latestMarketDate": status.get("latestMarketDate"),
        "maxMarketDate": status.get("maxMarketDate"),
        "failedTickers": status.get("failedTickers") or [],
        "staleTickers": status.get("staleTickers") or [],
        "tickerCoverageRatio": status.get("tickerCoverageRatio"),
        "totalTickers": status.get("totalTickers"),
        "outputTickers": status.get("outputRows"),
        "generatedAtUtc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    try:
        write_text_atomic(path, json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        return None
    return path


def is_market_data_refresh_attempt_manifest(manifest):
    manifest = manifest or {}
    return (
        manifest.get("manifestVersion") == "raw_market_incremental_v1"
        or manifest.get("refreshMode") == "market_data_only"
    )


def market_data_refresh_attempt_was_critical(manifest):
    manifest = manifest or {}
    status = str(manifest.get("status") or manifest.get("refreshStatus") or "").strip().lower()
    if manifest.get("criticalFailure") or status in {"failed", "error", "critical_failure"}:
        return True
    failed_tickers = manifest.get("failedTickers") or []
    total_tickers = manifest.get("totalTickers")
    try:
        total_tickers = int(total_tickers)
    except (TypeError, ValueError):
        total_tickers = 0
    try:
        coverage_ratio = float(manifest.get("tickerCoverageRatio"))
    except (TypeError, ValueError):
        coverage_ratio = None
    if total_tickers > 0 and len(failed_tickers) >= total_tickers and not manifest.get("latestMarketDate"):
        return True
    if total_tickers > 0 and coverage_ratio == 0 and not manifest.get("latestMarketDate"):
        return True
    return False


def market_data_refresh_attempt_status(manifest, expected_date, reference_date=None):
    manifest = manifest or {}
    reference_date = reference_date or datetime.now(KST).date()
    if isinstance(reference_date, datetime):
        reference_day = reference_date.astimezone(KST).date() if reference_date.tzinfo else reference_date.date()
    else:
        reference_day = reference_date
    generated_at = manifest.get("generatedAtUtc")
    generated_dt = parse_iso_datetime(generated_at, default_tz=timezone.utc)
    generated_day = generated_dt.astimezone(KST).date() if generated_dt else None
    target_latest_date = str(manifest.get("targetLatestMarketDate") or "")
    reaches_target = bool(expected_date and target_latest_date and target_latest_date >= expected_date)
    critical = market_data_refresh_attempt_was_critical(manifest)
    attempted = bool(
        is_market_data_refresh_attempt_manifest(manifest)
        and reaches_target
        and generated_day == reference_day
        and not critical
    )
    return {
        "marketDataRefreshAttempted": attempted,
        "marketDataRefreshAttemptedAtUtc": generated_at or None,
        "marketDataRefreshAttemptTargetLatestMarketDate": target_latest_date or None,
        "marketDataRefreshAttemptCritical": critical,
    }


def data_version_value(value):
    text = str(value or "").strip()
    return int(text) if re.fullmatch(r"\d{8}", text) else None


def is_newer_data_version(candidate, baseline):
    candidate_value = data_version_value(candidate)
    baseline_value = data_version_value(baseline)
    return candidate_value is not None and baseline_value is not None and candidate_value > baseline_value


def market_coverage_is_fresh(coverage_ratio):
    if coverage_ratio in (None, ""):
        return True
    try:
        return float(coverage_ratio) >= MARKET_DATA_FRESH_COVERAGE_THRESHOLD
    except (TypeError, ValueError):
        return False


def daily_market_state_run_ids(data_version):
    stamp = str(data_version or datetime.now(KST).strftime("%Y%m%d")).strip()
    return f"scenario-refresh-{stamp}", f"final-refresh-{stamp}"


def max_csv_date(path):
    if not path or not Path(path).exists():
        return None
    dates = []
    try:
        with Path(path).open("r", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                value = str(row.get("date") or row.get("as_of_date") or "").strip()
                if value:
                    dates.append(value[:10])
    except OSError:
        return None
    return max(dates) if dates else None


def scenario_final_output_status(data_version=None, expected_date=None):
    scenario_run, final_run = daily_market_state_run_ids(data_version)
    manifest = read_active_manifest()
    final_path = SCENARIO_FINAL_DIR / f"final_market_state_daily_{final_run}.csv"
    top_path = SCENARIO_FINAL_DIR / f"top_active_scenarios_{final_run}.json"
    confidence_path = SCENARIO_FINAL_DIR / f"scenario_confidence_{final_run}.csv"
    metadata_path = SCENARIO_REPORT_DIR / f"final_market_state_metadata_{final_run}.json"
    vector_path = SCENARIO_VECTOR_DIR / f"current_scenario_vector_{final_run}.json"
    top_payload = read_json(top_path, {}) if top_path.exists() else {}
    metadata = read_json(metadata_path, {}) if metadata_path.exists() else {}
    data_as_of_date = (
        str(top_payload.get("date") or metadata.get("date") or "").strip()
        or max_csv_date(final_path)
    )
    exists = all(path.exists() for path in (final_path, top_path, confidence_path, metadata_path))
    reaches_expected_date = not expected_date or (bool(data_as_of_date) and str(data_as_of_date) >= str(expected_date))
    active_run = scenario_manifest_final_run_id(manifest)
    fresh = bool(exists and reaches_expected_date and active_run == final_run)
    return {
        "fresh": fresh,
        "exists": exists,
        "scenarioRunId": scenario_run,
        "finalRunId": final_run,
        "activeFinalRunId": active_run,
        "dataAsOfDate": data_as_of_date or None,
        "expectedDate": expected_date,
        "finalPath": str(final_path),
        "topActiveScenariosPath": str(top_path),
        "confidencePath": str(confidence_path),
        "metadataPath": str(metadata_path),
        "vectorPath": str(vector_path),
    }


def latest_market_cache_status(data_version=None, reference_date=None):
    expected_date = expected_latest_market_date(reference_date)
    manifest_path, cache_manifest = latest_raw_market_manifest(OUTPUT_RAW_DIR)
    raw_path = raw_market_path_for_data_version(data_version)
    manifest_data_version = str(cache_manifest.get("dataVersion") or "") if cache_manifest else ""
    requested_data_version = str(data_version or "")
    should_use_raw_snapshot = bool(
        raw_path
        and raw_path.exists()
        and requested_data_version
        and (
            not cache_manifest
            or (
                data_version_value(manifest_data_version) is not None
                and data_version_value(requested_data_version) is not None
                and data_version_value(manifest_data_version) < data_version_value(requested_data_version)
            )
        )
    )
    snapshot_status = raw_market_snapshot_status(raw_path, expected_date) if should_use_raw_snapshot else None
    if snapshot_status:
        oldest_market_date = snapshot_status.get("oldestMarketDate")
        latest_market_date = snapshot_status.get("latestMarketDate")
        max_market_date = snapshot_status.get("maxMarketDate")
        failed_tickers = snapshot_status.get("failedTickers") or []
        stale_tickers = snapshot_status.get("staleTickers") or []
        coverage_ratio = snapshot_status.get("tickerCoverageRatio")
        manifest_path = write_raw_market_snapshot_manifest(raw_path, str(data_version), snapshot_status, expected_date)
        manifest_data_version = data_version
    elif cache_manifest:
        max_market_date = cache_manifest.get("maxMarketDate") or cache_manifest.get("latestMarketDate")
        latest_market_date = max_market_date
        oldest_market_date = cache_manifest.get("oldestMarketDate") or cache_manifest.get("latestMarketDate")
        failed_tickers = cache_manifest.get("failedTickers") or []
        stale_tickers = cache_manifest.get("staleTickers") or []
        coverage_ratio = cache_manifest.get("tickerCoverageRatio")
        output_snapshot = cache_manifest.get("outputSnapshot")
        if output_snapshot:
            candidate = Path(str(output_snapshot))
            if candidate.exists():
                raw_path = candidate
    else:
        oldest_market_date = None
        latest_market_date = None
        max_market_date = None
        failed_tickers = []
        stale_tickers = []
        coverage_ratio = None
        manifest_data_version = None
    if not latest_market_date and raw_path and raw_path.exists():
        snapshot_status = raw_market_snapshot_status(raw_path, expected_date)
        oldest_market_date = snapshot_status.get("oldestMarketDate") if snapshot_status else None
        latest_market_date = snapshot_status.get("latestMarketDate") if snapshot_status else None
        max_market_date = snapshot_status.get("maxMarketDate") if snapshot_status else None
        failed_tickers = snapshot_status.get("failedTickers") if snapshot_status else []
        stale_tickers = snapshot_status.get("staleTickers") if snapshot_status else []
        coverage_ratio = snapshot_status.get("tickerCoverageRatio") if snapshot_status else None
    market_data_fresh = bool(
        latest_market_date
        and latest_market_date >= expected_date
        and market_coverage_is_fresh(coverage_ratio)
    )
    attempt_status = market_data_refresh_attempt_status(cache_manifest, expected_date, reference_date=reference_date)
    return {
        "marketDataFresh": market_data_fresh,
        **attempt_status,
        "oldestMarketDate": oldest_market_date,
        "latestMarketDate": latest_market_date,
        "maxMarketDate": max_market_date,
        "expectedLatestMarketDate": expected_date,
        "marketDataManifestPath": str(manifest_path) if manifest_path else None,
        "marketDataVersion": manifest_data_version or data_version,
        "rawMarketPath": str(raw_path) if raw_path else None,
        "failedTickers": failed_tickers,
        "staleTickers": stale_tickers,
        "tickerCoverageRatio": coverage_ratio,
    }


def load_data_freshness(reference_date=None, manifest=None):
    reference_date = reference_date or datetime.now(KST).date()
    manifest = manifest if manifest is not None else read_product_manifest()
    bundle = active_bundle(manifest)
    data_version = active_data_version(manifest)
    data_date = None
    if re.fullmatch(r"\d{8}", data_version or ""):
        data_date = datetime.strptime(data_version, "%Y%m%d").date()
    status = manifest.get("freshness_status") or bundle.get("freshness_status") or "UNKNOWN"
    artifact_rows = manifest_artifact_status(manifest)
    missing = [row for row in artifact_rows if not row["exists"]]
    price_gap_summary = active_backtest_price_gap_summary(manifest)
    active_portfolio = manifest_portfolio_fingerprint(manifest, bundle)
    current_portfolio_path = INPUT_DIR / "portfolio_weights.csv"
    current_portfolio = current_portfolio_fingerprint(current_portfolio_path)
    compare_current_portfolio = should_compare_current_portfolio_input(active_portfolio, current_portfolio_path)
    portfolio_input_mismatch = bool(
        compare_current_portfolio
        and active_portfolio
        and current_portfolio
        and active_portfolio.get("hash")
        and current_portfolio.get("hash")
        and active_portfolio.get("hash") != current_portfolio.get("hash")
    )
    recommendation_portfolio_mismatch = bool(manifest.get("portfolio_input_mismatch") or bundle.get("portfolio_input_mismatch"))
    scenario_as_of = bundle.get("scenario_vector_as_of_date") or manifest.get("scenario_vector_as_of_date")
    scenario_snapshot = active_scenario_snapshot_metadata(manifest, bundle)
    scenario_data_version = str(scenario_snapshot.get("data_version") or "").strip()
    scenario_date = None
    if scenario_as_of:
        try:
            scenario_date = datetime.strptime(str(scenario_as_of)[:10], "%Y-%m-%d").date()
        except ValueError:
            scenario_date = None
    scenario_lag_days = (data_date - scenario_date).days if data_date and scenario_date else None
    scenario_version_mismatch = bool(data_version and scenario_data_version and scenario_data_version != data_version)
    market_cache = latest_market_cache_status(data_version=data_version, reference_date=reference_date)
    scenario_final = scenario_final_output_status(
        data_version=market_cache.get("marketDataVersion") or data_version,
        expected_date=market_cache.get("expectedLatestMarketDate"),
    )
    intraday_status = latest_intraday_nowcast_status()
    market_data_fresh = bool(market_cache.get("marketDataFresh"))
    market_cache_data_version = str(market_cache.get("marketDataVersion") or "").strip()
    active_bundle_older_than_market_cache = is_newer_data_version(market_cache_data_version, data_version)
    needs_refresh = (
        (not market_data_fresh)
        or status != "FRESH"
        or bool(missing)
        or price_gap_summary["outOfPriceRangeRows"] > 0
        or scenario_version_mismatch
        or active_bundle_older_than_market_cache
        or portfolio_input_mismatch
        or recommendation_portfolio_mismatch
    )
    reasons = list(manifest.get("stale_reasons") or bundle.get("stale_reasons") or [])
    def add_reason(text):
        if text and text not in reasons:
            reasons.append(text)

    if not market_data_fresh:
        add_reason(
            "market data latest date "
            f"{market_cache.get('latestMarketDate') or '-'} is older than expected "
            f"{market_cache.get('expectedLatestMarketDate') or '-'}"
        )
    if scenario_version_mismatch:
        add_reason(
            f"scenario data_version {scenario_data_version} does not match active data_version {data_version}"
        )
    if active_bundle_older_than_market_cache:
        add_reason(
            f"active analysis bundle data_version {data_version} is older than market data cache {market_cache_data_version}"
        )
    if missing:
        add_reason("missing artifacts: " + ", ".join(row["key"] for row in missing))
    if price_gap_summary["outOfPriceRangeRows"] > 0:
        names = ", ".join(price_gap_summary["caseNames"][:3])
        add_reason(
            f"historical stress price coverage gap: {price_gap_summary['outOfPriceRangeRows']} rows"
            + (f" ({names})" if names else "")
        )
    if portfolio_input_mismatch:
        add_reason("portfolio input mismatch: current portfolio_weights.csv differs from the active bundle")
    if recommendation_portfolio_mismatch:
        if not any(str(reason).startswith("portfolio input mismatch: active recommendation weights") for reason in reasons):
            add_reason("portfolio input mismatch: active recommendation weights do not match the active portfolio input")
    return {
        "status": "current" if not needs_refresh else "stale",
        "needsRefresh": needs_refresh,
        "skipHeavyRefresh": not needs_refresh,
        "referenceDate": reference_date.isoformat(),
        "dataVersion": data_version,
        "scenarioDataVersion": scenario_data_version or None,
        "scenarioVectorAsOfDate": scenario_as_of,
        "scenarioVectorLagDays": scenario_lag_days,
        "scenarioAnchorCoverageRatio": scenario_snapshot.get("anchor_ticker_coverage_ratio"),
        "scenarioDataQualityStatus": scenario_snapshot.get("data_quality_status"),
        "scenarioFinalFresh": scenario_final.get("fresh"),
        "scenarioFinalRunId": scenario_final.get("finalRunId"),
        "activeScenarioFinalRunId": scenario_final.get("activeFinalRunId"),
        "scenarioFinalDataAsOfDate": scenario_final.get("dataAsOfDate"),
        "expectedScenarioFinalDataAsOfDate": scenario_final.get("expectedDate"),
        "generatedAtUtc": bundle.get("generated_at_utc") or manifest.get("generated_at_utc"),
        "freshnessStatus": status,
        "marketDataFresh": market_data_fresh,
        "marketDataRefreshAttempted": market_cache.get("marketDataRefreshAttempted"),
        "marketDataRefreshAttemptedAtUtc": market_cache.get("marketDataRefreshAttemptedAtUtc"),
        "marketDataRefreshAttemptTargetLatestMarketDate": market_cache.get("marketDataRefreshAttemptTargetLatestMarketDate"),
        "marketDataRefreshAttemptCritical": market_cache.get("marketDataRefreshAttemptCritical"),
        "latestMarketDate": market_cache.get("latestMarketDate"),
        "oldestMarketDate": market_cache.get("oldestMarketDate"),
        "maxMarketDate": market_cache.get("maxMarketDate"),
        "expectedLatestMarketDate": market_cache.get("expectedLatestMarketDate"),
        "marketDataVersion": market_cache.get("marketDataVersion"),
        "activeBundleOlderThanMarketCache": active_bundle_older_than_market_cache,
        "marketDataManifestPath": market_cache.get("marketDataManifestPath"),
        "rawMarketPath": market_cache.get("rawMarketPath"),
        "marketDataFailedTickers": market_cache.get("failedTickers") or [],
        "marketDataStaleTickers": market_cache.get("staleTickers") or [],
        "marketDataTickerCoverageRatio": market_cache.get("tickerCoverageRatio"),
        "intradayNowcast": intraday_status,
        "intradayNowcastFresh": intraday_status.get("fresh"),
        "intradayNowcastLatestTimestampKst": intraday_status.get("latestTimestampKst"),
        "intradayNowcastRequiredAnchorKst": intraday_status.get("requiredAnchorKst"),
        "intradayNowcastInterval": intraday_status.get("interval"),
        "intradayNowcastBucketHours": intraday_status.get("bucketHours"),
        "marketDataDisplayAsOfKst": intraday_status.get("latestTimestampKst"),
        "reasons": reasons,
        "artifactStatus": artifact_rows,
        "backtestPriceGapSummary": price_gap_summary,
        "portfolioInputMismatch": portfolio_input_mismatch,
        "currentPortfolioCompared": compare_current_portfolio,
        "recommendationPortfolioMismatch": recommendation_portfolio_mismatch,
        "activePortfolioFingerprint": active_portfolio,
        "currentPortfolioFingerprint": current_portfolio,
        "eventOverlayStatus": normalized_event_overlay_status(manifest.get("event_overlay_status")),
    }


def user_facing_freshness_reasons(data_freshness):
    display_reasons = []
    for reason in (data_freshness or {}).get("reasons") or []:
        reason_text = str(reason or "").strip()
        if not reason_text:
            continue
        lower_reason = reason_text.lower()
        if lower_reason.startswith("scenario vector stale") or lower_reason.startswith("active analysis bundle data_version"):
            display_reason = "최신 시장데이터는 반영됐지만, 현재 리포트는 이전 분석 결과입니다. 포트폴리오 분석을 다시 실행하면 새 기준으로 갱신됩니다."
        elif lower_reason.startswith("market data latest date"):
            display_reason = "실시간 데이터 확인이 필요합니다."
        elif lower_reason.startswith("scenario data_version"):
            display_reason = "시나리오 데이터 상태 확인이 필요합니다."
        elif lower_reason.startswith("portfolio input mismatch"):
            display_reason = "선택 포트폴리오와 저장된 분석 결과가 달라 재분석이 필요합니다."
        else:
            display_reason = reason_text
        if display_reason not in display_reasons:
            display_reasons.append(display_reason)
    return display_reasons


def product_data_freshness_response(data_freshness):
    response = dict(data_freshness or {})
    raw_reasons = list(response.get("reasons") or [])
    display_reasons = user_facing_freshness_reasons(response)
    market_data_fresh = bool(response.get("marketDataFresh"))
    analysis_refresh_needed = bool(
        response.get("activeBundleOlderThanMarketCache")
        or str(response.get("freshnessStatus") or "").upper() == "STALE"
        or response.get("portfolioInputMismatch")
        or response.get("recommendationPortfolioMismatch")
    )
    response["reasons"] = display_reasons
    response["marketDataNeedsRefresh"] = not market_data_fresh
    response["needsAnalysisRefresh"] = analysis_refresh_needed
    if market_data_fresh and analysis_refresh_needed:
        response["needsRefresh"] = False
    return response


def resolve_manifest_artifact(manifest, key, default_dir):
    raw_path = manifest.get(f"{key}_path") or manifest.get(key)
    if not raw_path:
        return None
    candidate = Path(str(raw_path))
    if candidate.is_absolute():
        return candidate if candidate.exists() else None
    candidates = [
        SCENARIO_OUTPUT_DIR / candidate,
        Path(default_dir) / candidate,
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def final_run_id_from_filename(filename):
    name = Path(str(filename or "")).name
    m = re.search(r"final_market_state_daily_(.+)\.csv$", name)
    return m.group(1) if m else None


def scenario_manifest_final_run_id(manifest=None):
    manifest = manifest if isinstance(manifest, dict) else read_active_manifest()
    return (
        manifest.get("active_final_run")
        or final_run_id_from_filename(manifest.get("active_final_market_state"))
    )


def product_manifest_final_run_id(product_manifest=None):
    product_manifest = product_manifest if isinstance(product_manifest, dict) else read_product_manifest()
    product_bundle = active_bundle(product_manifest)
    return product_bundle.get("final_market_state_run") or product_manifest.get("active_final_run")


def latest_path(directory, pattern):
    paths = [path for path in directory.glob(pattern) if path.is_file()]
    if not paths:
        return None
    return max(paths, key=lambda path: (path.stat().st_mtime, path.name))


def latest_run_id_from_files(directory, pattern, regex):
    path = latest_path(directory, pattern)
    if not path:
        return None
    match = re.search(regex, path.name)
    return match.group(1) if match else None


def fallback_product_manifest():
    scenario_manifest = read_active_manifest()
    final_run = scenario_manifest.get("active_final_run") or final_run_id_from_filename(scenario_manifest.get("active_final_market_state"))
    scenario_run = scenario_manifest.get("active_scenario_run") or final_run
    hedge_run = latest_run_id_from_files(OUTPUT_PROCESSED_DIR, "features_summary_*.csv", r"features_summary_(.+)\.csv$")
    backtest_run = latest_run_id_from_files(OUTPUT_VALIDATION_DIR, "walk_forward_backtest_*.csv", r"walk_forward_backtest_(.+)\.csv$")
    reasons = ["active product manifest is missing; fallback discovery is not formal recommendation evidence"]
    if not final_run:
        reasons.append("시장국면 final run을 찾지 못했습니다")
    if not hedge_run:
        reasons.append("HedgeMate 추천 run을 찾지 못했습니다")
    if not backtest_run:
        reasons.append("backtest run을 찾지 못했습니다")
    status = "FRESH" if not reasons else "INCOMPLETE"
    return {
        "manifest_version": "hedgemate_active_bundle_fallback_v1",
        "freshness_status": status,
        "stale_reasons": reasons,
        "active_bundle": {
            "scenario_run": scenario_run,
            "final_market_state_run": final_run,
            "hedgemate_run": hedge_run,
            "backtest_run": backtest_run,
            "data_version": scenario_manifest.get("data_version"),
            "scenario_vector_as_of_date": scenario_manifest.get("scenario_vector_as_of_date") or scenario_manifest.get("final_market_state_as_of_date"),
            "generated_at_utc": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
            "freshness_status": status,
            "stale_reasons": reasons,
        },
        "event_overlay_status": dict(DEFAULT_EVENT_OVERLAY_STATUS),
    }


def find_available_run_ids(processed_dir=OUTPUT_PROCESSED_DIR):
    run_ids = set()
    for path in processed_dir.glob("features_summary_*.csv"):
        m = re.search(r"features_summary_(.+)\.csv$", path.name)
        if m:
            run_ids.add(m.group(1))
    ordered = sorted(run_ids, reverse=True)
    bundle = active_bundle()
    active_run = bundle.get("hedgemate_run") or read_product_manifest().get("active_hedgemate_run")
    if active_run and active_run in ordered:
        ordered = [active_run] + [run_id for run_id in ordered if run_id != active_run]
    return ordered


def find_scenario_run_ids(final_dir=None):
    final_dir = final_dir or SCENARIO_FINAL_DIR
    run_ids = {}
    for path in final_dir.glob("final_market_state_daily_*.csv"):
        m = re.search(r"final_market_state_daily_(.+)\.csv$", path.name)
        if m:
            run_ids[m.group(1)] = path.stat().st_mtime
    ordered = [
        run_id
        for run_id, _ in sorted(run_ids.items(), key=lambda item: (item[1], item[0]), reverse=True)
    ]
    manifest = read_active_manifest()
    product_manifest = read_product_manifest()
    for active_run in (scenario_manifest_final_run_id(manifest), product_manifest_final_run_id(product_manifest)):
        if active_run and active_run in ordered:
            ordered = [active_run] + [run_id for run_id in ordered if run_id != active_run]
            break
    return ordered


def parse_summary_markdown(path):
    meta = {}
    next_actions = []
    if not path.exists():
        return meta, next_actions

    in_next_actions = False
    with path.open("r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("## "):
                in_next_actions = line.startswith("## 6. 다음 액션")
                continue
            if in_next_actions and line.startswith("- "):
                next_actions.append(line[2:].strip())
                continue
            if line.startswith("- ") and ":" in line:
                key, value = line[2:].split(":", 1)
                meta[key.strip()] = value.strip()
    return meta, next_actions


def parse_single_asset_ticker(compare_rows):
    if not compare_rows:
        return None
    scenario = str(compare_rows[0].get("scenario", ""))
    m = re.search(r"기준\((.+?) 100%\)", scenario)
    return m.group(1) if m else None


def safe_rel_artifact(rel_path):
    rel_path = rel_path.lstrip("/")
    candidates = [(ROOT / rel_path).resolve(), (ROOT.parent / rel_path).resolve()]
    allowed_roots = [
        OUTPUT_RAW_DIR.resolve(),
        OUTPUT_PROCESSED_DIR.resolve(),
        OUTPUT_REPORT_DIR.resolve(),
        OUTPUT_VALIDATION_DIR.resolve(),
        DOC_RESULT_DIR.resolve(),
        SCENARIO_OUTPUT_DIR.resolve(),
    ]
    for abs_path in candidates:
        if any(root == abs_path or root in abs_path.parents for root in allowed_roots) and abs_path.exists():
            return abs_path
    return None


def latest_generated_at(run_id):
    candidates = [
        OUTPUT_PROCESSED_DIR / f"features_summary_{run_id}.csv",
        OUTPUT_PROCESSED_DIR / f"asset_risk_sensitivity_{run_id}.csv",
        OUTPUT_REPORT_DIR / f"portfolio_compare_{run_id}.csv",
        OUTPUT_REPORT_DIR / f"single_asset_compare_{run_id}.csv",
        OUTPUT_REPORT_DIR / f"asset_sensitivity_summary_{run_id}.md",
        DOC_RESULT_DIR / f"01_실행결과_{run_id}.md",
    ]
    existing = [p for p in candidates if p.exists()]
    if not existing:
        return None
    ts = max(p.stat().st_mtime for p in existing)
    return datetime.fromtimestamp(ts).isoformat(timespec="seconds")


def display_reference_date():
    return datetime.now().date().isoformat()


def parse_weights_snapshot(raw_value):
    if not raw_value:
        return []
    try:
        payload = json.loads(raw_value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    items = []
    for ticker, weight in payload.items():
        try:
            weight_value = float(weight)
        except (TypeError, ValueError):
            continue
        items.append(
            {
                "ticker": ticker,
                "displayName": display_label(ticker),
                "weightPct": weight_value,
            }
        )
    items.sort(key=lambda item: item["weightPct"], reverse=True)
    return items


def choose_best_detail(*row_groups):
    rows = []
    for group in row_groups:
        if not group:
            continue
        rows.extend(group)

    if not rows:
        return None
    recommendation_rank = {
        "PASS_RECOMMEND": 0,
        "REFERENCE_ONLY": 1,
        "INSUFFICIENT_DATA": 2,
        "FAIL_GATE": 3,
    }
    gate_rank = {"PASS": 0, "WARN": 1, "FAIL": 2}
    best = min(
        rows,
        key=lambda row: (
            recommendation_rank.get(str(row.get("recommendation_status") or ""), 9),
            gate_rank.get(str(row.get("status") or ""), 9),
            -(row.get("final_score") if isinstance(row.get("final_score"), (int, float)) else float("-inf")),
            str(row.get("candidate_label") or row.get("candidate_combo") or row.get("candidate_ticker") or ""),
        ),
    )
    enriched = dict(best)
    enrich_candidate_display(enriched)
    if not enriched.get("displayLabel"):
        enriched["displayLabel"] = humanize_scenario(enriched.get("scenario", ""))
    enriched["weights"] = parse_weights_snapshot(enriched.get("weights_snapshot"))
    return enriched


def parse_json_object(raw_value):
    if not raw_value:
        return {}
    try:
        payload = json.loads(raw_value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def enrich_candidate_display(row):
    if row.get("candidate_combo"):
        row["displayLabel"] = humanize_combo(row.get("candidate_combo"))
    elif row.get("candidate_ticker"):
        row["displayLabel"] = display_label(row.get("candidate_ticker"))
    elif row.get("candidate_label"):
        row["displayLabel"] = humanize_combo(row.get("candidate_label"))
    return row


def enrich_execution_plan(row):
    share_counts = parse_json_object(row.get("hedge_share_counts"))
    if share_counts:
        plan = []
        for ticker, quantity in share_counts.items():
            try:
                whole_quantity = int(float(quantity))
            except (TypeError, ValueError):
                continue
            if whole_quantity <= 0:
                continue
            try:
                price = lookup_price(ticker, quantity=whole_quantity)
                used_krw = price.get("marketValueKrw")
                if used_krw is None and price.get("latestPrice") and price.get("fxRate"):
                    used_krw = whole_quantity * float(price["latestPrice"]) * float(price["fxRate"])
                plan.append(
                    {
                        "ticker": ticker,
                        "displayName": display_label(ticker),
                        "targetAmountKrw": used_krw,
                        "latestPrice": price.get("latestPrice"),
                        "currency": price.get("currency"),
                        "fxRate": price.get("fxRate"),
                        "priceAsOf": price.get("priceAsOf"),
                        "impliedQuantity": whole_quantity,
                        "wholeShareQuantity": whole_quantity,
                        "estimatedUsedKrw": used_krw,
                        "estimatedCashLeftKrw": None,
                        "warnings": price.get("warnings", []),
                        "errors": price.get("errors", []),
                    }
                )
            except Exception as exc:
                plan.append({"ticker": ticker, "displayName": display_label(ticker), "targetAmountKrw": None, "errors": [str(exc)]})
        if plan:
            row["executionPlan"] = plan
            if isinstance(row.get("hedge_cash_left_krw"), (int, float)):
                row["executionNote"] = f"정수주 매수 기준 실행안 · 후보 전체 예상 잔액 {row['hedge_cash_left_krw']:.0f}원"
            return row

    budget = row.get("hedge_invested_krw") or row.get("hedge_budget_krw")
    if not isinstance(budget, (int, float)) or budget <= 0:
        row["executionPlan"] = []
        row["executionNote"] = "KRW 포트폴리오 금액으로 실행한 run이 아니어서 실제 매수 가능 수량은 포트폴리오 금액 입력 후 계산됩니다."
        return row

    allocations = parse_json_object(row.get("allocation_weights"))
    if not allocations:
        ticker = row.get("candidate_ticker")
        allocations = {ticker: 100.0} if ticker else {}
    total_weight = sum(float(value) for value in allocations.values() if str(value).strip())
    plan = []
    for ticker, weight in allocations.items():
        try:
            share = float(weight) / total_weight if total_weight > 0 else 0
        except (TypeError, ValueError):
            continue
        amount_krw = float(budget) * share
        try:
            price = lookup_price(ticker, amount_krw=amount_krw)
            quantity = price.get("impliedQuantity")
            whole_quantity = int(quantity) if isinstance(quantity, (int, float)) and quantity > 0 else None
            used_krw = None
            cash_left = None
            if whole_quantity is not None and price.get("latestPrice") and price.get("fxRate"):
                used_krw = whole_quantity * float(price["latestPrice"]) * float(price["fxRate"])
                cash_left = amount_krw - used_krw
            plan.append(
                {
                    "ticker": ticker,
                    "displayName": display_label(ticker),
                    "targetAmountKrw": amount_krw,
                    "latestPrice": price.get("latestPrice"),
                    "currency": price.get("currency"),
                    "fxRate": price.get("fxRate"),
                    "priceAsOf": price.get("priceAsOf"),
                    "impliedQuantity": quantity,
                    "wholeShareQuantity": whole_quantity,
                    "estimatedUsedKrw": used_krw,
                    "estimatedCashLeftKrw": cash_left,
                    "warnings": price.get("warnings", []),
                    "errors": price.get("errors", []),
                }
            )
        except Exception as exc:
            plan.append({"ticker": ticker, "displayName": display_label(ticker), "targetAmountKrw": amount_krw, "errors": [str(exc)]})
    row["executionPlan"] = plan
    row["executionNote"] = ""
    return row


def parse_portfolio_text(raw_text):
    rows = []
    for raw_line in str(raw_text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if "," not in line:
            raise ValueError("포트폴리오 입력은 'TICKER,비중' 형식이어야 합니다.")
        ticker, weight = line.split(",", 1)
        ticker = ticker.strip().upper()
        try:
            weight_pct = float(weight.strip())
        except ValueError as exc:
            raise ValueError("비중 숫자를 해석할 수 없습니다. 'TICKER,비중' 형식을 확인해 주세요.") from exc
        rows.append({"ticker": ticker, "weight_pct": weight_pct})
    if not rows:
        raise ValueError("포트폴리오 입력이 비어 있습니다.")
    return rows


def parse_portfolio_rows(raw_rows):
    rows = []
    total_amount_krw = 0.0
    seen_tickers = set()
    for item in raw_rows or []:
        ticker = resolve_asset_query(item.get("asset") or item.get("ticker"))
        if ticker in seen_tickers:
            raise ValueError(f"동일 자산은 한 번만 추가할 수 있습니다: {display_name(ticker)}")
        seen_tickers.add(ticker)
        try:
            amount_krw = float(item.get("amountKrw"))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{ticker} 금액을 숫자로 해석할 수 없습니다.") from exc
        if amount_krw <= 0:
            raise ValueError(f"{ticker} 금액은 0보다 커야 합니다.")
        rows.append({"ticker": ticker, "amount_krw": amount_krw})
        total_amount_krw += amount_krw

    if not rows:
        raise ValueError("포트폴리오 자산이 비어 있습니다.")

    return [
        {"ticker": row["ticker"], "weight_pct": (row["amount_krw"] / total_amount_krw) * 100.0}
        for row in rows
    ], total_amount_krw


def validate_portfolio_weights(rows, max_weight_pct=50.0):
    if not rows:
        raise ValueError("포트폴리오 입력이 비어 있습니다.")

    total = sum(float(row.get("weight_pct", 0.0)) for row in rows)
    if abs(total - 100.0) > 1e-6:
        raise ValueError(f"비중 합계가 100이 아닙니다. (현재 {total:.6f})")

    for row in sorted(rows, key=lambda item: item["ticker"]):
        ticker = row["ticker"]
        weight_pct = float(row.get("weight_pct", 0.0))
        if weight_pct < 0:
            raise ValueError(f"음수 비중 금지 위반 - {ticker}={weight_pct:.4f}%")
        if max_weight_pct is not None and weight_pct > max_weight_pct + 1e-9:
            raise ValueError(f"단일 자산 최대 {max_weight_pct:.1f}% 초과 - {ticker}={weight_pct:.4f}%")


def parse_budget_list_text(raw_value):
    values = []
    seen = set()
    for chunk in str(raw_value or "").split(","):
        token = chunk.strip()
        if not token:
            continue
        value = float(token)
        if value <= 0:
            raise ValueError("헷지 예산 퍼센트는 0보다 커야 합니다.")
        rounded = round(value, 8)
        if rounded not in seen:
            seen.add(rounded)
            values.append(value)
    if not values:
        raise ValueError("헷지 예산이 비어 있습니다.")
    return values


def build_hedge_budget_arg(payload, base_amount_krw=None):
    raw_budget_krw = (payload or {}).get("hedgeBudgetKrw")
    if raw_budget_krw not in (None, ""):
        if base_amount_krw in (None, 0):
            raise ValueError("KRW 헷지 예산을 사용하려면 기준 금액이 필요합니다.")
        try:
            hedge_budget_krw = float(raw_budget_krw)
        except (TypeError, ValueError) as exc:
            raise ValueError("헷지 예산(KRW)을 숫자로 해석할 수 없습니다.") from exc
        if hedge_budget_krw <= 0:
            raise ValueError("헷지 예산(KRW)은 0보다 커야 합니다.")
        hedge_budget_pct = (hedge_budget_krw / float(base_amount_krw)) * 100.0
        if hedge_budget_pct <= 0:
            raise ValueError("헷지 예산 퍼센트가 0 이하입니다.")
        return f"{hedge_budget_pct:.4f}".rstrip("0").rstrip(".")

    return ",".join(str(int(v)) if float(v).is_integer() else str(v) for v in parse_budget_list_text((payload or {}).get("hedgeBudgets") or "10,20,30"))


def write_portfolio_input(rows, job_id=None):
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    suffix = f"_{job_id}" if job_id else f"_{uuid.uuid4().hex[:8]}"
    path = INPUT_DIR / f"portfolio_weights{suffix}.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["ticker", "weight_pct"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return path


def portfolio_tickers_from_rows(rows):
    return normalize_ticker_list(str(row.get("ticker") or "").strip() for row in rows or [] if row.get("ticker"))


def safe_run_id_fragment(run_id):
    fragment = re.sub(r"[^0-9A-Za-z_.-]+", "_", str(run_id or "").strip())
    return fragment[:120] or uuid.uuid4().hex


def portable_analysis_manifest_path(path):
    resolved = Path(path)
    try:
        return resolved.resolve().relative_to(ROOT.parent.resolve()).as_posix()
    except Exception:
        return str(resolved)


def resolve_analysis_manifest_path(raw):
    if not raw:
        return None
    text = str(raw)
    path = Path(text)
    candidates = []
    if path.exists():
        return path
    if not path.is_absolute():
        candidates.extend([ROOT.parent / text, ROOT / text])
    try:
        name = PureWindowsPath(text).name if ("\\" in text or ":" in text) else path.name
    except Exception:
        name = path.name
    if name:
        candidates.append(ANALYSIS_CACHE_DIR / name)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return path


def find_analysis_cache_entry(cache_key=None, portfolio_request_hash=None):
    index = read_analysis_cache_index()
    entries = index.get("entries", {}) if isinstance(index, dict) else {}
    if cache_key and cache_key in entries:
        entry = entries[cache_key]
        manifest_path = resolve_analysis_manifest_path(entry.get("manifestPath"))
        if manifest_path.exists():
            return entry, manifest_path
    if portfolio_request_hash:
        candidates = [
            row
            for row in entries.values()
            if row.get("portfolioRequestHash") == portfolio_request_hash
        ]
        candidates.sort(key=lambda row: str(row.get("generatedAtUtc") or ""), reverse=True)
        for entry in candidates:
            manifest_path = resolve_analysis_manifest_path(entry.get("manifestPath"))
            if manifest_path.exists():
                return entry, manifest_path
    return None, None


def record_analysis_cache(prepared_request, result):
    run_id = result.get("runId") or prepared_request.get("runId")
    cache_key = prepared_request.get("analysisCacheKey")
    if not run_id or not cache_key:
        return None
    manifest = read_product_manifest()
    if not manifest:
        return None
    target = cache_manifest_path(run_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    index = read_analysis_cache_index()
    entries = index.setdefault("entries", {})
    request_fp = prepared_request.get("portfolioRequestFingerprint") or {}
    entry = {
        "runId": run_id,
        "cacheKey": cache_key,
        "manifestPath": portable_analysis_manifest_path(target),
        "portfolioRequestHash": request_fp.get("hash"),
        "portfolioRequestCanonical": request_fp.get("canonical"),
        "portfolioFingerprintHash": prepared_request.get("portfolioInputFingerprintHash"),
        "portfolioInputSha256": prepared_request.get("portfolioInputSha256"),
        "portfolioTickers": prepared_request.get("portfolioTickers") or [],
        "dataVersion": prepared_request.get("dataVersion"),
        "generatedAtUtc": manifest.get("generated_at_utc") or _now_iso(),
        "engineVersion": ANALYSIS_ENGINE_VERSION,
    }
    entries[cache_key] = entry
    write_analysis_cache_index(index)
    return entry


def portfolio_run_artifact_dir(result=None, cache_entry=None):
    result = result or {}
    cache_entry = cache_entry or {}
    for raw in (
        cache_entry.get("manifestPath"),
        result.get("analysisCacheManifestPath"),
        ROOT / "outputs" / "latest_manifest.json",
    ):
        if not raw:
            continue
        path = resolve_analysis_manifest_path(raw)
        if path.exists():
            return str(path)
    return None


def mark_portfolio_run_success(prepared_request, result=None, cache_entry=None):
    run_db_id = (prepared_request or {}).get("portfolioRunDbId")
    if not run_db_id:
        return
    persistence_store().update_portfolio_run(
        run_db_id,
        "SUCCESS",
        artifact_dir=portfolio_run_artifact_dir(result=result, cache_entry=cache_entry),
        error_message=None,
        finished=True,
    )


def mark_portfolio_run_failed(prepared_request, error_message):
    run_db_id = (prepared_request or {}).get("portfolioRunDbId")
    if not run_db_id:
        return
    persistence_store().update_portfolio_run(
        run_db_id,
        "FAILED",
        artifact_dir=None,
        error_message=sanitize_diagnostic_text(error_message or "analysis failed")[:4000],
        finished=True,
    )


def record_active_analysis_cache_for_payload(payload, cache_meta):
    cache_key = (cache_meta or {}).get("hash")
    if not cache_key:
        return None
    manifest = read_product_manifest()
    bundle = active_bundle(manifest)
    run_id = bundle.get("hedgemate_run") or manifest.get("active_hedgemate_run")
    active_fingerprint = bundle_portfolio_fingerprint(bundle) or manifest_portfolio_fingerprint(manifest, bundle)
    if not run_id or not active_fingerprint or not active_fingerprint.get("hash"):
        return None
    try:
        preview = preview_portfolio(payload or {})
    except Exception:
        return None
    requested_fingerprint = preview.get("portfolioInputFingerprint") or {}
    if requested_fingerprint.get("hash") != active_fingerprint.get("hash"):
        return None
    requested_tickers = normalize_ticker_list(requested_fingerprint.get("tickers") or [])
    active_tickers = normalize_ticker_list(active_fingerprint.get("tickers") or [])
    if requested_tickers != active_tickers:
        return None

    target = cache_manifest_path(run_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    index = read_analysis_cache_index()
    entries = index.setdefault("entries", {})
    request_fp = (cache_meta or {}).get("portfolioRequestFingerprint") or {}
    input_sha = (
        bundle.get("portfolioInputSha256")
        or manifest.get("portfolioInputSha256")
        or bundle.get("portfolio_input_sha256")
        or manifest.get("portfolio_input_sha256")
    )
    entry = {
        "runId": run_id,
        "cacheKey": cache_key,
        "manifestPath": portable_analysis_manifest_path(target),
        "portfolioRequestHash": request_fp.get("hash"),
        "portfolioRequestCanonical": request_fp.get("canonical"),
        "portfolioFingerprintHash": active_fingerprint.get("hash"),
        "portfolioInputSha256": input_sha,
        "portfolioTickers": active_tickers,
        "dataVersion": (cache_meta or {}).get("dataVersion") or bundle.get("data_version") or manifest.get("data_version"),
        "generatedAtUtc": manifest.get("generated_at_utc") or _now_iso(),
        "engineVersion": ANALYSIS_ENGINE_VERSION,
    }
    entries[cache_key] = entry
    write_analysis_cache_index(index)
    return entry


def activate_cached_analysis(entry):
    manifest_path = resolve_analysis_manifest_path(entry.get("manifestPath"))
    if not manifest_path.exists():
        raise FileNotFoundError("Cached analysis manifest is missing.")
    manifest = read_json(manifest_path, {})
    if not isinstance(manifest, dict) or not manifest:
        raise FileNotFoundError("Cached analysis manifest is invalid.")
    active_path = ROOT / "outputs" / "latest_manifest.json"
    active_path.parent.mkdir(parents=True, exist_ok=True)
    active_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def persist_portfolio_input(portfolio_input_path, run_id):
    if not portfolio_input_path:
        return None
    source = Path(portfolio_input_path)
    if not source.exists():
        return None
    target_base = Path(RUN_INPUT_DIR)
    if target_base == DEFAULT_ROOT / "outputs" / "run_inputs":
        target_base = ROOT / "outputs" / "run_inputs"
    target_dir = target_base / safe_run_id_fragment(run_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "portfolio_weights.csv"
    if source.resolve() != target.resolve():
        shutil.copyfile(source, target)
    return target


def attach_persisted_portfolio_input(prepared, portfolio_input_path, run_id):
    persisted = persist_portfolio_input(portfolio_input_path, run_id)
    if not persisted:
        return portfolio_input_path
    prepared["portfolioInputPath"] = str(portfolio_input_path)
    prepared["portfolioInputPersistedPath"] = str(persisted)
    prepared["backtestPortfolioInputPath"] = str(persisted)
    prepared["portfolioInputPersisted"] = True
    prepared["portfolioInputSha256"] = file_sha256(persisted)
    fingerprint = current_portfolio_fingerprint(persisted)
    if fingerprint:
        prepared["portfolioInputFingerprint"] = fingerprint
        prepared["portfolioInputFingerprintHash"] = fingerprint.get("hash")
        prepared["portfolioTickers"] = normalize_ticker_list(fingerprint.get("tickers") or prepared.get("portfolioTickers") or [])
    cleanup_paths = prepared.setdefault("cleanupPaths", [])
    if Path(portfolio_input_path).resolve() != persisted.resolve():
        cleanup_paths.append(str(portfolio_input_path))
    return persisted


def extract_run_id_from_stdout(stdout):
    match = re.search(r"FEATURE=.*?features_summary_(.+?)\.csv", stdout or "")
    return match.group(1) if match else None


def hedge_run_ready_for_product_update(run_id):
    if not run_id:
        return False
    required = [
        OUTPUT_PROCESSED_DIR / f"features_summary_{run_id}.csv",
        OUTPUT_PROCESSED_DIR / f"asset_scenario_sensitivity_{run_id}.csv",
        OUTPUT_REPORT_DIR / f"portfolio_1to1_hedge_{run_id}.csv",
        OUTPUT_REPORT_DIR / f"portfolio_multi_hedge_{run_id}.csv",
    ]
    return all(path.exists() for path in required)


def latest_scenario_bundle_context(product_manifest=None):
    product_manifest = product_manifest if isinstance(product_manifest, dict) else read_product_manifest()
    product_bundle = active_bundle(product_manifest)
    scenario_manifest = read_active_manifest()
    scenario_run = scenario_manifest.get("active_scenario_run") or product_bundle.get("scenario_run") or product_manifest.get("active_scenario_run")
    final_run = scenario_manifest_final_run_id(scenario_manifest) or product_bundle.get("final_market_state_run") or product_manifest.get("active_final_run") or scenario_run
    data_version = (
        scenario_manifest.get("data_version")
        or data_version_from_run_id(final_run)
        or data_version_from_run_id(scenario_run)
        or product_bundle.get("data_version")
        or product_manifest.get("data_version")
        or active_data_version(product_manifest)
    )
    scenario_vector_as_of = (
        scenario_manifest.get("scenario_vector_as_of_date")
        or scenario_manifest.get("final_market_state_as_of_date")
        or product_bundle.get("scenario_vector_as_of_date")
        or product_manifest.get("scenario_vector_as_of_date")
    )
    has_scenario_manifest_context = bool(scenario_manifest.get("active_scenario_run") or scenario_manifest_final_run_id(scenario_manifest))
    scenario_vector = (
        resolve_scenario_manifest_artifact(scenario_manifest, "active_scenario_vector", SCENARIO_VECTOR_DIR)
        or existing_artifact(SCENARIO_VECTOR_DIR / f"current_scenario_vector_{scenario_run}.csv")
    )
    final_scenario_vector = (
        resolve_scenario_manifest_artifact(scenario_manifest, "active_final_scenario_vector", SCENARIO_VECTOR_DIR)
        or existing_artifact(SCENARIO_VECTOR_DIR / f"current_scenario_vector_{final_run}.csv")
    )
    final_market_state = (
        resolve_scenario_manifest_artifact(scenario_manifest, "active_final_market_state", SCENARIO_FINAL_DIR)
        or existing_artifact(SCENARIO_FINAL_DIR / f"final_market_state_daily_{final_run}.csv")
    )
    scenario_confidence = (
        resolve_scenario_manifest_artifact(scenario_manifest, "active_scenario_confidence", SCENARIO_FINAL_DIR)
        or existing_artifact(SCENARIO_FINAL_DIR / f"scenario_confidence_{final_run}.csv")
    )
    top_active_scenarios = (
        resolve_scenario_manifest_artifact(scenario_manifest, "active_top_active_scenarios", SCENARIO_FINAL_DIR)
        or existing_artifact(SCENARIO_FINAL_DIR / f"top_active_scenarios_{final_run}.json")
    )
    final_metadata = (
        resolve_scenario_manifest_artifact(scenario_manifest, "active_final_metadata", SCENARIO_REPORT_DIR)
        or existing_artifact(SCENARIO_REPORT_DIR / f"final_market_state_metadata_{final_run}.json")
    )
    if not has_scenario_manifest_context:
        scenario_vector = scenario_vector or resolve_product_artifact(product_manifest, "scenarioVector", SCENARIO_VECTOR_DIR)
        final_scenario_vector = final_scenario_vector or resolve_product_artifact(product_manifest, "finalScenarioVector", SCENARIO_VECTOR_DIR)
        final_market_state = final_market_state or resolve_product_artifact(product_manifest, "finalMarketState", SCENARIO_FINAL_DIR)
        scenario_confidence = scenario_confidence or resolve_product_artifact(product_manifest, "scenarioConfidence", SCENARIO_FINAL_DIR)
        top_active_scenarios = top_active_scenarios or resolve_product_artifact(product_manifest, "topActiveScenarios", SCENARIO_FINAL_DIR)
        final_metadata = final_metadata or resolve_product_artifact(product_manifest, "finalMetadata", SCENARIO_REPORT_DIR)
    return {
        "manifest": product_manifest,
        "scenarioManifest": scenario_manifest,
        "scenarioRun": str(scenario_run) if scenario_run else None,
        "finalRun": str(final_run) if final_run else None,
        "dataVersion": str(data_version) if data_version else None,
        "scenarioVectorAsOfDate": scenario_vector_as_of,
        "artifacts": {
            "scenarioVector": scenario_vector,
            "finalScenarioVector": final_scenario_vector,
            "finalMarketState": final_market_state,
            "scenarioConfidence": scenario_confidence,
            "topActiveScenarios": top_active_scenarios,
            "finalMetadata": final_metadata,
            "eventOverlayMetadata": resolve_product_artifact(product_manifest, "eventOverlayMetadata", SCENARIO_REPORT_DIR),
            "finalRunbook": resolve_product_artifact(product_manifest, "finalRunbook", OUTPUT_REPORT_DIR),
        },
    }


def active_bundle_context_for_update():
    context = latest_scenario_bundle_context()
    scenario_run = context.get("scenarioRun")
    final_run = context.get("finalRun")
    data_version = context.get("dataVersion")
    if not scenario_run or not final_run or not data_version:
        return {}
    return context


def add_artifact_arg(cmd, manifest, arg_name, artifact_key, default_dir=None):
    path = resolve_product_artifact(manifest, artifact_key, default_dir=default_dir)
    if path:
        cmd.extend([arg_name, str(path)])


def add_path_arg(cmd, arg_name, path):
    if path:
        cmd.extend([arg_name, str(path)])


def build_product_update_commands(
    hedge_run_id,
    historical_validation_run_id="phase10a-wave5-20260514",
    portfolio_input_path=None,
    recommendation_scope="portfolio",
    data_version=None,
    backtest_candidate_limit=DASHBOARD_BACKTEST_CANDIDATE_LIMIT,
):
    context = active_bundle_context_for_update()
    if not context:
        return [], None
    resolved_data_version = str(data_version or context["dataVersion"])
    backtest_run_id = f"backtest-{hedge_run_id}"
    suffix = "backtest_gated"
    if recommendation_scope == "single_asset":
        one_input = OUTPUT_REPORT_DIR / f"single_asset_hedge_1to1_{hedge_run_id}.csv"
        multi_input = OUTPUT_REPORT_DIR / f"single_asset_hedge_multi_{hedge_run_id}.csv"
        one_output = OUTPUT_REPORT_DIR / f"single_asset_hedge_1to1_{hedge_run_id}_{suffix}.csv"
        multi_output = OUTPUT_REPORT_DIR / f"single_asset_hedge_multi_{hedge_run_id}_{suffix}.csv"
    else:
        recommendation_scope = "portfolio"
        one_input = OUTPUT_REPORT_DIR / f"portfolio_1to1_hedge_{hedge_run_id}.csv"
        multi_input = OUTPUT_REPORT_DIR / f"portfolio_multi_hedge_{hedge_run_id}.csv"
        one_output = OUTPUT_REPORT_DIR / f"portfolio_1to1_hedge_{hedge_run_id}_{suffix}.csv"
        multi_output = OUTPUT_REPORT_DIR / f"portfolio_multi_hedge_{hedge_run_id}_{suffix}.csv"
    python = sys.executable
    backtest_cmd = [
        python,
        str(ROOT / "scripts" / "run_scenario_backtest.py"),
        "--run-id",
        backtest_run_id,
        "--historical-validation-run-id",
        historical_validation_run_id,
        "--hedgemate-run-id",
        hedge_run_id,
        "--data-version",
        resolved_data_version,
        "--recommendation-scope",
        recommendation_scope,
    ]
    if backtest_candidate_limit and backtest_candidate_limit > 0:
        backtest_cmd.extend(["--candidate-limit", str(backtest_candidate_limit)])
    if portfolio_input_path:
        backtest_cmd.extend(["--portfolio-input", str(portfolio_input_path)])
    gate_cmd = [
        python,
        str(ROOT / "scripts" / "apply_backtest_gate.py"),
        "--hedgemate-run-id",
        hedge_run_id,
        "--backtest-run-id",
        backtest_run_id,
        "--one-to-one-path",
        str(one_input),
        "--multi-path",
        str(multi_input),
        "--one-output-path",
        str(one_output),
        "--multi-output-path",
        str(multi_output),
        "--output-suffix",
        suffix,
    ]
    update_cmd = [
        python,
        str(ROOT / "scripts" / "update_active_bundle.py"),
        "--scenario-run-id",
        context["scenarioRun"],
        "--final-run-id",
        context["finalRun"],
        "--hedgemate-run-id",
        hedge_run_id,
        "--backtest-run-id",
        backtest_run_id,
        "--data-version",
        resolved_data_version,
        "--features",
        str(OUTPUT_PROCESSED_DIR / f"features_summary_{hedge_run_id}.csv"),
        "--asset-scenario-sensitivity",
        str(OUTPUT_PROCESSED_DIR / f"asset_scenario_sensitivity_{hedge_run_id}.csv"),
        "--portfolio-1to1",
        str(one_output),
        "--portfolio-multi",
        str(multi_output),
        "--recommendation-status-qa",
        str(OUTPUT_REPORT_DIR / f"recommendation_status_qa_post_backtest_{hedge_run_id}_{suffix}.md"),
        "--backtest-csv",
        str(OUTPUT_VALIDATION_DIR / f"walk_forward_backtest_{backtest_run_id}.csv"),
        "--backtest-summary",
        str(OUTPUT_REPORT_DIR / f"walk_forward_backtest_summary_{backtest_run_id}.md"),
        "--backtest-gate-summary",
        str(OUTPUT_REPORT_DIR / f"backtest_gate_summary_{hedge_run_id}_{suffix}.md"),
        "--backtest-attribution-csv",
        str(OUTPUT_REPORT_DIR / f"backtest_attribution_{backtest_run_id}.csv"),
        "--backtest-attribution-summary",
        str(OUTPUT_REPORT_DIR / f"backtest_attribution_{backtest_run_id}.md"),
        "--formal-gate-audit-csv",
        str(OUTPUT_REPORT_DIR / f"formal_gate_audit_{hedge_run_id}_{suffix}.csv"),
        "--formal-gate-audit-summary",
        str(OUTPUT_REPORT_DIR / f"formal_gate_audit_{hedge_run_id}_{suffix}.md"),
    ]
    if portfolio_input_path:
        update_cmd.extend(["--portfolio-input", str(portfolio_input_path)])
    if context.get("scenarioVectorAsOfDate"):
        update_cmd.extend(["--scenario-vector-as-of-date", str(context["scenarioVectorAsOfDate"])])
    artifacts = context.get("artifacts") or {}
    add_path_arg(update_cmd, "--scenario-vector", artifacts.get("scenarioVector"))
    add_path_arg(update_cmd, "--final-scenario-vector", artifacts.get("finalScenarioVector"))
    add_path_arg(update_cmd, "--final-market-state", artifacts.get("finalMarketState"))
    add_path_arg(update_cmd, "--scenario-confidence", artifacts.get("scenarioConfidence"))
    add_path_arg(update_cmd, "--top-active-scenarios", artifacts.get("topActiveScenarios"))
    add_path_arg(update_cmd, "--final-metadata", artifacts.get("finalMetadata"))
    add_path_arg(update_cmd, "--event-overlay-metadata", artifacts.get("eventOverlayMetadata"))
    add_path_arg(update_cmd, "--final-runbook", artifacts.get("finalRunbook"))
    return [backtest_cmd, gate_cmd, update_cmd], backtest_run_id


def prepare_run_request(payload, job_id=None):
    if not isinstance(payload, dict):
        raise ValueError("JSON 객체 요청이 필요합니다.")

    mode = str((payload or {}).get("mode") or "").strip()
    max_combo_size = parse_max_combo_size((payload or {}).get("maxComboSize"))
    run_id = str((payload or {}).get("runId") or build_run_id())
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "run_data_pipeline.py"),
        "--max-combo-size",
        str(max_combo_size),
        "--run-id",
        run_id,
        "--action-bootstrap-iterations",
        str(DASHBOARD_ACTION_BOOTSTRAP_ITERATIONS),
    ]
    manifest = read_product_manifest()
    scenario_context = latest_scenario_bundle_context(manifest)
    data_version = (payload or {}).get("dataVersion") or scenario_context.get("dataVersion") or active_data_version(manifest)
    if data_version:
        cmd.extend(["--data-version", str(data_version)])
    if bool((payload or {}).get("forceRefreshRaw")):
        cmd.append("--force-refresh-raw")
    scenario_vector = (scenario_context.get("artifacts") or {}).get("finalScenarioVector") or resolve_product_artifact(manifest, "finalScenarioVector", default_dir=SCENARIO_VECTOR_DIR)
    if scenario_vector:
        cmd.extend(["--scenario-vector", str(scenario_vector)])
    prepared = {
        "_prepared_request": True,
        "jobId": job_id,
        "runId": run_id,
        "cmd": cmd,
        "dataVersion": str(data_version) if data_version else None,
        "forceReanalysis": bool((payload or {}).get("forceReanalysis")),
        "ignoreAnalysisCache": bool((payload or {}).get("ignoreAnalysisCache")),
    }
    cache_meta = analysis_cache_key(payload, data_version=data_version, scenario_vector=scenario_vector)
    if cache_meta:
        prepared["analysisCacheKey"] = cache_meta["hash"]
        prepared["analysisCacheKeyPayload"] = cache_meta["payload"]
        prepared["portfolioRequestFingerprint"] = cache_meta["portfolioRequestFingerprint"]

    if mode == "single_asset":
        single_asset = resolve_asset_query((payload or {}).get("singleAsset"))
        base_amount_krw = (payload or {}).get("baseAmountKrw")
        if base_amount_krw in (None, ""):
            hedge_budgets = build_hedge_budget_arg(payload)
            cmd.extend(["--hedge-budgets", hedge_budgets])
        else:
            try:
                base_amount_krw = float(base_amount_krw)
            except (TypeError, ValueError) as exc:
                raise ValueError("단일 자산 보유 금액(KRW)을 숫자로 해석할 수 없습니다.") from exc
            if base_amount_krw <= 0:
                raise ValueError("단일 자산 보유 금액(KRW)은 0보다 커야 합니다.")
            raw_budget_krw = (payload or {}).get("hedgeBudgetKrw")
            if raw_budget_krw in (None, ""):
                hedge_budgets = build_hedge_budget_arg(payload, base_amount_krw=base_amount_krw)
                cmd.extend(["--hedge-budgets", hedge_budgets])
            else:
                cmd.extend(["--base-total-krw", str(base_amount_krw), "--hedge-budgets-krw", str(float(raw_budget_krw))])
        cmd.extend(["--single-asset", single_asset])
        prepared["mode"] = "single_asset"
        prepared["singleAsset"] = single_asset
        prepared["portfolioTickers"] = [single_asset]
        portfolio_input_path = write_portfolio_input([{"ticker": single_asset, "weight_pct": 100.0}], job_id=job_id)
        persisted_portfolio_input = attach_persisted_portfolio_input(prepared, portfolio_input_path, run_id)
        cmd.extend(["--portfolio-input", str(persisted_portfolio_input)])
        return prepared

    if mode == "portfolio":
        portfolio_rows = (payload or {}).get("portfolioRows")
        if not portfolio_rows:
            raise ValueError("제품 API /api/run portfolio mode requires portfolioRows; sample/default portfolio fallback is disabled.")
        preview = preview_portfolio(payload)
        if not preview["canRunAnalysis"]:
            raise ValueError("; ".join(preview["errors"]) or "포트폴리오 preview를 분석 입력으로 변환할 수 없습니다.")
        rows = preview["analysisRows"]
        total_amount_krw = preview["totalMarketValueKrw"]
        if False and len(rows) == 1:
            single_asset = rows[0]["ticker"]
            if single_asset == "__CASH__":
                raise ValueError("현금 단독 입력은 단일자산 헷지 분석 기준으로 사용할 수 없습니다.")
            raw_budget_krw = (payload or {}).get("hedgeBudgetKrw")
            if raw_budget_krw not in (None, "") and total_amount_krw not in (None, 0):
                cmd.extend(["--base-total-krw", str(total_amount_krw), "--hedge-budgets-krw", str(float(raw_budget_krw))])
            else:
                hedge_budgets = build_hedge_budget_arg(payload, base_amount_krw=total_amount_krw)
                cmd.extend(["--hedge-budgets", hedge_budgets])
            cmd.extend(["--single-asset", single_asset])
            prepared["mode"] = "single_asset"
            prepared["singleAsset"] = single_asset
            prepared["portfolioTickers"] = [single_asset]
            portfolio_input_path = write_portfolio_input([{"ticker": single_asset, "weight_pct": 100.0}], job_id=job_id)
            persisted_portfolio_input = attach_persisted_portfolio_input(prepared, portfolio_input_path, run_id)
            cmd.extend(["--portfolio-input", str(persisted_portfolio_input)])
            return prepared
        validate_portfolio_weights(rows, max_weight_pct=None)
        raw_budget_krw = (payload or {}).get("hedgeBudgetKrw")
        if raw_budget_krw not in (None, "") and total_amount_krw not in (None, 0):
            cmd.extend(["--base-total-krw", str(total_amount_krw), "--hedge-budgets-krw", str(float(raw_budget_krw))])
        else:
            hedge_budgets = build_hedge_budget_arg(payload, base_amount_krw=total_amount_krw)
            cmd.extend(["--hedge-budgets", hedge_budgets])
        portfolio_input_path = write_portfolio_input(rows, job_id=job_id)
        persisted_portfolio_input = attach_persisted_portfolio_input(prepared, portfolio_input_path, run_id)
        cmd.extend(["--portfolio-input", str(persisted_portfolio_input)])
        prepared["mode"] = "portfolio"
        prepared["portfolioTickers"] = portfolio_tickers_from_rows(rows)
        return prepared

    raise ValueError("mode는 single_asset 또는 portfolio 여야 합니다.")


def _stage_detail(stage):
    return STAGE_DETAILS.get(str(stage or ""), (str(stage or "진행 중"), "작업이 진행 중입니다."))


def _now_iso():
    return datetime.now().isoformat(timespec="seconds")


def _elapsed_seconds(started_at):
    try:
        start = datetime.fromisoformat(str(started_at))
    except (TypeError, ValueError):
        return 0
    return max(0, int((datetime.now() - start).total_seconds()))


class PipelineExecutionError(RuntimeError):
    def __init__(self, message, diagnostics=None):
        super().__init__(message)
        self.diagnostics = diagnostics or {}


def sanitize_diagnostic_text(value):
    text = str(value or "")
    text = re.sub(
        r"(?i)\b(token|secret|password|passwd|api[_-]?key|github[_-]?token|webhook[_-]?secret)\b(\s*[:=]\s*)([^\s,;]+)",
        r"\1\2[hidden]",
        text,
    )
    text = re.sub(r"(?i)(https?://)([^/\s:@]+):([^@\s/]+)@", r"\1[hidden]:[hidden]@", text)
    return text


def tail_diagnostic_text(value, max_chars=DIAGNOSTIC_TEXT_LIMIT, max_lines=DIAGNOSTIC_LINE_LIMIT):
    text = sanitize_diagnostic_text(value)
    lines = text.splitlines()
    if len(lines) > max_lines:
        text = "\n".join(lines[-max_lines:])
    if len(text) > max_chars:
        text = text[-max_chars:]
    return sanitize_diagnostic_text(text).strip()


def diagnostic_summary(stdout="", stderr=""):
    for text in (stderr, stdout):
        lines = [line.strip() for line in tail_diagnostic_text(text).splitlines() if line.strip()]
        if lines:
            return lines[-1][:500]
    return ""


def subprocess_failure_diagnostics(stage, cmd, completed=None, cwd=None, stdout=None, stderr=None, returncode=None):
    stdout_tail = tail_diagnostic_text(stdout if stdout is not None else getattr(completed, "stdout", ""))
    stderr_tail = tail_diagnostic_text(stderr if stderr is not None else getattr(completed, "stderr", ""))
    code = returncode if returncode is not None else getattr(completed, "returncode", None)
    summary = diagnostic_summary(stdout_tail, stderr_tail)
    return {
        "stage": stage,
        "returncode": code,
        "cwd": str(cwd) if cwd else None,
        "cmd": [sanitize_diagnostic_text(part) for part in cmd],
        "stdoutTail": stdout_tail,
        "stderrTail": stderr_tail,
        "summary": summary,
    }


def raise_subprocess_failure(stage, cmd, completed, cwd, fallback):
    diagnostics = subprocess_failure_diagnostics(stage, cmd, completed=completed, cwd=cwd)
    message = f"{stage} failed"
    if diagnostics.get("returncode") is not None:
        message += f" (exit {diagnostics['returncode']})"
    message += f": {diagnostics.get('summary') or fallback}"
    raise PipelineExecutionError(message, diagnostics=diagnostics)


def exception_diagnostics(exc):
    diagnostics = getattr(exc, "diagnostics", None)
    return diagnostics if isinstance(diagnostics, dict) else None


def _snapshot_run_job(job_id):
    with RUN_JOBS_LOCK:
        job = RUN_JOBS.get(job_id)
        if not job:
            return None
        snapshot = dict(job)
        snapshot["elapsedSeconds"] = _elapsed_seconds(snapshot.get("startedAt"))
        snapshot.setdefault("timeoutSeconds", JOB_TIMEOUT_SECONDS)
        if snapshot.get("status") in {"queued", "running"} and snapshot["elapsedSeconds"] > JOB_TIMEOUT_SECONDS:
            job.update(
                {
                    "status": "failed",
                    "stage": "failed",
                    "currentStep": "timeout",
                    "estimatedRemainingMessage": "분석 제한 시간을 초과했습니다. 포트폴리오 규모를 줄이거나 다시 시도하세요.",
                    "error": "분석 제한 시간 초과",
                    "completedAt": _now_iso(),
                    "lastHeartbeatAt": _now_iso(),
                }
            )
            snapshot = dict(job)
            snapshot["elapsedSeconds"] = _elapsed_seconds(snapshot.get("startedAt"))
            snapshot.setdefault("timeoutSeconds", JOB_TIMEOUT_SECONDS)
        return snapshot


def _update_run_job(job_id, **fields):
    with RUN_JOBS_LOCK:
        if job_id not in RUN_JOBS:
            return None
        if "stage" in fields:
            current_step, estimated = _stage_detail(fields.get("stage"))
            fields.setdefault("currentStep", current_step)
            fields.setdefault("estimatedRemainingMessage", estimated)
            fields.setdefault("lastHeartbeatAt", _now_iso())
        RUN_JOBS[job_id].update(fields)
        return dict(RUN_JOBS[job_id])


def _cleanup_prepared_artifacts(prepared_request):
    paths = (prepared_request or {}).get("cleanupPaths")
    if paths is None:
        paths = {
            (prepared_request or {}).get("portfolioInputPath"),
            (prepared_request or {}).get("backtestPortfolioInputPath"),
        }
    for portfolio_input_path in paths:
        if not portfolio_input_path:
            continue
        try:
            Path(portfolio_input_path).unlink(missing_ok=True)
        except OSError:
            pass


def run_subprocess_with_timeout(runner, cmd, **kwargs):
    try:
        return runner(cmd, timeout=JOB_TIMEOUT_SECONDS, **kwargs)
    except subprocess.TimeoutExpired as exc:
        diagnostics = subprocess_failure_diagnostics(
            "subprocess timeout",
            cmd,
            cwd=kwargs.get("cwd"),
            stdout=getattr(exc, "stdout", ""),
            stderr=getattr(exc, "stderr", ""),
            returncode=None,
        )
        raise PipelineExecutionError(
            f"subprocess timeout after {JOB_TIMEOUT_SECONDS // 60} minutes",
            diagnostics=diagnostics,
        ) from exc
    except TypeError:
        return runner(cmd, **kwargs)


def ensure_daily_auxiliary_raw_data(data_version, target_latest_date=None):
    try:
        import run_data_pipeline as hedgemate_pipeline
    except ImportError as exc:
        raise RuntimeError("Could not import HedgeMate raw FX/benchmark refresh helpers") from exc

    hedgemate_pipeline.OUTPUT_RAW_DIR = OUTPUT_RAW_DIR
    for filename in (f"raw_fx_daily_{data_version}.csv", f"raw_benchmark_daily_{data_version}.csv"):
        path = OUTPUT_RAW_DIR / filename
        if target_latest_date and path.exists():
            latest_date = max_csv_date(path)
            if latest_date and latest_date < str(target_latest_date):
                path.unlink(missing_ok=True)

    run_ts = datetime.now(timezone.utc)
    start_dt = (run_ts - timedelta(days=365 * 5 + 10)).replace(hour=0, minute=0, second=0, microsecond=0)
    end_dt = run_ts + timedelta(days=1)
    period1 = int(start_dt.timestamp())
    period2 = int(end_dt.timestamp())
    ingested_at = run_ts.isoformat()
    fx_file, _, fx_rate_map, fx_cached = hedgemate_pipeline.load_or_fetch_fx(
        period1,
        period2,
        data_version,
        ingested_at,
    )
    benchmark_file, _, benchmark_series, benchmark_symbol, benchmark_cached = hedgemate_pipeline.load_or_fetch_benchmark_symbol(
        "^KS200",
        "^KS11",
        period1,
        period2,
        data_version,
        ingested_at,
    )
    benchmark_latest = max((date_str for date_str, _ in benchmark_series), default=None)
    return {
        "fxRawPath": str(fx_file),
        "fxLatestDate": max(fx_rate_map) if fx_rate_map else None,
        "fxUsedCached": bool(fx_cached),
        "benchmarkRawPath": str(benchmark_file),
        "benchmarkLatestDate": benchmark_latest,
        "benchmarkSymbol": benchmark_symbol,
        "benchmarkUsedCached": bool(benchmark_cached),
    }


def refresh_daily_market_state_outputs(data_version, runner=subprocess.run, target_latest_date=None, force=False, status_callback=None):
    before = scenario_final_output_status(data_version=data_version, expected_date=target_latest_date)
    if before.get("fresh") and not force:
        return {
            "ok": True,
            "skipped": True,
            "reason": "daily market-state final is already current",
            **before,
        }

    scenario_run, final_run = daily_market_state_run_ids(data_version)
    if status_callback:
        status_callback("refreshing auxiliary raw data", "updating FX and benchmark raw cache")
    auxiliary_raw = ensure_daily_auxiliary_raw_data(data_version, target_latest_date=target_latest_date)

    commands = [
        [
            sys.executable,
            str(SCENARIO_RESEARCH_ROOT / "scripts" / "run_market_state_pipeline.py"),
            "--run-id",
            scenario_run,
            "--data-version",
            str(data_version),
        ],
        [
            sys.executable,
            str(SCENARIO_RESEARCH_ROOT / "scripts" / "run_final_market_state_pipeline.py"),
            "--run-id",
            final_run,
            "--scenario-run-id",
            scenario_run,
        ],
    ]
    stdout_by_step = {}
    for index, cmd in enumerate(commands, start=1):
        if status_callback:
            label = "scenario market-state pipeline" if index == 1 else "final market-state merge"
            status_callback(label, label)
        completed = run_subprocess_with_timeout(
            runner,
            cmd,
            cwd=str(ROOT.parent),
            capture_output=True,
            text=True,
            check=False,
        )
        stdout_by_step[f"step{index}"] = completed.stdout
        if completed.returncode != 0:
            raise_subprocess_failure(label, cmd, completed, ROOT.parent, "daily market-state refresh failed")

    after = scenario_final_output_status(data_version=data_version, expected_date=target_latest_date)
    return {
        "ok": bool(after.get("exists")),
        "skipped": False,
        "scenarioRunId": scenario_run,
        "finalRunId": final_run,
        "targetLatestMarketDate": target_latest_date,
        "dataAsOfDate": after.get("dataAsOfDate"),
        "fresh": after.get("fresh"),
        "auxiliaryRaw": auxiliary_raw,
        "stdout": stdout_by_step,
    }


def _start_job_heartbeat(job_id, stop_event):
    def heartbeat():
        while not stop_event.wait(JOB_HEARTBEAT_SECONDS):
            snapshot = _snapshot_run_job(job_id)
            if not snapshot or snapshot.get("status") not in {"running", "queued"}:
                return
            _update_run_job(
                job_id,
                lastHeartbeatAt=_now_iso(),
                estimatedRemainingMessage=snapshot.get("estimatedRemainingMessage") or "작업이 계속 진행 중입니다.",
            )

    worker = threading.Thread(target=heartbeat, daemon=True)
    worker.start()
    return worker


def _run_pipeline_job(job_id, prepared_request, runner):
    stop_heartbeat = threading.Event()
    _start_job_heartbeat(job_id, stop_heartbeat)
    try:
        result = run_pipeline_for_request(
            prepared_request,
            runner=runner,
            status_callback=lambda stage: _update_run_job(job_id, stage=stage),
        )
        cache_entry = record_analysis_cache(prepared_request, result)
        if cache_entry:
            result["cached"] = False
            result["analysisCacheKey"] = cache_entry.get("cacheKey")
            result["analysisCacheManifestPath"] = cache_entry.get("manifestPath")
        mark_portfolio_run_success(prepared_request, result=result, cache_entry=cache_entry)
        _update_run_job(
            job_id,
            status="completed",
            runId=result.get("runId"),
            result=result,
            error=None,
            completedAt=datetime.now().isoformat(timespec="seconds"),
        )
    except Exception as exc:
        diagnostics = exception_diagnostics(exc)
        if diagnostics:
            print(
                "HedgeMate analysis failed: "
                + json.dumps(diagnostics, ensure_ascii=False),
                file=sys.stderr,
                flush=True,
            )
        mark_portfolio_run_failed(prepared_request, exc)
        _update_run_job(
            job_id,
            status="failed",
            runId=prepared_request.get("runId"),
            error=sanitize_diagnostic_text(str(exc)),
            diagnostics=diagnostics,
            completedAt=datetime.now().isoformat(timespec="seconds"),
        )
    finally:
        stop_heartbeat.set()
        _cleanup_prepared_artifacts(prepared_request)


def launch_run_job(payload, runner=subprocess.run, thread_factory=threading.Thread):
    job_id = (payload or {}).get("jobId") or uuid.uuid4().hex
    prepared_request = payload if (payload or {}).get("_prepared_request") else prepare_run_request(payload, job_id=job_id)
    job_id = prepared_request.get("jobId") or job_id
    prepared_request["jobId"] = job_id
    use_cache = not bool((payload or {}).get("forceReanalysis") or (payload or {}).get("ignoreAnalysisCache"))
    if use_cache and prepared_request.get("analysisCacheKey"):
        cached_entry, _ = find_analysis_cache_entry(cache_key=prepared_request.get("analysisCacheKey"))
        if cached_entry:
            activate_cached_analysis(cached_entry)
            mark_portfolio_run_success(
                prepared_request,
                result={
                    "runId": cached_entry.get("runId"),
                    "portfolioInputSha256": cached_entry.get("portfolioInputSha256"),
                    "portfolioInputFingerprintHash": cached_entry.get("portfolioFingerprintHash"),
                },
                cache_entry=cached_entry,
            )
            with RUN_JOBS_LOCK:
                RUN_JOBS[job_id] = {
                    "jobId": job_id,
                    "status": "completed",
                    "stage": "cache hit",
                    "currentStep": "cached analysis reused",
                    "estimatedRemainingMessage": "",
                    "lastHeartbeatAt": _now_iso(),
                    "elapsedSeconds": 0,
                    "timeoutSeconds": JOB_TIMEOUT_SECONDS,
                    "runId": cached_entry.get("runId"),
                    "error": None,
                    "diagnostics": None,
                    "result": {
                        "ok": True,
                        "cached": True,
                        "runId": cached_entry.get("runId"),
                        "cacheKey": prepared_request.get("analysisCacheKey"),
                        "portfolioInputSha256": cached_entry.get("portfolioInputSha256"),
                        "portfolioInputFingerprintHash": cached_entry.get("portfolioFingerprintHash"),
                        "portfolioTickers": cached_entry.get("portfolioTickers") or [],
                    },
                    "portfolioTickers": cached_entry.get("portfolioTickers") or [],
                    "portfolioInputSha256": cached_entry.get("portfolioInputSha256"),
                    "portfolioInputFingerprintHash": cached_entry.get("portfolioFingerprintHash"),
                    "startedAt": _now_iso(),
                    "completedAt": _now_iso(),
                }
            return _snapshot_run_job(job_id)
    with RUN_JOBS_LOCK:
        RUN_JOBS[job_id] = {
            "jobId": job_id,
            "status": "running",
            "stage": "queued",
            "currentStep": "대기 중",
            "estimatedRemainingMessage": "작업 순서를 기다리고 있습니다.",
            "lastHeartbeatAt": _now_iso(),
            "elapsedSeconds": 0,
            "timeoutSeconds": JOB_TIMEOUT_SECONDS,
            "runId": prepared_request.get("runId"),
            "error": None,
            "diagnostics": None,
            "result": None,
            "portfolioTickers": prepared_request.get("portfolioTickers") or [],
            "portfolioInputSha256": prepared_request.get("portfolioInputSha256"),
            "portfolioInputFingerprintHash": prepared_request.get("portfolioInputFingerprintHash"),
            "startedAt": _now_iso(),
            "completedAt": None,
        }
    worker = thread_factory(target=_run_pipeline_job, args=(job_id, prepared_request, runner), daemon=True)
    worker.start()
    return _snapshot_run_job(job_id)


def refresh_job_type_for_mode(mode):
    if mode == "intraday_nowcast":
        return REFRESH_JOB_TYPE_INTRADAY_NOWCAST
    if mode == INTRADAY_NEWS_JOB_TYPE:
        return REFRESH_JOB_TYPE_NEWS_OVERLAY
    return REFRESH_JOB_TYPE_MARKET_DATA


def trigger_type_from_payload(payload):
    payload = payload or {}
    if payload.get("schedulerRefresh"):
        return "scheduler"
    if payload.get("startupRefresh"):
        return "startup"
    if payload.get("autoRefresh"):
        return "auto"
    return "manual"


def create_refresh_job_record(job_id, job_type, trigger_type, status="PENDING"):
    try:
        persistence_store().create_refresh_job(job_id, job_type, trigger_type=trigger_type, status=status)
    except DuplicateRefreshJobError:
        return


def update_refresh_job_record(job_id, status, error_message=None, finished=True):
    try:
        persistence_store().update_refresh_job(job_id, status, error_message=error_message, finished=finished)
    except Exception:
        return


def record_data_snapshot_for_refresh(job_type, status, payload=None, result=None):
    payload = payload or {}
    result = result or {}
    freshness = result.get("freshness") or result.get("result", {}).get("freshness") or {}
    data_version = result.get("dataVersion") or payload.get("dataVersion") or freshness.get("dataVersion") or freshness.get("marketDataVersion")
    as_of = (
        result.get("latestMarketDate")
        or result.get("targetLatestMarketDate")
        or freshness.get("latestMarketDate")
        or freshness.get("intradayNowcastLatestTimestampKst")
    )
    artifact_path = result.get("manifestPath") or result.get("rawPath") or result.get("artifactPath")
    try:
        persistence_store().record_data_snapshot(
            job_type,
            data_version=data_version,
            as_of_kst=as_of,
            artifact_path=artifact_path,
            freshness_status=status,
        )
    except Exception:
        return


def _run_refresh_market_data_job(job_id, payload, runner):
    data_version = str((payload or {}).get("dataVersion") or datetime.now().strftime("%Y%m%d"))
    run_stamp = str((payload or {}).get("runStamp") or data_version)
    max_combo_size = parse_max_combo_size((payload or {}).get("maxComboSize") or 2)
    mode = str((payload or {}).get("mode") or "market_data_only").strip() or "market_data_only"
    force_full_refresh = bool((payload or {}).get("forceFullRefresh") or mode == "full_rebuild")
    if mode not in MARKET_REFRESH_MODES:
        raise ValueError("mode must be one of market_data_only, portfolio_reanalysis, full_rebuild, intraday_nowcast.")
    _update_run_job(job_id, stage="cache loading" if not force_full_refresh else "running refresh pipeline")

    if mode == "intraday_nowcast":
        _update_run_job(job_id, stage="intraday nowcast", currentStep="fetching latest intraday nowcast")
        intraday_run_id = f"intraday-refresh-{run_stamp}"
        cmd = [
            sys.executable,
            str(SCENARIO_RESEARCH_ROOT / "scripts" / "run_intraday_nowcast_pipeline.py"),
            "--run-id",
            intraday_run_id,
            "--data-version",
            data_version,
            "--interval",
            "1h",
        ]
        if (payload or {}).get("reuseRaw"):
            cmd.append("--reuse-raw")
        completed = run_subprocess_with_timeout(
            runner,
            cmd,
            cwd=str(ROOT.parent),
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise_subprocess_failure("intraday nowcast refresh", cmd, completed, ROOT.parent, "intraday nowcast refresh failed")
        status = latest_intraday_nowcast_status()
        _update_run_job(
            job_id,
            status="completed",
            stage="complete",
            currentStep="complete",
            intradayNowcast=status,
            result={
                "ok": True,
                "mode": "intraday_nowcast",
                "dataVersion": data_version,
                "runId": intraday_run_id,
                "stdout": completed.stdout,
                "intradayNowcast": status,
            },
            error=None,
            completedAt=datetime.now().isoformat(timespec="seconds"),
        )
        return

    if mode == "market_data_only" and not force_full_refresh:
        def on_progress(update):
            stage = update.get("stage") or "refreshing market data"
            current_step = update.get("currentStep") or stage
            _update_run_job(
                job_id,
                stage=stage,
                currentStep=current_step,
                estimatedRemainingMessage=(
                    f"{update.get('fetchedTickers', 0)}/{update.get('totalTickers', len(universe_asset_rows()))} tickers processed"
                    if update.get("totalTickers")
                    else "updating raw market cache"
                ),
                latestMarketDate=update.get("latestMarketDate"),
                rowsAdded=update.get("rowsAdded"),
            )

        result = incremental_update_raw_market_data(
            universe_asset_rows(),
            OUTPUT_RAW_DIR,
            data_version=data_version,
            source_snapshot=(payload or {}).get("sourceSnapshot"),
            target_latest_date=(payload or {}).get("targetLatestMarketDate"),
            progress_callback=on_progress,
        )
        manifest = result["manifest"]
        target_latest_date = manifest.get("targetLatestMarketDate")
        market_latest_date = manifest.get("maxMarketDate") or manifest.get("latestMarketDate")
        market_ready_for_daily_state = bool(
            target_latest_date
            and market_latest_date
            and str(market_latest_date) >= str(target_latest_date)
            and market_coverage_is_fresh(manifest.get("tickerCoverageRatio"))
        )
        if market_ready_for_daily_state:
            daily_market_state = refresh_daily_market_state_outputs(
                data_version,
                runner=runner,
                target_latest_date=target_latest_date,
                force=bool((payload or {}).get("forceDailyMarketState")),
                status_callback=lambda stage, step: _update_run_job(job_id, stage=stage, currentStep=step),
            )
        else:
            daily_market_state = {
                "ok": False,
                "skipped": True,
                "reason": "raw market data did not reach the target latest date or coverage threshold",
                "targetLatestMarketDate": target_latest_date,
                "latestMarketDate": market_latest_date,
                "tickerCoverageRatio": manifest.get("tickerCoverageRatio"),
            }
        freshness = load_data_freshness(reference_date=datetime.now(KST).date())
        intraday_status = freshness.get("intradayNowcast")
        _update_run_job(
            job_id,
            status="completed",
            stage="complete",
            currentStep="complete",
            freshness=freshness,
            intradayNowcast=intraday_status,
            result={
                "ok": True,
                "mode": "market_data_only",
                "dataVersion": data_version,
                "rawPath": str(result["rawPath"]),
                "manifestPath": str(result["manifestPath"]),
                "latestMarketDate": manifest.get("latestMarketDate"),
                "targetLatestMarketDate": manifest.get("targetLatestMarketDate"),
                "rowsAdded": manifest.get("rowsAdded"),
                "failedTickers": manifest.get("failedTickers") or [],
                "staleTickers": manifest.get("staleTickers") or [],
                "durationSeconds": manifest.get("durationSeconds"),
                "dailyMarketState": daily_market_state,
                "freshness": freshness,
                "intradayNowcast": intraday_status,
                "warning": "Some tickers failed to update; existing cached rows were kept."
                if manifest.get("failedTickers")
                else "",
            },
            error=None,
            completedAt=datetime.now().isoformat(timespec="seconds"),
        )
        return

    if mode == "portfolio_reanalysis":
        _update_run_job(job_id, stage="portfolio analysis", currentStep="running selected portfolio analysis")
        analysis_payload = dict(payload or {})
        analysis_payload["mode"] = "portfolio"
        analysis_payload["dataVersion"] = data_version
        result = run_pipeline_for_request(
            analysis_payload,
            runner=runner,
            status_callback=lambda stage: _update_run_job(job_id, stage=stage, currentStep=stage),
        )
        _update_run_job(
            job_id,
            status="completed",
            stage="complete",
            currentStep="complete",
            result={"ok": True, "mode": "portfolio_reanalysis", **result},
            error=None,
            completedAt=datetime.now().isoformat(timespec="seconds"),
        )
        return

    cleanup_paths = []
    portfolio_context = {
        "requested": refresh_payload_has_portfolio_context(payload),
        "applied": False,
        "reason": "no_portfolio_context_requested",
    }
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "refresh_product_bundle.py"),
        "--data-version",
        data_version,
        "--run-stamp",
        run_stamp,
        "--max-combo-size",
        str(max_combo_size),
    ]
    if (payload or {}).get("portfolioRows"):
        preview = preview_portfolio(payload)
        if not preview["canRunAnalysis"]:
            portfolio_context.update(
                {
                    "applied": False,
                    "reason": "portfolio_context_omitted_preview_error: "
                    + ("; ".join(preview.get("errors") or []) or "portfolio preview cannot be converted into analysis input."),
                }
            )
            preview = None
        if preview:
            portfolio_context.update(
                {
                    "reason": "portfolio_context_pending_validation",
                    "totalMarketValueKrw": preview.get("totalMarketValueKrw"),
                    "rowCount": len(preview.get("analysisRows") or []),
                }
            )
            rows = [
                row
                for row in preview["analysisRows"]
                if row.get("ticker") and row.get("ticker") != "__CASH__"
            ]
            try:
                validate_portfolio_weights(rows)
            except ValueError as exc:
                portfolio_context.update({"applied": False, "reason": f"portfolio_context_omitted_invalid_weights: {exc}"})
                rows = []
            if rows:
                total_amount_krw = preview["totalMarketValueKrw"]
                raw_budget_krw = (payload or {}).get("hedgeBudgetKrw")
                if raw_budget_krw not in (None, "") and total_amount_krw not in (None, 0):
                    budget_args = ["--base-total-krw", str(total_amount_krw), "--hedge-budgets-krw", str(float(raw_budget_krw))]
                    portfolio_context["hedgeBudgetKrw"] = float(raw_budget_krw)
                else:
                    budget_args = ["--hedge-budgets", build_hedge_budget_arg(payload, base_amount_krw=total_amount_krw)]
                portfolio_input_path = write_portfolio_input(rows, job_id=job_id)
                cleanup_paths.append(portfolio_input_path)
                cmd.extend(["--portfolio-input", str(portfolio_input_path)])
                cmd.extend(budget_args)
                portfolio_context.update(
                    {
                        "applied": True,
                        "reason": "portfolio_context_applied",
                        "portfolioInputPath": str(portfolio_input_path),
                        "totalMarketValueKrw": total_amount_krw,
                        "rowCount": len(rows),
                    }
                )
    else:
        raw_base_total_krw = (payload or {}).get("baseTotalKrw") or (payload or {}).get("baseAmountKrw")
        raw_budget_krw = (payload or {}).get("hedgeBudgetKrw")
        if raw_base_total_krw not in (None, "") and raw_budget_krw not in (None, ""):
            base_total_krw = float(raw_base_total_krw)
            if base_total_krw <= 0:
                raise ValueError("baseTotalKrw must be greater than zero.")
            hedge_budget_krw = float(raw_budget_krw)
            cmd.extend(["--base-total-krw", str(base_total_krw), "--hedge-budgets-krw", str(hedge_budget_krw)])
            portfolio_context.update(
                {
                    "applied": True,
                    "reason": "portfolio_amount_context_applied_without_portfolio_rows",
                    "totalMarketValueKrw": base_total_krw,
                    "hedgeBudgetKrw": hedge_budget_krw,
                }
            )
    if bool((payload or {}).get("forceRefreshRaw")):
        cmd.append("--force-refresh-raw")
    try:
        completed = run_subprocess_with_timeout(
            runner,
            cmd,
            cwd=str(ROOT.parent),
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise_subprocess_failure("market data refresh pipeline", cmd, completed, ROOT.parent, "market data refresh pipeline failed")
            raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "시장데이터 갱신 pipeline 실패")
        _update_run_job(
            job_id,
            status="completed",
            stage="complete",
            result={
                "ok": True,
                "mode": "full_rebuild",
                "dataVersion": data_version,
                "stdout": completed.stdout,
                "portfolioContext": portfolio_context,
            },
            error=None,
            completedAt=datetime.now().isoformat(timespec="seconds"),
        )
    finally:
        for path in cleanup_paths:
            try:
                Path(path).unlink(missing_ok=True)
            except OSError:
                pass


def refresh_payload_has_portfolio_context(payload):
    payload = payload or {}
    if payload.get("portfolioRows"):
        return True
    raw_base_total_krw = payload.get("baseTotalKrw") or payload.get("baseAmountKrw")
    raw_budget_krw = payload.get("hedgeBudgetKrw")
    return raw_base_total_krw not in (None, "") and raw_budget_krw not in (None, "")


def is_market_refresh_job(job):
    job = job or {}
    return (
        job.get("jobType") == MARKET_REFRESH_JOB_TYPE
        or job.get("jobType") in MARKET_REFRESH_MODES
        or job.get("mode") in MARKET_REFRESH_MODES
    )


def latest_running_market_refresh_job(mode=None):
    mode_filter = str(mode or "").strip() or None
    with RUN_JOBS_LOCK:
        job_ids = [
            job_id
            for job_id, job in RUN_JOBS.items()
            if is_market_refresh_job(job) and job.get("status") in {"queued", "running"}
            and (mode_filter is None or str(job.get("mode") or "").strip() == mode_filter)
        ]
    snapshots = [
        snapshot
        for snapshot in (_snapshot_run_job(job_id) for job_id in job_ids)
        if snapshot and snapshot.get("status") in {"queued", "running"}
    ]
    return snapshots[-1] if snapshots else None


def blocked_by_running_refresh_job_response(requested_mode, running_job):
    blocking_mode = str((running_job or {}).get("mode") or "").strip() or None
    return {
        "jobId": None,
        "jobType": MARKET_REFRESH_JOB_TYPE,
        "mode": requested_mode,
        "status": "blocked_by_existing_job",
        "stage": "blocked_by_existing_job",
        "currentStep": "다른 시장데이터 작업 진행 중",
        "estimatedRemainingMessage": "진행 중인 시장데이터 작업이 끝난 뒤 다시 시도하세요.",
        "attachedToExisting": False,
        "blockingJobId": (running_job or {}).get("jobId"),
        "blockingMode": blocking_mode,
        "blockingStatus": (running_job or {}).get("status"),
        "blockingStage": (running_job or {}).get("stage"),
        "error": None,
        "result": {
            "ok": False,
            "mode": requested_mode,
            "blocked": True,
            "blockingJobId": (running_job or {}).get("jobId"),
            "blockingMode": blocking_mode,
            "reason": f"Another market refresh job is already running in mode {blocking_mode or 'unknown'}.",
        },
    }


def launch_startup_market_refresh_if_needed(runner=subprocess.run, thread_factory=threading.Thread):
    today_stamp = datetime.now(KST).strftime("%Y%m%d")
    payload = {
        "mode": "market_data_only",
        "dataVersion": today_stamp,
        "runStamp": datetime.now(KST).strftime("%Y%m%dT%H%M%S"),
        "startupRefresh": True,
    }
    return launch_refresh_market_data_job(payload, runner=runner, thread_factory=thread_factory)


def launch_refresh_market_data_job(payload=None, runner=subprocess.run, thread_factory=threading.Thread):
    payload = payload or {}
    mode = str(payload.get("mode") or "market_data_only").strip() or "market_data_only"
    if mode not in MARKET_REFRESH_MODES:
        raise ValueError("mode must be one of market_data_only, portfolio_reanalysis, full_rebuild, intraday_nowcast.")
    force = bool(payload.get("force") or payload.get("forceFullRefresh"))
    has_portfolio_context = refresh_payload_has_portfolio_context(payload)
    if server_safe_mode() and not payload.get("forceServerRefresh"):
        status_payload = {}
        if mode == "intraday_nowcast":
            status_payload["intradayNowcast"] = latest_intraday_nowcast_status()
        else:
            freshness = load_data_freshness()
            status_payload["freshness"] = freshness
            status_payload["intradayNowcast"] = freshness.get("intradayNowcast")
        return server_safe_skip_refresh_job(
            uuid.uuid4().hex,
            refresh_job_type_for_mode(mode),
            mode,
            trigger_type_from_payload(payload),
            payload=payload,
            status_payload=status_payload,
        )
    same_mode_running_job = latest_running_market_refresh_job(mode=mode)
    if same_mode_running_job:
        same_mode_running_job["attachedToExisting"] = True
        return same_mode_running_job
    running_job = latest_running_market_refresh_job()
    if running_job:
        return blocked_by_running_refresh_job_response(mode, running_job)
    freshness = {} if mode == "intraday_nowcast" else load_data_freshness()
    intraday_status = latest_intraday_nowcast_status() if mode == "intraday_nowcast" else freshness.get("intradayNowcast")
    job_id = uuid.uuid4().hex
    with RUN_JOBS_LOCK:
        RUN_JOBS[job_id] = {
            "jobId": job_id,
            "jobType": MARKET_REFRESH_JOB_TYPE,
            "mode": mode,
            "startupRefresh": bool(payload.get("startupRefresh")),
            "status": "queued",
            "stage": "queued",
            "currentStep": "대기 중",
            "estimatedRemainingMessage": "시장데이터 갱신 작업 순서를 기다리고 있습니다.",
            "lastHeartbeatAt": _now_iso(),
            "elapsedSeconds": 0,
            "timeoutSeconds": JOB_TIMEOUT_SECONDS,
            "runId": None,
            "error": None,
            "diagnostics": None,
            "result": None,
            "freshness": freshness,
            "intradayNowcast": intraday_status,
            "startedAt": _now_iso(),
            "completedAt": None,
        }
    scenario_final_fresh = freshness.get("scenarioFinalFresh", True)
    stale_market_tickers = freshness.get("marketDataStaleTickers") or []
    failed_market_tickers = freshness.get("marketDataFailedTickers") or []
    market_data_only_current = bool(
        freshness.get("marketDataFresh")
        and scenario_final_fresh
        and not stale_market_tickers
        and not failed_market_tickers
    )
    market_data_attempted_but_not_fresh = bool(freshness.get("marketDataRefreshAttempted") and not freshness.get("marketDataFresh"))
    should_skip_latest = not force and (
        (mode == "market_data_only" and (market_data_only_current or market_data_attempted_but_not_fresh))
        or (mode == "full_rebuild" and freshness.get("skipHeavyRefresh"))
        or (mode == "intraday_nowcast" and intraday_status and intraday_status.get("fresh"))
    )
    job_type = refresh_job_type_for_mode(mode)
    trigger_type = trigger_type_from_payload(payload)
    create_refresh_job_record(job_id, job_type, trigger_type, status="PENDING")
    if should_skip_latest:
        if mode == "full_rebuild":
            skip_reason = "Market data and derived scenario/product artifacts are already current."
        elif mode == "intraday_nowcast":
            skip_reason = "Intraday 3-hour nowcast anchor is already current."
        elif market_data_attempted_but_not_fresh:
            skip_reason = (
                "Market data refresh was already attempted today for the target latest market date; "
                "remaining stale tickers are kept as warnings."
            )
        else:
            skip_reason = (
                "Market data and daily market-state outputs are already fresh. Use portfolio reanalysis for the selected portfolio."
                if has_portfolio_context
                else "Market data and daily market-state outputs are already fresh for the latest completed trading day."
            )
        _update_run_job(
            job_id,
            status="skipped_latest",
            stage="skipped_latest",
            result={
                "ok": True,
                "skipped": True,
                "reason": skip_reason,
                "freshness": freshness,
                "intradayNowcast": intraday_status,
                "portfolioContext": {
                    "requested": has_portfolio_context,
                    "applied": False,
                    "reason": "skipped_latest_with_portfolio_context"
                    if has_portfolio_context
                    else "skipped_latest_without_portfolio_context",
                },
            },
            completedAt=datetime.now().isoformat(timespec="seconds"),
        )
        update_refresh_job_record(job_id, "SKIPPED_FRESH", finished=True)
        record_data_snapshot_for_refresh(job_type, "SKIPPED_FRESH", payload=payload, result=_snapshot_run_job(job_id))
        return _snapshot_run_job(job_id)

    def worker_target():
        stop_heartbeat = threading.Event()
        _start_job_heartbeat(job_id, stop_heartbeat)
        try:
            update_refresh_job_record(job_id, "RUNNING", finished=False)
            _update_run_job(job_id, status="running", stage=mode)
            _run_refresh_market_data_job(job_id, payload, runner)
            snapshot = _snapshot_run_job(job_id) or {}
            update_refresh_job_record(job_id, "SUCCESS", finished=True)
            record_data_snapshot_for_refresh(job_type, "SUCCESS", payload=payload, result=snapshot.get("result") or snapshot)
        except Exception as exc:
            diagnostics = exception_diagnostics(exc)
            if diagnostics:
                print(
                    "HedgeMate refresh failed: "
                    + json.dumps(diagnostics, ensure_ascii=False),
                    file=sys.stderr,
                    flush=True,
                )
            update_refresh_job_record(job_id, "FAILED", error_message=sanitize_diagnostic_text(exc)[:4000], finished=True)
            _update_run_job(
                job_id,
                status="failed",
                stage="failed",
                error=sanitize_diagnostic_text(str(exc)),
                diagnostics=diagnostics,
                completedAt=datetime.now().isoformat(timespec="seconds"),
            )
        finally:
            stop_heartbeat.set()

    worker = thread_factory(target=worker_target, daemon=True)
    worker.start()
    return _snapshot_run_job(job_id)


def is_intraday_news_refresh_job(job):
    job = job or {}
    return job.get("jobType") == INTRADAY_NEWS_JOB_TYPE or job.get("mode") == INTRADAY_NEWS_JOB_TYPE


def latest_running_intraday_news_job():
    with RUN_JOBS_LOCK:
        job_ids = [
            job_id
            for job_id, job in RUN_JOBS.items()
            if is_intraday_news_refresh_job(job) and job.get("status") in {"queued", "running"}
        ]
    snapshots = [
        snapshot
        for snapshot in (_snapshot_run_job(job_id) for job_id in job_ids)
        if snapshot and snapshot.get("status") in {"queued", "running"}
    ]
    return snapshots[-1] if snapshots else None


def _run_intraday_news_overlay_job(job_id, payload, runner):
    data_version = str((payload or {}).get("dataVersion") or datetime.now(KST).strftime("%Y%m%d"))
    run_stamp = str((payload or {}).get("runStamp") or datetime.now(KST).strftime("%Y%m%dT%H%M%S"))
    trigger_reason = str((payload or {}).get("triggerReason") or (payload or {}).get("trigger_reason") or "scheduled")
    force = bool((payload or {}).get("force"))
    allow_network = not bool((payload or {}).get("noNetwork"))
    model = str((payload or {}).get("model") or "gemini-2.5-flash-lite")

    _update_run_job(job_id, stage="intraday news overlay", currentStep="refreshing intraday Top5 news overlay")
    news_run_id = f"intraday-news-refresh-{run_stamp}"
    cmd = [
        sys.executable,
        str(SCENARIO_RESEARCH_ROOT / "scripts" / "run_intraday_news_overlay_pipeline.py"),
        "--run-id",
        news_run_id,
        "--data-version",
        data_version,
        "--trigger-reason",
        trigger_reason,
        "--model",
        model,
    ]
    if force:
        cmd.append("--force")
    if not allow_network:
        cmd.append("--no-network")
    completed = run_subprocess_with_timeout(
        runner,
        cmd,
        cwd=str(ROOT.parent),
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise_subprocess_failure("intraday news overlay refresh", cmd, completed, ROOT.parent, "intraday news overlay refresh failed")
    status = latest_intraday_news_overlay_status()
    top5, _ = load_intraday_news_top5()
    _update_run_job(
        job_id,
        status="completed",
        stage="complete",
        currentStep="complete",
        intradayNewsOverlay=status,
        result={
            "ok": True,
            "mode": INTRADAY_NEWS_JOB_TYPE,
            "dataVersion": data_version,
            "runId": news_run_id,
            "stdout": completed.stdout,
            "intradayNewsOverlay": status,
            "intradayNewsTop5": top5,
        },
        error=None,
        completedAt=datetime.now().isoformat(timespec="seconds"),
    )


def launch_intraday_news_overlay_job(payload=None, runner=subprocess.run, thread_factory=threading.Thread):
    payload = payload or {}
    running_job = latest_running_intraday_news_job()
    if running_job:
        running_job["attachedToExisting"] = True
        return running_job

    force = bool(payload.get("force"))
    status = latest_intraday_news_overlay_status()
    job_id = uuid.uuid4().hex
    job_type = REFRESH_JOB_TYPE_NEWS_OVERLAY
    trigger_type = trigger_type_from_payload(payload)
    if server_safe_mode() and not payload.get("forceServerRefresh"):
        return server_safe_skip_refresh_job(
            job_id,
            job_type,
            INTRADAY_NEWS_JOB_TYPE,
            trigger_type,
            payload=payload,
            status_payload={"intradayNewsOverlay": status},
        )
    with RUN_JOBS_LOCK:
        RUN_JOBS[job_id] = {
            "jobId": job_id,
            "jobType": INTRADAY_NEWS_JOB_TYPE,
            "mode": INTRADAY_NEWS_JOB_TYPE,
            "status": "queued",
            "stage": "queued",
            "currentStep": "대기 중",
            "estimatedRemainingMessage": "뉴스 오버레이 작업 순서를 기다리고 있습니다.",
            "lastHeartbeatAt": _now_iso(),
            "elapsedSeconds": 0,
            "timeoutSeconds": JOB_TIMEOUT_SECONDS,
            "runId": None,
            "error": None,
            "diagnostics": None,
            "result": None,
            "intradayNewsOverlay": status,
            "startedAt": _now_iso(),
            "completedAt": None,
        }
    create_refresh_job_record(job_id, job_type, trigger_type, status="PENDING")

    if status.get("fresh") and not force:
        _update_run_job(
            job_id,
            status="skipped_latest",
            stage="skipped_latest",
            result={
                "ok": True,
                "skipped": True,
                "mode": INTRADAY_NEWS_JOB_TYPE,
                "reason": "Intraday news overlay is already current for the 09/15/21 KST window.",
                "intradayNewsOverlay": status,
            },
            completedAt=datetime.now().isoformat(timespec="seconds"),
        )
        update_refresh_job_record(job_id, "SKIPPED_FRESH", finished=True)
        record_data_snapshot_for_refresh(job_type, "SKIPPED_FRESH", payload=payload, result={"intradayNewsOverlay": status})
        return _snapshot_run_job(job_id)

    def worker_target():
        stop_heartbeat = threading.Event()
        _start_job_heartbeat(job_id, stop_heartbeat)
        try:
            update_refresh_job_record(job_id, "RUNNING", finished=False)
            _update_run_job(job_id, status="running", stage="intraday news overlay")
            _run_intraday_news_overlay_job(job_id, payload, runner)
            snapshot = _snapshot_run_job(job_id) or {}
            update_refresh_job_record(job_id, "SUCCESS", finished=True)
            record_data_snapshot_for_refresh(job_type, "SUCCESS", payload=payload, result=snapshot.get("result") or snapshot)
        except Exception as exc:
            diagnostics = exception_diagnostics(exc)
            if diagnostics:
                print(
                    "HedgeMate intraday news refresh failed: "
                    + json.dumps(diagnostics, ensure_ascii=False),
                    file=sys.stderr,
                    flush=True,
                )
            update_refresh_job_record(job_id, "FAILED", error_message=sanitize_diagnostic_text(exc)[:4000], finished=True)
            _update_run_job(
                job_id,
                status="failed",
                stage="failed",
                error=sanitize_diagnostic_text(str(exc)),
                diagnostics=diagnostics,
                completedAt=datetime.now().isoformat(timespec="seconds"),
            )
        finally:
            stop_heartbeat.set()

    worker = thread_factory(target=worker_target, daemon=True)
    worker.start()
    return _snapshot_run_job(job_id)


def persistent_running_refresh_job(job_type):
    try:
        return persistence_store().has_running_refresh_job(job_type)
    except Exception:
        return None


def run_scheduled_refresh_cycle(runner=subprocess.run, thread_factory=threading.Thread):
    SCHEDULER_STATE["lastCycleAt"] = _utc_iso()
    SCHEDULER_STATE["lastError"] = None
    results = []
    specs = [
        (
            REFRESH_JOB_TYPE_MARKET_DATA,
            launch_refresh_market_data_job,
            {
                "mode": "market_data_only",
                "schedulerRefresh": True,
                "dataVersion": datetime.now(KST).strftime("%Y%m%d"),
                "runStamp": datetime.now(KST).strftime("%Y%m%dT%H%M%S"),
            },
        ),
        (
            REFRESH_JOB_TYPE_INTRADAY_NOWCAST,
            launch_refresh_market_data_job,
            {
                "mode": "intraday_nowcast",
                "schedulerRefresh": True,
                "dataVersion": datetime.now(KST).strftime("%Y%m%d"),
                "runStamp": datetime.now(KST).strftime("%Y%m%dT%H%M%S"),
                "reuseRaw": True,
            },
        ),
        (
            REFRESH_JOB_TYPE_NEWS_OVERLAY,
            launch_intraday_news_overlay_job,
            {
                "schedulerRefresh": True,
                "dataVersion": datetime.now(KST).strftime("%Y%m%d"),
                "runStamp": datetime.now(KST).strftime("%Y%m%dT%H%M%S"),
            },
        ),
    ]
    for job_type, launcher, payload in specs:
        running = persistent_running_refresh_job(job_type)
        if running:
            results.append(
                {
                    "jobType": job_type,
                    "status": "SKIPPED_RUNNING",
                    "blockingJobId": running.get("job_id"),
                }
            )
            continue
        try:
            result = launcher(payload, runner=runner, thread_factory=thread_factory)
            results.append({"jobType": job_type, **(result or {})})
        except Exception as exc:
            SCHEDULER_STATE["lastError"] = str(exc)
            results.append({"jobType": job_type, "status": "ERROR", "error": str(exc)})
    return {"ok": not SCHEDULER_STATE.get("lastError"), "results": results}


def scheduler_loop(stop_event, runner=subprocess.run, thread_factory=threading.Thread, interval_seconds=SCHEDULER_INTERVAL_SECONDS):
    initial_delay = parse_int_env("HEDGEMATE_SCHEDULER_INITIAL_DELAY_SECONDS", interval_seconds)
    if initial_delay > 0 and stop_event.wait(initial_delay):
        return
    while not stop_event.is_set():
        try:
            run_scheduled_refresh_cycle(runner=runner, thread_factory=thread_factory)
        except Exception as exc:
            SCHEDULER_STATE["lastError"] = str(exc)
        if stop_event.wait(interval_seconds):
            break


def start_scheduler_thread(runner=subprocess.run, thread_factory=threading.Thread, interval_seconds=SCHEDULER_INTERVAL_SECONDS):
    if SCHEDULER_STATE.get("running"):
        return SCHEDULER_STATE
    stop_event = threading.Event()
    SCHEDULER_STATE.update(
        {
            "enabled": True,
            "running": True,
            "lastStartedAt": _utc_iso(),
            "lastError": None,
            "stopEvent": stop_event,
        }
    )
    worker = threading.Thread(
        target=scheduler_loop,
        args=(stop_event, runner, thread_factory, interval_seconds),
        daemon=True,
    )
    worker.start()
    SCHEDULER_STATE["thread"] = worker
    return SCHEDULER_STATE


def scheduler_status_value():
    if not SCHEDULER_STATE.get("enabled"):
        return "STOPPED"
    if SCHEDULER_STATE.get("lastError"):
        return "DEGRADED"
    return "RUNNING" if SCHEDULER_STATE.get("running") else "STOPPED"


def parse_int_env(name, default):
    raw = os.environ.get(name)
    if raw in (None, ""):
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def run_pipeline_for_request(payload, runner=subprocess.run, status_callback=None):
    prepared_request = payload if (payload or {}).get("_prepared_request") else prepare_run_request(payload, job_id=(payload or {}).get("jobId"))
    cmd = list(prepared_request["cmd"])

    if status_callback:
        status_callback("running HedgeMate analysis")
    completed = run_subprocess_with_timeout(
        runner,
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise_subprocess_failure("running HedgeMate analysis", cmd, completed, ROOT, "pipeline execution failed")
    run_id = extract_run_id_from_stdout(completed.stdout)
    run_id = run_id or prepared_request.get("runId") or (find_available_run_ids()[0] if find_available_run_ids() else None)
    product_bundle_updated = False
    backtest_run_id = None
    if hedge_run_ready_for_product_update(run_id):
        followup_commands, backtest_run_id = build_product_update_commands(
            run_id,
            portfolio_input_path=prepared_request.get("backtestPortfolioInputPath"),
            recommendation_scope=prepared_request.get("mode") or "portfolio",
            data_version=prepared_request.get("dataVersion"),
        )
        for followup_cmd in followup_commands:
            command_text = " ".join(str(part) for part in followup_cmd)
            if status_callback:
                if "run_scenario_backtest.py" in command_text:
                    status_callback("running scenario backtest")
                elif "apply_backtest_gate.py" in command_text:
                    status_callback("applying backtest gate")
                elif "update_active_bundle.py" in command_text:
                    status_callback("updating active dashboard bundle")
            followup = run_subprocess_with_timeout(
                runner,
                followup_cmd,
                cwd=str(ROOT.parent),
                capture_output=True,
                text=True,
                check=False,
            )
            if followup.returncode != 0:
                raise_subprocess_failure("product bundle update", followup_cmd, followup, ROOT.parent, "product bundle update failed")
        product_bundle_updated = bool(followup_commands)
    if not product_bundle_updated:
        raise RuntimeError(
            "active dashboard bundle was not updated for this analysis run; refusing to mark the job completed."
        )
    active_validation = validate_active_bundle_for_request(run_id, prepared_request)
    if not active_validation["ok"]:
        raise RuntimeError("active dashboard bundle validation failed: " + "; ".join(active_validation["errors"]))
    if status_callback:
        status_callback("completed")
    return {
        "ok": True,
        "runId": run_id,
        "backtestRunId": backtest_run_id,
        "productBundleUpdated": product_bundle_updated,
        "activeBundleUpdated": product_bundle_updated,
        "portfolioInput": prepared_request.get("backtestPortfolioInputPath"),
        "portfolioInputSha256": prepared_request.get("portfolioInputSha256"),
        "portfolioInputFingerprintHash": prepared_request.get("portfolioInputFingerprintHash"),
        "portfolioTickers": prepared_request.get("portfolioTickers") or [],
        "portfolioInputPersisted": bool(prepared_request.get("portfolioInputPersisted")),
        "activeBundleValidation": active_validation,
        "stdout": completed.stdout,
    }


def artifact_rel_from_path(path):
    if not path:
        return None
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = (SCENARIO_RESEARCH_ROOT / candidate).resolve()
    else:
        candidate = candidate.resolve()
    try:
        return str(candidate.relative_to(ROOT.parent.resolve())).replace("\\", "/")
    except ValueError:
        return None


def scenario_artifact(path):
    if not path:
        return None
    return artifact_rel_from_path(path)


def markdown_bullets(path, limit=8):
    if not path or not path.exists():
        return []
    bullets = []
    with path.open("r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if line.startswith("- "):
                bullets.append(line[2:].strip())
                if len(bullets) >= limit:
                    break
    return bullets


def latest_scenario_validation_payload():
    metadata_path = latest_path(SCENARIO_REPORT_DIR, "historical_validation_metadata_*.json")
    metadata = read_json(metadata_path, {}) if metadata_path else {}
    validation_path = None
    review_path = None
    if metadata:
        validation_csv = metadata.get("validation_csv")
        validation_review = metadata.get("validation_review")
        validation_path = Path(validation_csv) if validation_csv else None
        review_path = Path(validation_review) if validation_review else None
    if not validation_path or not validation_path.exists():
        validation_path = latest_path(SCENARIO_VALIDATION_DIR, "historical_validation_cases_*.csv")
    if not review_path or not review_path.exists():
        review_path = latest_path(SCENARIO_REPORT_DIR, "historical_validation_review_*.md")
    return {
        "metadata": metadata,
        "cases": read_csv_rows(validation_path)[:12] if validation_path else [],
        "reviewBullets": markdown_bullets(review_path, limit=8) if review_path else [],
        "artifacts": {
            "validationCsv": scenario_artifact(validation_path),
            "validationReview": scenario_artifact(review_path),
            "validationMetadata": scenario_artifact(metadata_path),
        },
    }


def state_counts(rows):
    counts = {}
    for row in rows:
        state = row.get("final_display_state") or row.get("display_state") or row.get("final_state") or "UNKNOWN"
        counts[str(state)] = counts.get(str(state), 0) + 1
    return [{"state": key, "count": counts[key]} for key in sorted(counts)]


def lens_summary(rows):
    grouped = {}
    for row in rows:
        lens = str(row.get("lens") or "unknown")
        current = grouped.setdefault(lens, {"lens": lens, "count": 0, "topScore": None, "topScenario": None})
        current["count"] += 1
        score = row.get("final_score")
        if isinstance(score, (int, float)) and (current["topScore"] is None or score > current["topScore"]):
            current["topScore"] = score
            current["topScenario"] = row.get("scenario_name_ko") or row.get("scenario_name") or row.get("scenario_code")
    return sorted(grouped.values(), key=lambda item: (item["topScore"] is None, -(item["topScore"] or 0), item["lens"]))


NEWS_ADJUSTED_WEIGHT = 0.15

NOWCAST_TO_SCENARIO_LINKS = {
    "krw_weakness_intraday": ["usd_strength_krw_weakness"],
    "kr_semiconductor_pressure_intraday": ["semiconductor_ai_cycle_shock"],
    "global_risk_spillover_intraday": [
        "acute_global_stress_liquidity_crunch",
        "china_trade_fragmentation_shock",
    ],
    "kr_risk_on_intraday": ["soft_landing_goldilocks"],
}


def numeric_or_none(value):
    parsed = parse_float(value)
    return parsed if isinstance(parsed, (int, float)) else None


def kst_date_from_iso(value):
    text = str(value or "").strip()
    if not text:
        return None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return text
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return text[:10] if re.match(r"\d{4}-\d{2}-\d{2}", text) else None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=KST)
    return parsed.astimezone(KST).date().isoformat()


def news_overlay_dates(news_top5, news_status):
    dates = []
    for item in news_top5 or []:
        if not isinstance(item, dict):
            continue
        date = kst_date_from_iso(item.get("date"))
        if date and date not in dates:
            dates.append(date)
    if not dates and isinstance(news_status, dict):
        for key in ("latestTimestampKst", "refreshWindowKst", "generatedAt"):
            date = kst_date_from_iso(news_status.get(key))
            if date and date not in dates:
                dates.append(date)
    return dates


def same_day_news_allowed(base_date, news_top5, news_status):
    base = kst_date_from_iso(base_date)
    return bool(base and base in news_overlay_dates(news_top5, news_status))


def news_items_for_base_date(base_date, news_top5, news_status):
    base = kst_date_from_iso(base_date)
    if not base:
        return []
    rows = [item for item in news_top5 or [] if isinstance(item, dict)]
    dated_rows = [item for item in rows if kst_date_from_iso(item.get("date"))]
    if dated_rows:
        return [item for item in dated_rows if kst_date_from_iso(item.get("date")) == base]
    return rows if same_day_news_allowed(base, rows, news_status) else []


def news_item_score(item):
    severity = numeric_or_none(item.get("severity"))
    confidence = numeric_or_none(item.get("confidence"))
    if confidence is not None and confidence <= 1:
        confidence *= 100.0
    if severity is None and confidence is None:
        return None
    if severity is None:
        return confidence
    if confidence is None:
        return severity
    return max(0.0, min(100.0, severity * 0.7 + confidence * 0.3))


def build_news_score_by_scenario(news_top5):
    scores = {}
    for item in news_top5 or []:
        score = news_item_score(item if isinstance(item, dict) else {})
        if score is None:
            continue
        links = item.get("scenarioLinks") if isinstance(item, dict) else []
        if not isinstance(links, list):
            links = [part for part in str(links or "").split("|") if part]
        for code in links:
            key = str(code or "").strip()
            if not key:
                continue
            scores[key] = max(scores.get(key, 0.0), score)
    return scores


def row_news_link_codes(row):
    codes = []
    for key in ("scenario_code", "nowcast_code", "code"):
        value = str(row.get(key) or "").strip()
        if value and value not in codes:
            codes.append(value)
        for mapped in NOWCAST_TO_SCENARIO_LINKS.get(value, []):
            if mapped not in codes:
                codes.append(mapped)
    return codes


def attach_intraday_news_adjustment(rows, news_top5, weight=NEWS_ADJUSTED_WEIGHT):
    news_scores = build_news_score_by_scenario(news_top5)
    adjusted = []
    for row in rows or []:
        next_row = dict(row)
        base_score = numeric_or_none(next_row.get("final_score") or next_row.get("score") or next_row.get("activation_weight"))
        news_score = None
        for code in row_news_link_codes(next_row):
            if code in news_scores:
                news_score = max(news_score or 0.0, news_scores[code])
        if base_score is not None and news_score is not None:
            adjusted_score = max(0.0, min(100.0, (1.0 - weight) * base_score + weight * news_score))
            next_row["baseFinalScore"] = round(base_score, 6)
            next_row["newsOverlayScore"] = round(news_score, 6)
            next_row["newsAdjustedScore"] = round(adjusted_score, 6)
            next_row["newsAdjustmentWeight"] = weight
            next_row["newsAdjustmentApplied"] = True
        else:
            next_row["newsAdjustmentApplied"] = False
        adjusted.append(next_row)
    return adjusted


def scenario_state_run_id_from_metadata(metadata, fallback):
    state_path = metadata.get("state_path")
    if not state_path:
        return fallback
    m = re.search(r"scenario_state_daily_(.+)\.csv$", Path(str(state_path)).name)
    return m.group(1) if m else fallback


def build_data_freshness_note(display_date, data_date, snapshot_metadata):
    if not display_date or not data_date or str(display_date) == str(data_date):
        return ""
    last_dates = snapshot_metadata.get("last_date_by_ticker", {}) if isinstance(snapshot_metadata, dict) else {}
    core_tickers = ["SPY", "QQQ", "TLT", "DIA", "VTI", "^VIX"]
    lagging = [ticker for ticker in core_tickers if last_dates.get(ticker) and str(last_dates[ticker]) < str(display_date)]
    if lagging:
        preview = ", ".join(lagging[:4])
        suffix = " 등" if len(lagging) > 4 else ""
        return f"실시간 화면은 오늘 장중 nowcast를 우선 사용합니다. {preview}{suffix}의 완료 일봉은 내부 검증 레이어에서만 보조로 처리합니다."
    return "실시간 화면은 오늘 장중 nowcast를 우선 사용합니다. 완료 일봉 레이어는 내부 검증에만 보조로 처리합니다."


NOWCAST_DISPLAY_FALLBACKS = {
    "kr_risk_on_intraday": {
        "nameKo": "한국장 장중 위험선호",
        "interpretationKo": "KOSPI200, 대형주 breadth, 반도체와 원화 흐름이 같은 방향으로 개선되는지 보는 장중 위험선호 nowcast입니다.",
    },
    "global_risk_spillover_intraday": {
        "nameKo": "글로벌 위험회피 한국 전이",
        "interpretationKo": "미국 ETF와 반도체 proxy, 원화 흐름을 함께 보며 글로벌 risk-off가 한국장으로 전이되는지 점검합니다.",
    },
    "krw_weakness_intraday": {
        "nameKo": "원화약세 장중 압력",
        "interpretationKo": "USD/KRW와 한국 위험자산 흐름을 함께 보며 원화 기준 포트폴리오의 장중 환율 부담을 점검합니다.",
    },
    "kr_semiconductor_pressure_intraday": {
        "nameKo": "한국 반도체 장중 부담",
        "interpretationKo": "삼성전자, SK하이닉스와 글로벌 반도체 proxy를 함께 보며 반도체 노출의 장중 부담을 점검합니다.",
    },
    "kr_defensive_rotation_intraday": {
        "nameKo": "한국장 방어주 상대 강세",
        "interpretationKo": "방어 업종 basket이 성장/민감 업종보다 상대적으로 강한지 확인하는 장중 rotation 신호입니다.",
    },
}


DAILY_SCENARIO_DISPLAY_FALLBACKS = {
    "usd_strength_krw_weakness": "달러강세/원화약세",
    "soft_landing_goldilocks": "골디락스/연착륙",
    "slowdown_recession_deflation_risk": "경기둔화/침체",
    "higher_for_longer_long_rate_shock": "장기금리 부담",
    "stagflation_reinflation_energy_shock": "스태그플레이션/에너지",
    "acute_global_stress_liquidity_crunch": "글로벌 스트레스",
    "china_trade_fragmentation_shock": "중국/무역 분절",
    "semiconductor_ai_cycle_shock": "반도체 AI 사이클",
    "korea_domestic_financial_stress": "한국 금융 스트레스",
    "geopolitical_escalation_supply_shock": "지정학/공급충격",
}


def text_looks_mojibake(value):
    text = str(value or "")
    if not text:
        return False
    markers = ("媛", "湲", "諛", "愿", "吏", "쨌", "?쒓", "?μ", "?꾩", "?먰")
    return ("?" in text and re.search(r"[가-힣]", text)) or text.count("?") >= 2 or any(marker in text for marker in markers)


def display_text(value, fallback=None):
    text = str(value or "").strip()
    if text and not text_looks_mojibake(text):
        return text
    return fallback or text


def select_primary_nowcast(nowcast_leaders):
    status_rank = {
        "RISK_OFF": 0,
        "STRESS": 1,
        "WATCH": 2,
        "RISK_ON": 3,
        "ACTIVE": 4,
        "OFF": 5,
        "NEUTRAL": 5,
    }

    def sort_key(row):
        state = str(row.get("status") or row.get("state") or "").upper()
        score = numeric_or_none(row.get("score")) or 0.0
        return (status_rank.get(state, 4), -score)

    rows = [row for row in nowcast_leaders or [] if isinstance(row, dict)]
    return sorted(rows, key=sort_key)[0] if rows else None


def build_primary_market_state(top_active_scenarios, nowcast_leaders, nowcast_status, data_as_of_date, display_date=None):
    nowcast_status = nowcast_status if isinstance(nowcast_status, dict) else {}
    daily_note = f"정식 일간 국면 데이터는 {data_as_of_date} 기준입니다." if data_as_of_date else "정식 일간 국면 데이터 기준일을 확인할 수 없습니다."
    nowcast_row = select_primary_nowcast(nowcast_leaders) if nowcast_status.get("fresh") else None
    if nowcast_row:
        code = str(nowcast_row.get("nowcast_code") or nowcast_row.get("scenario_code") or "")
        fallback = NOWCAST_DISPLAY_FALLBACKS.get(code, {})
        nowcast_as_of = nowcast_row.get("as_of_kst") or nowcast_status.get("latestTimestampKst")
        nowcast_data_date = nowcast_row.get("date_kst") or kst_date_from_iso(nowcast_as_of) or display_date
        return {
            "source": "intraday_nowcast",
            "isFresh": True,
            "code": code,
            "nameKo": display_text(nowcast_row.get("nowcast_name_ko") or nowcast_row.get("scenario_name_ko"), fallback.get("nameKo") or code),
            "lens": nowcast_row.get("lens"),
            "score": numeric_or_none(nowcast_row.get("score")),
            "confidence": numeric_or_none(nowcast_row.get("confidence")),
            "state": nowcast_row.get("status") or nowcast_row.get("state") or nowcast_row.get("display_state"),
            "asOfKst": nowcast_as_of,
            "dataAsOfDate": nowcast_data_date,
            "officialDailyDataAsOfDate": data_as_of_date,
            "interpretationKo": display_text(nowcast_row.get("interpretation_ko"), fallback.get("interpretationKo")),
            "officialDailyBasisNote": daily_note,
        }

    daily_row = next((row for row in top_active_scenarios or [] if isinstance(row, dict)), {})
    code = str(daily_row.get("scenario_code") or "")
    score = daily_row.get("final_score") or daily_row.get("score") or daily_row.get("activation_weight")
    confidence = daily_row.get("final_confidence") or daily_row.get("confidence")
    is_daily_fresh = bool(display_date and data_as_of_date and str(display_date) == str(data_as_of_date))
    fallback_name = DAILY_SCENARIO_DISPLAY_FALLBACKS.get(code, code)
    return {
        "source": "daily_final",
        "isFresh": is_daily_fresh,
        "code": code,
        "nameKo": display_text(daily_row.get("scenario_name_ko") or daily_row.get("scenario_name"), fallback_name),
        "lens": daily_row.get("lens"),
        "score": numeric_or_none(score),
        "confidence": numeric_or_none(confidence),
        "state": daily_row.get("final_display_state") or daily_row.get("display_state") or daily_row.get("status"),
        "asOfKst": None,
        "dataAsOfDate": data_as_of_date,
        "officialDailyDataAsOfDate": data_as_of_date,
        "interpretationKo": display_text(daily_row.get("market_interpretation_ko")),
        "officialDailyBasisNote": daily_note,
    }


def build_market_state_freshness(display_date, data_as_of_date, nowcast_status, primary_market_state=None):
    nowcast_status = nowcast_status if isinstance(nowcast_status, dict) else {}
    intraday_as_of = nowcast_status.get("latestTimestampKst")
    if not intraday_as_of and isinstance(primary_market_state, dict):
        intraday_as_of = primary_market_state.get("asOfKst")
    return {
        "displayDate": display_date,
        "primarySource": primary_market_state.get("source") if isinstance(primary_market_state, dict) else None,
        "primaryDataAsOfDate": primary_market_state.get("dataAsOfDate") if isinstance(primary_market_state, dict) else data_as_of_date,
        "primaryAsOfKst": primary_market_state.get("asOfKst") if isinstance(primary_market_state, dict) else None,
        "dailyFinalDataAsOfDate": data_as_of_date,
        "intradayNowcastAsOfKst": intraday_as_of,
        "intradayFresh": bool(nowcast_status.get("fresh")),
        "dailyFinalStale": bool(display_date and data_as_of_date and str(display_date) != str(data_as_of_date)),
    }


def apply_intraday_news_to_primary_market_state(primary_market_state, news_top5, news_status):
    summary = {
        "applied": False,
        "weight": NEWS_ADJUSTED_WEIGHT,
        "scope": "market_state_primary_only",
        "target": "primaryMarketState",
        "baseScoreField": "primaryMarketState.score",
        "adjustedScoreField": "primaryMarketState.newsAdjustedScore",
        "newsDates": news_overlay_dates(news_top5, news_status),
    }
    if not isinstance(primary_market_state, dict) or not news_top5:
        summary["skipReason"] = "missing_primary_or_news"
        return primary_market_state, summary

    status = news_status if isinstance(news_status, dict) else {}
    if status.get("fallbackUsed") or status.get("provider") != "gemini":
        summary["skipReason"] = "news_provider_not_gemini_validated"
        summary["provider"] = status.get("provider")
        summary["fallbackUsed"] = bool(status.get("fallbackUsed"))
        primary_market_state["newsAdjustmentApplied"] = False
        return primary_market_state, summary

    if primary_market_state.get("source") == "intraday_nowcast":
        base_date = kst_date_from_iso(primary_market_state.get("asOfKst"))
    elif primary_market_state.get("source") == "daily_final":
        base_date = kst_date_from_iso(primary_market_state.get("dataAsOfDate"))
    else:
        base_date = None
    summary["baseDate"] = base_date

    matching_news = news_items_for_base_date(base_date, news_top5, news_status)
    if not matching_news:
        summary["skipReason"] = "news_date_mismatch"
        primary_market_state["newsAdjustmentApplied"] = False
        return primary_market_state, summary

    adjusted_row = attach_intraday_news_adjustment([primary_market_state], matching_news)[0]
    if not adjusted_row.get("newsAdjustmentApplied"):
        summary["skipReason"] = "no_matching_news_scenario"
        primary_market_state["newsAdjustmentApplied"] = False
        return primary_market_state, summary

    primary_market_state.update(
        {
            "baseScore": adjusted_row.get("baseFinalScore"),
            "newsOverlayScore": adjusted_row.get("newsOverlayScore"),
            "newsAdjustedScore": adjusted_row.get("newsAdjustedScore"),
            "newsAdjustmentWeight": adjusted_row.get("newsAdjustmentWeight"),
            "newsAdjustmentApplied": True,
            "score": adjusted_row.get("newsAdjustedScore"),
        }
    )
    summary["applied"] = True
    return primary_market_state, summary


def load_scenario_dashboard_data(run_id=None, include_intraday_news=True):
    product_manifest = read_product_manifest()
    manifest = read_active_manifest()
    runs = find_scenario_run_ids()
    manifest_run_id = scenario_manifest_final_run_id(manifest)
    product_run_id = product_manifest_final_run_id(product_manifest)
    target_run_id = run_id or manifest_run_id or (runs[0] if runs else None) or product_run_id
    if not target_run_id:
        raise FileNotFoundError("Scenario research run not found")

    final_path = SCENARIO_FINAL_DIR / f"final_market_state_daily_{target_run_id}.csv"
    if not run_id and not final_path.exists() and runs:
        target_run_id = runs[0]
        final_path = SCENARIO_FINAL_DIR / f"final_market_state_daily_{target_run_id}.csv"
    if not final_path.exists():
        raise FileNotFoundError(f"Scenario research run not found: {target_run_id}")

    confidence_path = SCENARIO_FINAL_DIR / f"scenario_confidence_{target_run_id}.csv"
    top_path = SCENARIO_FINAL_DIR / f"top_active_scenarios_{target_run_id}.json"
    metadata_path = SCENARIO_REPORT_DIR / f"final_market_state_metadata_{target_run_id}.json"
    summary_path = SCENARIO_REPORT_DIR / f"final_market_state_summary_{target_run_id}.md"
    target_vector_path = SCENARIO_VECTOR_DIR / f"current_scenario_vector_{target_run_id}.json"
    target_vector_path = target_vector_path if target_vector_path.exists() else None
    manifest_vector_path = (
        resolve_manifest_artifact(manifest, "active_final_scenario_vector", SCENARIO_VECTOR_DIR)
        or resolve_manifest_artifact(manifest, "active_scenario_vector_json", SCENARIO_VECTOR_DIR)
        or resolve_manifest_artifact(manifest, "active_scenario_vector", SCENARIO_VECTOR_DIR)
    )
    product_vector_path = (
        resolve_product_artifact(product_manifest, "finalScenarioVector", SCENARIO_VECTOR_DIR)
        or resolve_product_artifact(product_manifest, "scenarioVector", SCENARIO_VECTOR_DIR)
    )
    if run_id and run_id != manifest_run_id:
        vector_path = target_vector_path or product_vector_path or manifest_vector_path or latest_path(SCENARIO_VECTOR_DIR, "current_scenario_vector_*.json")
    else:
        vector_path = target_vector_path or manifest_vector_path or product_vector_path or latest_path(SCENARIO_VECTOR_DIR, "current_scenario_vector_*.json")
    nowcast_path = latest_path(SCENARIO_NOWCAST_DIR, "current_intraday_nowcast_*.json")
    event_metadata_path = resolve_product_artifact(product_manifest, "eventOverlayMetadata", SCENARIO_REPORT_DIR) or latest_path(SCENARIO_REPORT_DIR, "event_overlay_metadata_*.json")
    event_review_path = latest_path(SCENARIO_REPORT_DIR, "event_overlay_review_*.md")
    event_daily_path = latest_path(SCENARIO_EVENT_DIR, "event_overlay_daily_*.csv")
    integration_dashboard_path = latest_path(SCENARIO_REPORT_DIR, "integration_review_dashboard_*.html")
    phase4_dashboard_path = latest_path(SCENARIO_REPORT_DIR, "phase4_review_dashboard_*.html")
    phase5_dashboard_path = latest_path(SCENARIO_REPORT_DIR, "phase5_event_overlay_dashboard_*.html")

    final_rows = read_csv_rows(final_path)
    top_payload = read_json(top_path, {}) or {}
    metadata = read_json(metadata_path, {}) or {}
    scenario_state_run_id = scenario_state_run_id_from_metadata(metadata, target_run_id)
    snapshot_metadata_path = SCENARIO_REPORT_DIR / f"scenario_snapshot_metadata_{scenario_state_run_id}.json"
    snapshot_metadata = read_json(snapshot_metadata_path, {}) if snapshot_metadata_path.exists() else {}
    vector_rows = read_json_or_csv_rows(vector_path)
    nowcast_rows = read_json(nowcast_path, []) if nowcast_path else []
    nowcast_status = latest_intraday_nowcast_status()
    news_status = {}
    news_top5 = []
    news_top5_path = None
    news_metadata_path = None
    if include_intraday_news:
        news_status = latest_intraday_news_overlay_status()
        news_top5, news_top5_path = load_intraday_news_top5()
        news_metadata_path = latest_intraday_news_metadata_path()
    event_metadata = read_json(event_metadata_path, {}) if event_metadata_path else {}
    validation = latest_scenario_validation_payload()

    data_as_of_date = top_payload.get("date") or metadata.get("date")
    if not data_as_of_date and final_rows:
        data_as_of_date = max(str(row.get("date")) for row in final_rows if row.get("date"))
    display_as_of_date = display_reference_date()
    data_freshness_note = build_data_freshness_note(display_as_of_date, data_as_of_date, snapshot_metadata)
    rows_for_date = [row for row in final_rows if str(row.get("date")) == str(data_as_of_date)] if data_as_of_date else []
    if not rows_for_date:
        rows_for_date = final_rows[-20:]

    top_market_rows = sorted(
        rows_for_date,
        key=lambda row: row.get("final_score") if isinstance(row.get("final_score"), (int, float)) else float("-inf"),
        reverse=True,
    )[:12]
    top_active_scenarios = top_payload.get("top_active_scenarios", [])
    news_adjusted_summary = {
        "applied": False,
        "weight": NEWS_ADJUSTED_WEIGHT,
        "scope": "market_state_primary_only",
        "target": "primaryMarketState",
        "baseScoreField": "primaryMarketState.score",
        "adjustedScoreField": "primaryMarketState.newsAdjustedScore",
    }
    vector_leaders = sorted(
        vector_rows if isinstance(vector_rows, list) else [],
        key=lambda row: row.get("score") if isinstance(row.get("score"), (int, float)) else float("-inf"),
        reverse=True,
    )[:8]
    nowcast_leaders = sorted(
        nowcast_rows if isinstance(nowcast_rows, list) else [],
        key=lambda row: row.get("score") if isinstance(row.get("score"), (int, float)) else float("-inf"),
        reverse=True,
    )[:8]
    primary_market_state = build_primary_market_state(
        top_active_scenarios,
        nowcast_leaders,
        nowcast_status,
        data_as_of_date,
        display_as_of_date,
    )
    if include_intraday_news:
        primary_market_state, news_adjusted_summary = apply_intraday_news_to_primary_market_state(
            primary_market_state,
            news_top5,
            news_status,
        )
    market_state_freshness = build_market_state_freshness(
        display_as_of_date,
        data_as_of_date,
        nowcast_status,
        primary_market_state,
    )

    artifacts = {
        "finalMarketState": scenario_artifact(final_path),
        "scenarioConfidence": scenario_artifact(confidence_path),
        "topActiveJson": scenario_artifact(top_path),
        "finalSummary": scenario_artifact(summary_path),
        "finalMetadata": scenario_artifact(metadata_path),
        "scenarioVector": scenario_artifact(vector_path),
        "nowcastVector": scenario_artifact(nowcast_path),
        "eventOverlayDaily": scenario_artifact(event_daily_path),
        "eventOverlayMetadata": scenario_artifact(event_metadata_path),
        "eventOverlayReview": scenario_artifact(event_review_path),
        "integrationDashboard": scenario_artifact(integration_dashboard_path),
        "phase4Dashboard": scenario_artifact(phase4_dashboard_path),
        "phase5Dashboard": scenario_artifact(phase5_dashboard_path),
    }
    if include_intraday_news:
        artifacts["latestIntradayNewsOverlay"] = scenario_artifact(news_top5_path)
        artifacts["intradayNewsOverlayMetadata"] = scenario_artifact(news_metadata_path)
    artifacts.update(validation.get("artifacts", {}))
    artifacts = {key: value for key, value in artifacts.items() if value}

    payload = {
        "runId": target_run_id,
        "runs": runs,
        "asOfDate": display_as_of_date,
        "dataAsOfDate": data_as_of_date,
        "generatedAt": datetime.fromtimestamp(final_path.stat().st_mtime).isoformat(timespec="seconds"),
        "meta": {
            "pipelinePhase": metadata.get("pipeline_phase"),
            "engineVersion": top_payload.get("merge_engine_version") or metadata.get("merge_engine_version"),
            "finalRowCount": metadata.get("final_row_count") or len(final_rows),
            "overlayRowCount": metadata.get("overlay_row_count"),
            "validationCases": validation.get("metadata", {}).get("case_count"),
            "validationOkCases": validation.get("metadata", {}).get("ok_case_count"),
            "eventArticleCount": event_metadata.get("article_count"),
            "anchorDate": snapshot_metadata.get("anchor_date"),
            "dataQualityStatus": snapshot_metadata.get("data_quality_status"),
        },
        "dataFreshnessNote": data_freshness_note,
        "intradayNowcastStatus": nowcast_status,
        "primaryMarketState": primary_market_state,
        "marketStateFreshness": market_state_freshness,
        "summaryBullets": markdown_bullets(summary_path, limit=8),
        "topActiveScenarios": top_active_scenarios,
        "topMarketRows": top_market_rows,
        "stateCounts": state_counts(rows_for_date),
        "lensSummary": lens_summary(rows_for_date),
        "scenarioVectorLeaders": vector_leaders,
        "nowcastLeaders": nowcast_leaders,
        "eventOverlay": {
            "metadata": event_metadata,
            "rows": read_csv_rows(event_daily_path)[:10] if event_daily_path else [],
            "reviewBullets": markdown_bullets(event_review_path, limit=6) if event_review_path else [],
        },
        "validation": validation,
        "artifacts": artifacts,
    }
    if include_intraday_news:
        payload.update(
            {
                "intradayNewsOverlayStatus": news_status,
                "intradayNewsTop5": news_top5[:5],
                "intradayNewsScoreAdjustment": news_adjusted_summary,
                "latestIntradayNewsOverlay": scenario_artifact(news_top5_path),
            }
        )
    return payload


def load_dashboard_data(run_id, product_manifest=None, include_execution_plan=True):
    features_path = OUTPUT_PROCESSED_DIR / f"features_summary_{run_id}.csv"
    if not features_path.exists():
        raise FileNotFoundError(f"Run not found: {run_id}")
    product_manifest = read_product_manifest() if product_manifest is None else product_manifest
    product_bundle = active_bundle(product_manifest)
    use_active_artifacts = run_id == (product_bundle.get("hedgemate_run") or product_manifest.get("active_hedgemate_run"))

    result_md = DOC_RESULT_DIR / f"01_실행결과_{run_id}.md"
    review_md = DOC_RESULT_DIR / f"03_결과검토_{run_id}.md"
    draft_md = DOC_RESULT_DIR / f"02_분석리포트_초안_{run_id}.md"

    summary_meta, next_actions = parse_summary_markdown(result_md)
    features = read_csv_rows(features_path)
    asset_sensitivities = read_csv_rows(OUTPUT_PROCESSED_DIR / f"asset_risk_sensitivity_{run_id}.csv")
    dq_rows = read_csv_rows(OUTPUT_REPORT_DIR / f"dq_result_{run_id}.csv")
    top_hedges = read_csv_rows(OUTPUT_REPORT_DIR / f"hes_components_{run_id}.csv")
    portfolio_compare = read_csv_rows(OUTPUT_REPORT_DIR / f"portfolio_compare_{run_id}.csv")
    single_asset_compare = read_csv_rows(OUTPUT_REPORT_DIR / f"single_asset_compare_{run_id}.csv")
    recommendation_artifact_warnings = []
    if use_active_artifacts:
        portfolio_multi_path, warning = resolve_active_gated_recommendation_artifact(product_manifest, "portfolioMulti")
        if warning:
            recommendation_artifact_warnings.append(warning)
        portfolio_1to1_path, warning = resolve_active_gated_recommendation_artifact(product_manifest, "portfolio1to1")
        if warning:
            recommendation_artifact_warnings.append(warning)
    else:
        portfolio_multi_path = OUTPUT_REPORT_DIR / f"portfolio_multi_hedge_{run_id}.csv"
        portfolio_1to1_path = OUTPUT_REPORT_DIR / f"portfolio_1to1_hedge_{run_id}.csv"
    portfolio_multi = read_csv_rows(portfolio_multi_path) if portfolio_multi_path else []
    portfolio_1to1 = read_csv_rows(portfolio_1to1_path) if portfolio_1to1_path else []
    single_asset_multi = read_csv_rows(OUTPUT_REPORT_DIR / f"single_asset_hedge_multi_{run_id}.csv")
    single_asset_1to1 = read_csv_rows(OUTPUT_REPORT_DIR / f"single_asset_hedge_1to1_{run_id}.csv")
    metric_validation = read_csv_rows(OUTPUT_REPORT_DIR / f"metric_validation_{run_id}.csv")

    worst_risk_assets = sorted(
        [row for row in features if row.get("mdd_1y_krw") is not None],
        key=lambda row: row["mdd_1y_krw"],
    )[:8]

    for row in top_hedges:
        row["displayName"] = display_name(row.get("ticker"))
    for row in worst_risk_assets:
        row["displayName"] = display_name(row.get("ticker"))
    for row in asset_sensitivities:
        row["displayName"] = display_name(row.get("ticker"))
    for row in portfolio_compare:
        row["displayScenario"] = humanize_scenario(row.get("scenario"))
    for row in single_asset_compare:
        row["displayScenario"] = humanize_scenario(row.get("scenario"))
    for row in portfolio_multi + portfolio_1to1 + single_asset_multi + single_asset_1to1:
        enrich_candidate_display(row)
        if include_execution_plan:
            enrich_execution_plan(row)

    dq_summary = {"pass": 0, "warn": 0, "fail": 0}
    for row in dq_rows:
        status = str(row.get("status", "")).lower()
        if status == "pass":
            dq_summary["pass"] += 1
        elif status == "warn":
            dq_summary["warn"] += 1
        elif status == "fail":
            dq_summary["fail"] += 1

    validation_summary = {
        "pass": sum(1 for row in metric_validation if row.get("status") == "PASS"),
        "fail": sum(1 for row in metric_validation if row.get("status") == "FAIL"),
    }

    product_artifacts = product_manifest.get("artifacts", {}) if isinstance(product_manifest.get("artifacts"), dict) else {}
    artifacts = {
        "marketRaw": f"outputs/raw/raw_market_daily_{run_id}.csv",
        "fxRaw": f"outputs/raw/raw_fx_daily_{run_id}.csv",
        "benchmarkRaw": f"outputs/raw/raw_benchmark_daily_{run_id}.csv",
        "features": f"outputs/processed/features_summary_{run_id}.csv",
        "assetSensitivity": f"outputs/processed/asset_risk_sensitivity_{run_id}.csv",
        "dq": f"outputs/reports/dq_result_{run_id}.csv",
        "hes": f"outputs/reports/hes_components_{run_id}.csv",
        "assetSensitivitySummary": f"outputs/reports/asset_sensitivity_summary_{run_id}.md",
        "portfolioCompare": f"outputs/reports/portfolio_compare_{run_id}.csv",
        "portfolio1to1": product_artifacts.get("portfolio1to1") if use_active_artifacts else f"outputs/reports/portfolio_1to1_hedge_{run_id}.csv",
        "portfolioMulti": product_artifacts.get("portfolioMulti") if use_active_artifacts else f"outputs/reports/portfolio_multi_hedge_{run_id}.csv",
        "singleAssetCompare": f"outputs/reports/single_asset_compare_{run_id}.csv",
        "singleAsset1to1": f"outputs/reports/single_asset_hedge_1to1_{run_id}.csv",
        "singleAssetMulti": f"outputs/reports/single_asset_hedge_multi_{run_id}.csv",
        "resultMd": f"docs/STEP_1/04_실행결과/01_실행결과_{run_id}.md",
        "draftMd": f"docs/STEP_1/04_실행결과/02_분석리포트_초안_{run_id}.md",
        "reviewMd": f"docs/STEP_1/04_실행결과/03_결과검토_{run_id}.md",
    }

    base_portfolio_weights = []
    input_path = None
    if product_bundle:
        input_path = product_bundle.get("portfolio_input_fingerprint", {}).get("path")
    if not input_path and product_manifest:
        input_path = product_manifest.get("portfolio_input_fingerprint", {}).get("path")
    
    if input_path:
        full_path = ROOT / input_path
        if full_path.exists():
            base_portfolio_weights = read_csv_rows(full_path)
    if not base_portfolio_weights:
        fallback_path = ROOT / "inputs" / "portfolio_weights.csv"
        if fallback_path.exists():
            base_portfolio_weights = read_csv_rows(fallback_path)
            
    for row in base_portfolio_weights:
        if "weight_pct" in row:
            try:
                row["weightPct"] = float(row["weight_pct"])
            except ValueError:
                row["weightPct"] = 0.0

    return {
        "runId": run_id,
        "generatedAt": latest_generated_at(run_id),
        "singleAssetTicker": parse_single_asset_ticker(single_asset_compare),
        "meta": {
            "baseCurrency": "KRW",
            "analysisPeriod": summary_meta.get("분석기간"),
            "targetTickers": summary_meta.get("대상 티커"),
            "fetchedTickers": summary_meta.get("수집 성공 티커"),
            "stressDays": summary_meta.get("위기구간(stress) 일수"),
            "benchmark": summary_meta.get("위기구간 벤치마크"),
            "cachedRaw": summary_meta.get("raw 재사용 여부(동일 data_version 재실행)"),
            "cachedFx": summary_meta.get("FX raw 재사용 여부"),
            "recommendationArtifactWarnings": recommendation_artifact_warnings,
            "usesActiveGatedRecommendations": bool(use_active_artifacts and not recommendation_artifact_warnings),
        },
        "dqSummary": dq_summary,
        "validationSummary": validation_summary,
        "portfolioCompare": portfolio_compare,
        "singleAssetCompare": single_asset_compare,
        "portfolioOneToOne": portfolio_1to1,
        "portfolioMulti": portfolio_multi,
        "singleAssetOneToOne": single_asset_1to1,
        "singleAssetMulti": single_asset_multi,
        "portfolioBestDetail": choose_best_detail(portfolio_multi, portfolio_1to1),
        "singleAssetBestDetail": choose_best_detail(single_asset_multi, single_asset_1to1),
        "assetSensitivities": asset_sensitivities,
        "topHedges": top_hedges,
        "worstRiskAssets": worst_risk_assets,
        "basePortfolioWeights": base_portfolio_weights,
        "nextActions": next_actions,
        "artifacts": artifacts,
        "activeManifest": product_manifest if use_active_artifacts else {},
    }


PRODUCT_DASHBOARD_COMPACT_HEDGE_META_KEYS = (
    "runId",
    "generatedAt",
    "singleAssetTicker",
    "meta",
    "dqSummary",
    "validationSummary",
    "portfolioBestDetail",
    "singleAssetBestDetail",
    "basePortfolioWeights",
    "nextActions",
    "artifacts",
)

PRODUCT_DASHBOARD_COMPACT_HEDGE_ROW_KEYS = (
    "portfolioCompare",
    "singleAssetCompare",
    "portfolioOneToOne",
    "portfolioMulti",
    "singleAssetOneToOne",
    "singleAssetMulti",
    "assetSensitivities",
    "topHedges",
    "worstRiskAssets",
)

PRODUCT_DASHBOARD_COMPACT_ROW_PREVIEW_LIMIT = 5
INTRADAY_NEWS_MANIFEST_KEYS = {
    "latestIntradayNewsOverlay",
    "intradayNewsOverlayStatus",
    "intradayNewsTop5",
}
INTRADAY_NEWS_ARTIFACT_KEYS = {
    "latestIntradayNewsOverlay",
    "intradayNewsOverlayMetadata",
}


def strip_intraday_news_from_product_manifest(manifest):
    if not isinstance(manifest, dict):
        return manifest
    sanitized = dict(manifest)
    for key in INTRADAY_NEWS_MANIFEST_KEYS:
        sanitized.pop(key, None)
    artifacts = sanitized.get("artifacts")
    if isinstance(artifacts, dict):
        sanitized["artifacts"] = {
            key: value
            for key, value in artifacts.items()
            if key not in INTRADAY_NEWS_ARTIFACT_KEYS
        }
    return sanitized


def compact_product_dashboard_payload(dashboard, hedge_row_limit=PRODUCT_DASHBOARD_COMPACT_ROW_PREVIEW_LIMIT):
    if not isinstance(dashboard, dict):
        return dashboard
    compact = dict(dashboard)
    hedge = compact.get("hedge")
    if not isinstance(hedge, dict):
        compact["payloadCompact"] = {"enabled": True, "hedgeCompacted": False}
        return compact

    compact_hedge = {
        key: hedge.get(key)
        for key in PRODUCT_DASHBOARD_COMPACT_HEDGE_META_KEYS
        if key in hedge
    }
    hedge_row_counts = {}
    for key in PRODUCT_DASHBOARD_COMPACT_HEDGE_ROW_KEYS:
        value = hedge.get(key)
        if isinstance(value, list):
            hedge_row_counts[key] = len(value)
            compact_hedge[key] = value[:hedge_row_limit]
        elif key in hedge:
            compact_hedge[key] = value

    compact_hedge["compact"] = True
    compact_hedge["rowCounts"] = hedge_row_counts
    compact["hedge"] = compact_hedge
    compact["payloadCompact"] = {
        "enabled": True,
        "hedgeCompacted": True,
        "hedgeRowPreviewLimit": hedge_row_limit,
        "hedgeRowCounts": hedge_row_counts,
    }
    return compact


def backtest_case_key(row):
    case_id = str(row.get("case_id") or "").strip()
    scenario = str(row.get("expected_scenario_code") or "").strip()
    case_name = str(row.get("case_name") or "").strip()
    if case_id:
        return case_id
    if scenario or case_name:
        return f"{scenario}|{case_name}"
    return ""


def backtest_case_label(row):
    return str(row.get("case_name") or row.get("case_id") or row.get("expected_scenario_code") or "").strip()


def is_target_backtest_row(row):
    return str(row.get("is_target_scenario") or "").strip().upper() in {"Y", "TRUE", "1"}


def numeric_values(rows, key):
    values = []
    for row in rows:
        value = row.get(key)
        if isinstance(value, (int, float)):
            values.append(float(value))
    return values


def number_summary(values, digits=2):
    if not values:
        return {"min": None, "avg": None, "max": None}
    return {
        "min": round(min(values), digits),
        "avg": round(sum(values) / len(values), digits),
        "max": round(max(values), digits),
    }


def unique_case_labels(rows):
    labels = {}
    for row in rows:
        key = backtest_case_key(row)
        if not key:
            continue
        labels[key] = backtest_case_label(row) or key
    return [labels[key] for key in sorted(labels)]


def pipe_separated_counts(rows, key):
    counts = {}
    for row in rows:
        for value in str(row.get(key) or "").split("|"):
            ticker = value.strip()
            if ticker:
                counts[ticker] = counts.get(ticker, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


FORMAL_GATE_BLOCKER_DETAILS = {
    "cash_baseline_lag": {
        "labelKo": "현금 기준 대비 열위",
        "technicalExplanation": "The hedge did not beat a same-notional cash-only de-risking baseline in target stress rows.",
        "nextAction": "Improve the cash-baseline comparison or keep the candidate review-only.",
    },
    "bootstrap_not_robust": {
        "labelKo": "부트스트랩 신뢰도 부족",
        "technicalExplanation": "Target stress bootstrap confidence did not meet the robust formal threshold.",
        "nextAction": "Increase sample coverage or downgrade fragile candidates to reference-only.",
    },
    "cash_bootstrap_not_robust": {
        "labelKo": "현금 기준 부트스트랩 부족",
        "technicalExplanation": "Cash-baseline bootstrap confidence did not meet the robust formal threshold.",
        "nextAction": "Add stronger cash-baseline evidence before considering formal execution.",
    },
    "validation_thin": {
        "labelKo": "검증 표본 부족",
        "technicalExplanation": "The target stress sample exists but is too thin for formal use.",
        "nextAction": "Require additional stress cases or keep the row as review-only.",
    },
    "validation_insufficient": {
        "labelKo": "검증 이력 부족",
        "technicalExplanation": "The target stress validation history is insufficient.",
        "nextAction": "Add newer or longer historical validation evidence.",
    },
    "liquidity_below_formal": {
        "labelKo": "유동성 기준 미달",
        "technicalExplanation": "60-day ADV evidence is missing or below the formal notional threshold.",
        "nextAction": "Refresh ADV evidence or exclude the candidate from formal recommendations.",
    },
    "turnover_above_formal": {
        "labelKo": "회전율 기준 초과",
        "technicalExplanation": "Target stress turnover is above the formal threshold.",
        "nextAction": "Lower turnover or move the action to review-only.",
    },
    "return_drag_reference": {
        "labelKo": "수익률 훼손 검토 필요",
        "technicalExplanation": "Pre-backtest scoring kept the candidate reference-only because return drag remains material.",
        "nextAction": "Confirm risk reduction compensates for return drag before promotion.",
    },
    "reference_only": {
        "labelKo": "참고 후보",
        "technicalExplanation": "The candidate remains reference-only after formal gate checks.",
        "nextAction": "Use as research context, not an execution recommendation.",
    },
    "fail_gate": {
        "labelKo": "하드 게이트 실패",
        "technicalExplanation": "The candidate failed a hard backtest or product safety gate.",
        "nextAction": "Do not promote until the failing gate is resolved.",
    },
    "validation_missing": {
        "labelKo": "검증 자료 없음",
        "technicalExplanation": "No matching backtest evidence was attached to the candidate.",
        "nextAction": "Generate matching backtest rows before formal use.",
    },
    "target_worsened": {
        "labelKo": "대상 스트레스 악화",
        "technicalExplanation": "Target stress backtest worsened at least one risk metric.",
        "nextAction": "Keep blocked unless the candidate improves target stress metrics.",
    },
    "unclassified_non_formal": {
        "labelKo": "미분류 비정식 후보",
        "technicalExplanation": "The row is not formal but no known blocker code was assigned.",
        "nextAction": "Classify the blocker before relying on the audit.",
    },
}


def formal_gate_blocker_detail(code):
    detail = FORMAL_GATE_BLOCKER_DETAILS.get(str(code or "").strip())
    if detail:
        return {"code": code, **detail}
    return {
        "code": code,
        "labelKo": str(code or "unknown"),
        "technicalExplanation": "No blocker explanation mapping is available.",
        "nextAction": "Add a blocker mapping before treating this as a resolved audit item.",
    }


def build_formal_gate_blocker_summary(formal_gate_rows):
    rows = formal_gate_rows or []
    counts = pipe_separated_counts(rows, "formal_gate_blockers")
    items = []
    for code, count in counts.items():
        affected = [
            row
            for row in rows
            if has_pipe_token(row, "formal_gate_blockers", code)
        ]
        detail = formal_gate_blocker_detail(code)
        items.append(
            {
                **detail,
                "count": count,
                "affectedCandidates": [
                    {
                        "candidate": row.get("candidate_name") or row.get("candidate_label") or row.get("candidate_ticker") or row.get("candidate_combo") or "",
                        "scenario": row.get("expected_scenario_code") or row.get("risk_sleeve") or "",
                        "status": row.get("recommendation_status") or "",
                    }
                    for row in affected[:8]
                ],
            }
        )
    return {
        "rowCount": len(rows),
        "blockerCounts": counts,
        "items": items,
        "unknownBlockers": [code for code in counts if code not in FORMAL_GATE_BLOCKER_DETAILS],
    }


def has_pipe_separated_value(row, key):
    return any(value.strip() for value in str(row.get(key) or "").split("|"))


def has_pipe_token(row, key, token):
    return token in {value.strip() for value in str(row.get(key) or "").split("|") if value.strip()}


def formal_gate_cash_baseline_summary(rows):
    lag_rows = [row for row in rows if has_pipe_token(row, "formal_gate_blockers", "cash_baseline_lag")]
    if not lag_rows:
        return {
            "lagCandidateRows": 0,
            "targetLagStressRows": 0,
            "avgCashNetStressDelta": number_summary([], digits=6),
            "topRows": [],
        }
    return {
        "lagCandidateRows": len(lag_rows),
        "targetLagStressRows": int(sum(parse_float(row.get("target_lags_cash_count")) or 0 for row in lag_rows)),
        "avgCashNetStressDelta": number_summary(numeric_values(lag_rows, "target_avg_cash_net_stress_delta"), digits=6),
        "minCashNetStressDelta": number_summary(numeric_values(lag_rows, "target_min_cash_net_stress_delta"), digits=6),
        "avgCashNetMddDelta": number_summary(numeric_values(lag_rows, "target_avg_cash_net_mdd_delta"), digits=6),
        "avgCashNetCvarDelta": number_summary(numeric_values(lag_rows, "target_avg_cash_net_cvar_delta"), digits=6),
        "topRows": lag_rows[:8],
    }


def formal_gate_bootstrap_summary(rows):
    blocked_rows = [
        row
        for row in rows
        if has_pipe_token(row, "formal_gate_blockers", "bootstrap_not_robust")
        or has_pipe_token(row, "formal_gate_blockers", "cash_bootstrap_not_robust")
    ]
    cash_blocked_rows = [row for row in rows if has_pipe_token(row, "formal_gate_blockers", "cash_bootstrap_not_robust")]
    if not blocked_rows:
        return {
            "notRobustCandidateRows": 0,
            "cashNotRobustCandidateRows": 0,
            "targetBootstrapRows": 0,
            "targetBootstrapRobustRows": 0,
            "targetCashBootstrapRows": 0,
            "targetCashBootstrapRobustRows": 0,
            "pImprove": number_summary([], digits=4),
            "cashPImprove": number_summary([], digits=4),
            "topRows": [],
        }
    return {
        "notRobustCandidateRows": len(blocked_rows),
        "cashNotRobustCandidateRows": len(cash_blocked_rows),
        "targetBootstrapRows": int(sum(parse_float(row.get("target_bootstrap_count")) or 0 for row in blocked_rows)),
        "targetBootstrapRobustRows": int(sum(parse_float(row.get("target_bootstrap_robust_count")) or 0 for row in blocked_rows)),
        "targetCashBootstrapRows": int(sum(parse_float(row.get("target_cash_bootstrap_count")) or 0 for row in blocked_rows)),
        "targetCashBootstrapRobustRows": int(sum(parse_float(row.get("target_cash_bootstrap_robust_count")) or 0 for row in blocked_rows)),
        "pImprove": number_summary(numeric_values(blocked_rows, "target_bootstrap_min_p_improve"), digits=4),
        "avgPImprove": number_summary(numeric_values(blocked_rows, "target_bootstrap_avg_p_improve"), digits=4),
        "cashPImprove": number_summary(numeric_values(blocked_rows, "target_cash_bootstrap_min_p_improve"), digits=4),
        "cashAvgPImprove": number_summary(numeric_values(blocked_rows, "target_cash_bootstrap_avg_p_improve"), digits=4),
        "topRows": blocked_rows[:8],
    }


def is_short_evaluation_row(row, min_days=60):
    value = parse_float(row.get("evaluation_day_count"))
    return value is not None and value < min_days


def price_coverage_blocker_type(no_common_rows, pre_inception_rows, missing_price_rows):
    if not no_common_rows and not missing_price_rows:
        return "PRICE_COVERED_FOR_EVALUATED_WINDOWS"
    if missing_price_rows and pre_inception_rows:
        return "MIXED_PRE_INCEPTION_AND_MISSING_PRICE"
    if missing_price_rows:
        return "MISSING_PRICE_DATA"
    if no_common_rows and len(pre_inception_rows) == len(no_common_rows):
        return "PRE_INCEPTION_ONLY"
    if pre_inception_rows:
        return "PRE_INCEPTION_PARTIAL"
    return "OTHER_PRICE_WINDOW_GAP"


def backtest_quality_level(summary):
    if summary["rowCount"] <= 0 or summary["evaluatedRows"] <= 0:
        return "MISSING"
    if summary["targetEvaluatedRows"] <= 0 or summary["evaluatedCaseCount"] < 3:
        return "LOW"
    if summary["insufficientCaseCount"] > 0 or (summary["evaluationDays"]["min"] or 0) < 60 or summary["evaluatedCaseCount"] < 8:
        return "MEDIUM"
    return "HIGH"


def backtest_quality_warnings(summary):
    warnings = []
    if summary.get("cashLagRows", 0) > 0:
        warnings.append(f"현금화 기준보다 약한 hedge stress 결과 {summary['cashLagRows']}건")
    if summary.get("priceGapCaseCount", 0) > 0:
        names = ", ".join(summary.get("priceGapCaseNames", [])[:3])
        warnings.append(f"가격 히스토리 범위 밖 stress case {summary['priceGapCaseCount']}개: {names}")
    if summary.get("noCommonPriceCaseCount", 0) > 0:
        names = ", ".join(summary.get("noCommonPriceCaseNames", [])[:3])
        warnings.append(f"공통 가격일이 없어 직접검증 불가 stress case {summary['noCommonPriceCaseCount']}개: {names}")
    if summary.get("priceCoverageBlockerType") == "PRE_INCEPTION_ONLY":
        warnings.append("가격 공백은 missing data가 아니라 현재 포트폴리오 종목의 상장 전 stress window에서 발생했습니다.")
    if summary["insufficientCaseCount"] > 0:
        names = ", ".join(summary["insufficientCaseNames"][:3])
        warnings.append(f"검증 불가 stress case {summary['insufficientCaseCount']}개: {names}")
    min_days = summary["evaluationDays"]["min"]
    if min_days is not None and min_days < 60:
        names = ", ".join(summary.get("shortEvaluationCaseNames", [])[:3])
        suffix = f": {names}" if names else ""
        warnings.append(f"가장 짧은 평가 구간이 {min_days:g}거래일이라 장기 stress 검증으로는 약합니다{suffix}.")
    if summary["targetEvaluatedRows"] <= 0:
        warnings.append("후보의 대상 시나리오와 직접 맞는 백테스트가 없습니다.")
    if summary["evaluatedCaseCount"] < 8:
        warnings.append(f"평가된 stress case가 {summary['evaluatedCaseCount']}개라 regime 표본이 제한적입니다.")
    if summary.get("targetBootstrapRows", 0) > 0 and summary.get("targetBootstrapRobustRows", 0) < summary.get("targetBootstrapRows", 0):
        warnings.append("대상 stress case 전체에서 bootstrap 신뢰가 충분히 강하지 않습니다.")
    if summary.get("targetCashBootstrapRows", 0) > 0 and summary.get("targetCashBootstrapRobustRows", 0) < summary.get("targetCashBootstrapRows", 0):
        warnings.append("대상 stress case 전체에서 cash-baseline 대비 bootstrap 신뢰가 충분히 강하지 않습니다.")
    if summary.get("preInceptionTickerCounts"):
        tickers = ", ".join(list(summary["preInceptionTickerCounts"])[:5])
        warnings.append(f"Pre-inception price history blocks stress validation for: {tickers}")
    if summary.get("missingPriceTickerCounts"):
        tickers = ", ".join(list(summary["missingPriceTickerCounts"])[:5])
        warnings.append(f"Missing price history blocks stress validation for: {tickers}")
    return warnings


def build_backtest_coverage_summary(rows):
    evaluated = [row for row in rows if str(row.get("backtest_status") or "").upper() == "EVALUATED"]
    insufficient = [row for row in rows if str(row.get("backtest_status") or "").upper() == "INSUFFICIENT_HISTORY"]
    short_evaluation_rows = [row for row in evaluated if is_short_evaluation_row(row)]
    price_gap_rows = [row for row in rows if str(row.get("price_window_status") or "").upper() == "OUT_OF_PRICE_RANGE"]
    no_common_price_rows = [row for row in rows if str(row.get("price_window_status") or "").upper() in {"NO_COMMON_PRICE_DATES", "PRICE_DATA_MISSING"}]
    pre_inception_rows = [row for row in rows if has_pipe_separated_value(row, "pre_inception_tickers")]
    missing_price_rows = [row for row in rows if has_pipe_separated_value(row, "missing_price_tickers")]
    cash_lag_rows = [row for row in rows if str(row.get("hedge_vs_cash_verdict") or "").upper() == "LAGS_CASH"]
    target_rows = [row for row in rows if is_target_backtest_row(row)]
    target_evaluated = [row for row in target_rows if str(row.get("backtest_status") or "").upper() == "EVALUATED"]
    target_worsened = [row for row in target_evaluated if str(row.get("verdict") or "").upper() == "WORSENED"]
    target_improved = [row for row in target_evaluated if str(row.get("verdict") or "").upper() == "IMPROVED"]
    target_insufficient = [row for row in target_rows if str(row.get("verdict") or "").upper() == "INSUFFICIENT_HISTORY"]
    target_bootstrap_rows = [row for row in target_evaluated if str(row.get("bootstrap_confidence") or "").strip()]
    target_bootstrap_robust = [
        row for row in target_bootstrap_rows if str(row.get("bootstrap_confidence") or "").upper() == "ROBUST_IMPROVE"
    ]
    target_bootstrap_uncertain = [
        row for row in target_bootstrap_rows if str(row.get("bootstrap_confidence") or "").upper() == "UNCERTAIN"
    ]
    target_bootstrap_worse = [
        row for row in target_bootstrap_rows if str(row.get("bootstrap_confidence") or "").upper() == "ROBUST_WORSE"
    ]
    target_cash_bootstrap_rows = [row for row in target_evaluated if str(row.get("cash_bootstrap_confidence") or "").strip()]
    target_cash_bootstrap_robust = [
        row for row in target_cash_bootstrap_rows if str(row.get("cash_bootstrap_confidence") or "").upper() == "ROBUST_IMPROVE"
    ]
    target_cash_bootstrap_uncertain = [
        row for row in target_cash_bootstrap_rows if str(row.get("cash_bootstrap_confidence") or "").upper() == "UNCERTAIN"
    ]
    target_cash_bootstrap_worse = [
        row for row in target_cash_bootstrap_rows if str(row.get("cash_bootstrap_confidence") or "").upper() == "ROBUST_WORSE"
    ]
    evaluated_case_names = unique_case_labels(evaluated)
    insufficient_case_names = unique_case_labels(insufficient)
    short_evaluation_case_names = unique_case_labels(short_evaluation_rows)
    price_gap_case_names = unique_case_labels(price_gap_rows)
    no_common_price_case_names = unique_case_labels(no_common_price_rows)
    pre_inception_case_names = unique_case_labels(pre_inception_rows)
    missing_price_case_names = unique_case_labels(missing_price_rows)
    price_window_status_counts = {}
    cash_verdict_counts = {}
    bootstrap_confidence_counts = {}
    cash_bootstrap_confidence_counts = {}
    for row in rows:
        status = str(row.get("price_window_status") or "").strip() or "UNKNOWN"
        price_window_status_counts[status] = price_window_status_counts.get(status, 0) + 1
        cash_status = str(row.get("hedge_vs_cash_verdict") or "").strip()
        if cash_status:
            cash_verdict_counts[cash_status] = cash_verdict_counts.get(cash_status, 0) + 1
        bootstrap_status = str(row.get("bootstrap_confidence") or "").strip()
        if bootstrap_status:
            bootstrap_confidence_counts[bootstrap_status] = bootstrap_confidence_counts.get(bootstrap_status, 0) + 1
        cash_bootstrap_status = str(row.get("cash_bootstrap_confidence") or "").strip()
        if cash_bootstrap_status:
            cash_bootstrap_confidence_counts[cash_bootstrap_status] = cash_bootstrap_confidence_counts.get(cash_bootstrap_status, 0) + 1
    summary = {
        "rowCount": len(rows),
        "evaluatedRows": len(evaluated),
        "insufficientRows": len(insufficient),
        "shortEvaluationRows": len(short_evaluation_rows),
        "outOfPriceRangeRows": len(price_gap_rows),
        "noCommonPriceRows": len(no_common_price_rows),
        "preInceptionBlockedRows": len(pre_inception_rows),
        "missingPriceBlockedRows": len(missing_price_rows),
        "cashLagRows": len(cash_lag_rows),
        "targetEvaluatedRows": len(target_evaluated),
        "targetImprovedRows": len(target_improved),
        "targetWorsenedRows": len(target_worsened),
        "targetInsufficientRows": len(target_insufficient),
        "evaluatedCaseCount": len(evaluated_case_names),
        "insufficientCaseCount": len(insufficient_case_names),
        "shortEvaluationCaseCount": len(short_evaluation_case_names),
        "priceGapCaseCount": len(price_gap_case_names),
        "noCommonPriceCaseCount": len(no_common_price_case_names),
        "preInceptionBlockedCaseCount": len(pre_inception_case_names),
        "missingPriceBlockedCaseCount": len(missing_price_case_names),
        "evaluatedCaseNames": evaluated_case_names[:12],
        "insufficientCaseNames": insufficient_case_names[:12],
        "shortEvaluationCaseNames": short_evaluation_case_names[:12],
        "priceGapCaseNames": price_gap_case_names[:12],
        "noCommonPriceCaseNames": no_common_price_case_names[:12],
        "preInceptionBlockedCaseNames": pre_inception_case_names[:12],
        "missingPriceBlockedCaseNames": missing_price_case_names[:12],
        "priceCoverageBlockerType": price_coverage_blocker_type(no_common_price_rows, pre_inception_rows, missing_price_rows),
        "priceWindowStatusCounts": price_window_status_counts,
        "priceBlockingTickerCounts": pipe_separated_counts(rows, "price_blocking_tickers"),
        "preInceptionTickerCounts": pipe_separated_counts(rows, "pre_inception_tickers"),
        "missingPriceTickerCounts": pipe_separated_counts(rows, "missing_price_tickers"),
        "cashBaselineVerdictCounts": cash_verdict_counts,
        "evaluatedScenarioCount": len({str(row.get("expected_scenario_code") or "") for row in evaluated if row.get("expected_scenario_code")}),
        "evaluationDays": number_summary(numeric_values(evaluated, "evaluation_day_count")),
        "priceCoverageRatio": number_summary(numeric_values(evaluated, "price_coverage_ratio")),
        "implementationCost": number_summary(numeric_values(evaluated, "implementation_cost"), digits=6),
        "recurringRebalanceCost": number_summary(numeric_values(evaluated, "recurring_rebalance_cost"), digits=6),
        "totalPathCost": number_summary(numeric_values(evaluated, "total_path_cost"), digits=6),
        "transactionCostBps": number_summary(numeric_values(evaluated, "transaction_cost_bps")),
        "slippageBps": number_summary(numeric_values(evaluated, "slippage_bps")),
        "bootstrapConfidenceCounts": bootstrap_confidence_counts,
        "cashBootstrapConfidenceCounts": cash_bootstrap_confidence_counts,
        "targetBootstrapRows": len(target_bootstrap_rows),
        "targetBootstrapRobustRows": len(target_bootstrap_robust),
        "targetBootstrapUncertainRows": len(target_bootstrap_uncertain),
        "targetBootstrapWorseRows": len(target_bootstrap_worse),
        "targetBootstrapPImprove": number_summary(numeric_values(target_bootstrap_rows, "net_stress_delta_p_improve"), digits=4),
        "targetCashBootstrapRows": len(target_cash_bootstrap_rows),
        "targetCashBootstrapRobustRows": len(target_cash_bootstrap_robust),
        "targetCashBootstrapUncertainRows": len(target_cash_bootstrap_uncertain),
        "targetCashBootstrapWorseRows": len(target_cash_bootstrap_worse),
        "targetCashBootstrapPImprove": number_summary(numeric_values(target_cash_bootstrap_rows, "cash_net_stress_delta_p_improve"), digits=4),
    }
    summary["qualityLevel"] = backtest_quality_level(summary)
    summary["warnings"] = backtest_quality_warnings(summary)
    return summary


def load_backtest_payload(manifest):
    path = resolve_product_artifact(manifest, "backtestCsv", OUTPUT_VALIDATION_DIR)
    rows = read_csv_rows(path) if path else []
    formal_gate_audit_path = resolve_product_artifact(manifest, "formalGateAuditCsv", OUTPUT_REPORT_DIR)
    formal_gate_rows = read_csv_rows(formal_gate_audit_path) if formal_gate_audit_path else []
    verdict_counts = {}
    status_counts_payload = {}
    for row in rows:
        verdict = str(row.get("verdict") or "UNKNOWN")
        verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1
        status = str(row.get("backtest_status") or "UNKNOWN")
        status_counts_payload[status] = status_counts_payload.get(status, 0) + 1
    return {
        "rows": rows[:40],
        "rowCount": len(rows),
        "verdictCounts": verdict_counts,
        "statusCounts": status_counts_payload,
        "coverageSummary": build_backtest_coverage_summary(rows),
        "summaryArtifact": scenario_artifact(resolve_product_artifact(manifest, "backtestSummary", OUTPUT_REPORT_DIR)),
        "gateSummaryArtifact": scenario_artifact(resolve_product_artifact(manifest, "backtestGateSummary", OUTPUT_REPORT_DIR)),
        "attributionCsvArtifact": scenario_artifact(resolve_product_artifact(manifest, "backtestAttributionCsv", OUTPUT_REPORT_DIR)),
        "attributionSummaryArtifact": scenario_artifact(resolve_product_artifact(manifest, "backtestAttributionSummary", OUTPUT_REPORT_DIR)),
        "formalGateAuditCsvArtifact": scenario_artifact(formal_gate_audit_path),
        "formalGateAuditSummaryArtifact": scenario_artifact(resolve_product_artifact(manifest, "formalGateAuditSummary", OUTPUT_REPORT_DIR)),
        "formalGateAuditSummary": {
            "rowCount": len(formal_gate_rows),
            "blockerCounts": pipe_separated_counts(formal_gate_rows, "formal_gate_blockers"),
            "blockerSummary": build_formal_gate_blocker_summary(formal_gate_rows),
            "statusCounts": {
                status: sum(1 for row in formal_gate_rows if str(row.get("recommendation_status") or "") == status)
                for status in sorted({str(row.get("recommendation_status") or "") for row in formal_gate_rows if row.get("recommendation_status")})
            },
            "cashBaselineAudit": formal_gate_cash_baseline_summary(formal_gate_rows),
            "bootstrapAudit": formal_gate_bootstrap_summary(formal_gate_rows),
            "topRows": formal_gate_rows[:12],
        },
    }


def recommendation_rows_from_hedge(hedge):
    hedge = hedge or {}
    single_asset_rows = [
        row
        for key in ("singleAssetOneToOne", "singleAssetMulti")
        for row in hedge.get(key, []) or []
        if row and (row.get("candidate_ticker") or row.get("candidate_combo"))
    ]
    single_asset_rows_are_gated = any(row.get("backtest_gate_status") for row in single_asset_rows)
    selected_rows = (
        single_asset_rows
        if hedge.get("singleAssetTicker") and single_asset_rows_are_gated
        else [
            row
            for key in ("portfolioOneToOne", "portfolioMulti")
            for row in hedge.get(key, []) or []
            if row and (row.get("candidate_ticker") or row.get("candidate_combo"))
        ]
    )
    return [row for row in selected_rows if row.get("recommendation_status")]


def recommendation_status_counts(rows):
    counts = {
        "PASS_RECOMMEND": 0,
        "REFERENCE_ONLY": 0,
        "FAIL_GATE": 0,
        "INSUFFICIENT_DATA": 0,
    }
    for row in rows or []:
        status = str(row.get("recommendation_status") or "UNKNOWN")
        counts[status] = counts.get(status, 0) + 1
    return counts


def event_overlay_trade_gate_allowed(event_status):
    if event_status is None:
        return True
    usage = str(
        event_status.get("trade_gate_usage")
        or event_status.get("recommendation_usage")
        or ""
    ).strip().lower()
    return usage in {"enabled", "trade_gate_enabled", "live_trade_gate_enabled", "production_trade_gate_enabled"}


def build_recommendation_decision(hedge, backtest, data_freshness, event_status=None):
    rows = recommendation_rows_from_hedge(hedge)
    counts = recommendation_status_counts(rows)
    coverage = (backtest or {}).get("coverageSummary") or {}
    formal_gate_summary = (backtest or {}).get("formalGateAuditSummary") or {}
    cash_baseline_audit = formal_gate_summary.get("cashBaselineAudit") or {}
    bootstrap_audit = formal_gate_summary.get("bootstrapAudit") or {}
    reasons = []
    blockers = []

    freshness_status = str((data_freshness or {}).get("status") or "").lower()
    if freshness_status == "stale":
        reason_text = "; ".join(user_facing_freshness_reasons(data_freshness)) or "시장/시나리오 데이터 상태 확인이 필요합니다."
        blockers.append("stale_data")
        reasons.append(f"데이터 갱신 확인 필요: {reason_text}")

    if counts.get("PASS_RECOMMEND", 0) <= 0:
        blockers.append("no_formal_recommendation")
        reasons.append("백테스트 게이트를 통과한 정식 추천 후보가 없습니다.")

    if not coverage.get("rowCount"):
        blockers.append("missing_backtest")
        reasons.append("과거 stress backtest 산출물이 없어 실행 추천으로 승격할 수 없습니다.")

    quality_level = str(coverage.get("qualityLevel") or "").upper()
    if coverage.get("rowCount") and quality_level and quality_level != "HIGH":
        blockers.append("validation_quality_not_high")
        reasons.append(f"Backtest 검증 강도가 {quality_level}이라 HIGH 기준에 미달해 정식 실행 추천을 차단합니다.")

    if not event_overlay_trade_gate_allowed(event_status):
        blockers.append("event_overlay_not_trade_safe")
        reasons.append("이벤트 오버레이가 fixture/review-only 상태이거나 trade gate 사용으로 활성화되지 않아 정식 실행 추천을 차단합니다.")

    cash_lag_rows = int(coverage.get("cashLagRows") or 0)
    if cash_lag_rows > 0:
        reasons.append(f"{cash_lag_rows}개 검증행에서 같은 금액을 현금으로 남기는 기준보다 약했습니다.")

    no_common_cases = int(coverage.get("noCommonPriceCaseCount") or 0)
    if no_common_cases > 0:
        if coverage.get("priceCoverageBlockerType") == "PRE_INCEPTION_ONLY":
            tickers = ", ".join(list((coverage.get("preInceptionTickerCounts") or {}).keys())[:5])
            reasons.append(f"{no_common_cases}개 stress case는 missing price가 아니라 상장 전 가격 이력 한계로 직접 검증하지 못했습니다: {tickers}")
        else:
            reasons.append(f"{no_common_cases}개 stress case는 공통 가격일 부족으로 직접 검증하지 못했습니다.")

    insufficient_cases = int(coverage.get("insufficientCaseCount") or 0)
    if insufficient_cases > 0:
        reasons.append(f"{insufficient_cases}개 stress case는 히스토리 부족으로 충분히 검증되지 않았습니다.")

    evaluated_cases = int(coverage.get("evaluatedCaseCount") or 0)
    if coverage.get("rowCount") and evaluated_cases < 8:
        reasons.append(f"평가된 stress case가 {evaluated_cases}개라 regime 표본이 제한적입니다.")

    can_execute = not blockers
    if can_execute:
        state = "FORMAL_RECOMMENDATION_AVAILABLE"
        severity = "ok"
        title = "정식 추천 후보가 있습니다."
        copy = "그래도 헷지 후보는 현금 보유 기준, stress 표본, 데이터 상태를 함께 확인한 뒤 실행해야 합니다."
        section_title = "정식 추천과 검증 근거"
        section_copy = "정식 추천 후보를 먼저 보여주고, 참고/탈락 후보는 비교 감사용으로 분리합니다."
    elif "stale_data" in blockers:
        state = "BLOCKED_STALE_DATA"
        severity = "danger"
        title = "데이터 상태 확인이 필요해 실행 추천을 차단했습니다."
        copy = "가격 데이터와 시나리오 스냅샷 상태가 맞지 않는 경우에는 좋은 후보처럼 보여도 실행 추천으로 취급하지 않습니다."
        section_title = "실행 추천 차단 · 후보 감사 목록"
        section_copy = "아래 항목은 현재 실행 권고가 아니라, 갱신 후 다시 검증해야 할 후보 목록입니다."
    elif counts.get("PASS_RECOMMEND", 0) <= 0:
        state = "NO_FORMAL_RECOMMENDATION"
        severity = "danger" if counts.get("FAIL_GATE", 0) else "warning"
        title = "현재 검증 기준에서 실행 추천 가능한 헷지 후보가 없습니다."
        copy = "참고용 후보가 있더라도 현금화 기준 대비 초과효과, 직접 stress 표본, backtest evidence가 부족하면 추천으로 보지 않습니다."
        section_title = "실행 추천 불가 · 후보 감사 목록"
        section_copy = "아래 카드는 매수 권고가 아니라 왜 탈락/참고 판정을 받았는지 확인하는 감사 목록입니다."
    else:
        state = "BLOCKED_VALIDATION"
        severity = "warning"
        title = "검증 조건이 약해 실행 추천을 보류했습니다."
        copy = "정식 추천 후보가 일부 있어도 backtest 산출물이나 stress 검증 조건이 약하면 실행 후보로 취급하지 않습니다."
        section_title = "추천 보류 · 후보 감사 목록"
        section_copy = "아래 후보는 추가 검증 전까지 실행 권고가 아닙니다."

    return {
        "state": state,
        "severity": severity,
        "canExecuteRecommendations": can_execute,
        "title": title,
        "copy": copy,
        "sectionTitle": section_title,
        "sectionCopy": section_copy,
        "primaryReasons": reasons[:8],
        "blockers": blockers,
        "statusCounts": counts,
        "candidateCount": len(rows),
        "formalRecommendationCount": counts.get("PASS_RECOMMEND", 0),
        "referenceOnlyCount": counts.get("REFERENCE_ONLY", 0),
        "failGateCount": counts.get("FAIL_GATE", 0),
        "cashLagRows": cash_lag_rows,
        "cashBaselineAudit": cash_baseline_audit,
        "bootstrapAudit": bootstrap_audit,
        "evaluatedStressCaseCount": evaluated_cases,
        "insufficientStressCaseCount": insufficient_cases,
        "noCommonPriceStressCaseCount": no_common_cases,
    }


ACTION_STATUSES = ("FORMAL_ACTION", "REVIEW_ACTION", "RESEARCH_ONLY", "FAIL_ACTION", "NO_ACTION")
ACTION_STATUS_ALIASES = {
    "FORMAL": "FORMAL_ACTION",
    "FORMAL_RECOMMENDATION": "FORMAL_ACTION",
    "PASS_RECOMMEND": "FORMAL_ACTION",
    "REVIEW": "REVIEW_ACTION",
    "REVIEW_ONLY": "REVIEW_ACTION",
    "REFERENCE_ONLY": "REVIEW_ACTION",
    "REFERENCE": "REVIEW_ACTION",
    "RESEARCH": "RESEARCH_ONLY",
    "RESEARCH_ONLY": "RESEARCH_ONLY",
    "INFO_ONLY": "RESEARCH_ONLY",
    "FAIL": "FAIL_ACTION",
    "FAILED": "FAIL_ACTION",
    "FAIL_GATE": "FAIL_ACTION",
    "BLOCKED": "FAIL_ACTION",
    "NO_ACTION": "NO_ACTION",
    "NONE": "NO_ACTION",
    "NO_VALID_ACTION": "NO_ACTION",
    "INSUFFICIENT_DATA": "NO_ACTION",
}
ACTION_STATUS_FIELDS = (
    "action_status",
    "actionStatus",
    "action_plan_status",
    "actionPlanStatus",
    "action_decision",
    "actionDecision",
    "decision_status",
    "decisionStatus",
    "status",
    "recommendation_status",
)
ACTION_PLAN_SCOPE = "SELECTED_ACTIONS_ONLY"
ACTION_CANDIDATES_SCOPE = "FULL_EVALUATED_ACTION_CANDIDATES"
ACTION_DECISION_COUNT_BASIS = "hedgeActionPlan_selected_actions_only"
RECOMMENDATION_GRADES = ("A", "B", "C", "D")
SCORE_METHOD_VERSION = "grade_banded_final_score_v1"
GRADE_SCORE_BANDS = {
    "A": (90, 100),
    "B": (70, 89),
    "C": (50, 69),
    "D": (0, 49),
}
DEFENSIVE_BENCHMARK_TICKERS = {
    "__CASH__",
    "CASH",
    "BIL",
    "SGOV",
    "SHV",
    "SHY",
    "IEF",
    "TLT",
    "TIP",
    "GLD",
    "IAU",
    "UUP",
}


def action_payload_shape():
    return {
        "portfolioVulnerabilityAttribution": {
            "type": "array",
            "scope": "portfolio_holding_vulnerability_attribution_rows",
            "countedByActionPlanDecision": False,
        },
        "portfolioVulnerabilitySummary": {
            "type": "summary",
            "scope": "portfolio_vulnerability_summary",
            "countedByActionPlanDecision": False,
        },
        "hedgeActionCandidates": {
            "type": "array",
            "scope": ACTION_CANDIDATES_SCOPE,
            "countedByActionPlanDecision": False,
        },
        "hedgeActionPlan": {
            "type": "array",
            "scope": ACTION_PLAN_SCOPE,
            "jsonSourceKey": "selected_actions",
            "countedByActionPlanDecision": True,
        },
        "hedgeActionPlanSummary": {
            "type": "summary",
            "scope": "selected_action_plan_summary",
            "countedByActionPlanDecision": False,
        },
        "actionPlanDecision": {
            "type": "decision",
            "countBasis": ACTION_DECISION_COUNT_BASIS,
            "countedRowSet": "hedgeActionPlan",
            "countedRowScope": ACTION_PLAN_SCOPE,
        },
    }


def row_keys_for_optional_artifact(key):
    if key == "hedgeActionPlan":
        return ("selected_actions", "action_plan", "actions", "rows", "items", "records")
    if key == "hedgeActionCandidates":
        return ("action_candidates", "candidates", "rows", "items", "records")
    if key == "portfolioVulnerabilityAttribution":
        return ("attribution", "portfolio_vulnerability_attribution", "rows", "items", "records")
    return ("rows", "items", "records")


def _split_action_list(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part.strip() for part in str(value or "").replace(",", "|").split("|") if part.strip()]


def _parse_weight_json_for_api(value):
    if not value:
        return {}
    if isinstance(value, dict):
        return value
    try:
        payload = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _float_for_api(value, default=0.0):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(number):
        return default
    return number


def _clip01_for_api(value):
    return max(0.0, min(1.0, _float_for_api(value, 0.0) or 0.0))


def _score_band_for_api(grade):
    return GRADE_SCORE_BANDS.get(str(grade or "").strip().upper())


def _score_grade_for_api(grade):
    normalized = str(grade or "").strip().upper()
    return normalized if normalized in GRADE_SCORE_BANDS else "D"


def _score_band_label_for_api(grade):
    normalized = _score_grade_for_api(grade)
    band = _score_band_for_api(normalized)
    if not band:
        return ""
    return f"{normalized}:{band[0]}-{band[1]}"


def _linked_final_score_for_api(row):
    for key in ("linked_final_score", "linkedFinalScore", "final_score", "finalScore"):
        if row.get(key) not in (None, ""):
            return _clip01_for_api(row.get(key))
    return 0.0


def _raw_linked_final_score_for_api(row):
    for key in ("raw_linked_final_score", "rawLinkedFinalScore", "linked_final_score", "linkedFinalScore", "final_score", "finalScore"):
        if row.get(key) not in (None, ""):
            return _clip01_for_api(row.get(key))
    return 0.0


ACTION_QUALITY_COMPONENTS = [
    ("input_aware_score", ("input_aware_score", "inputAwareScore"), 0.20, 1.0),
    ("vulnerability_improve_pct", ("vulnerability_improve_pct", "vulnerabilityImprovePct"), 0.35, 20.0),
    ("cvar_delta", ("expected_cvar_delta_after_cost", "expectedCvarDeltaAfterCost", "cvar_delta", "cvarDelta"), 0.12, 0.003),
    ("mdd_delta", ("expected_mdd_delta_after_cost", "expectedMddDeltaAfterCost", "mdd_delta", "mddDelta"), 0.12, 0.03),
    ("stress_delta", ("expected_stress_delta_after_cost", "expectedStressDeltaAfterCost", "stress_delta", "stressDelta"), 0.11, 0.001),
    ("sharpe_delta", ("sharpe_delta", "sharpeDelta"), 0.10, 0.05),
]


def _positive_component_for_api(row, keys):
    for key in keys:
        value = _float_for_api(row.get(key), None)
        if value is not None:
            return max(0.0, value)
    return None


def _component_score_for_api(value, values, fallback_scale):
    if value is None:
        return None
    usable = [item for item in values if item is not None]
    if len(usable) >= 2:
        low = min(usable)
        high = max(usable)
        if high > low:
            return _clip01_for_api((value - low) / (high - low))
    return _clip01_for_api(value / fallback_scale if fallback_scale else value)


def _action_quality_scores_for_api(rows):
    values_by_name = {}
    for name, keys, _, _ in ACTION_QUALITY_COMPONENTS:
        values_by_name[name] = [_positive_component_for_api(row, keys) for row in rows or []]

    scores = {}
    for row in rows or []:
        components = []
        for name, keys, weight, fallback_scale in ACTION_QUALITY_COMPONENTS:
            value = _positive_component_for_api(row, keys)
            score = _component_score_for_api(value, values_by_name.get(name, []), fallback_scale)
            if score is not None:
                components.append((weight, score))
        if not components:
            continue
        weight_sum = sum(weight for weight, _ in components)
        if weight_sum > 0:
            scores[id(row)] = _clip01_for_api(sum(weight * score for weight, score in components) / weight_sum)
    return scores


def _display_score_from_linked_for_api(grade, linked_score):
    band = _score_band_for_api(grade)
    if not band:
        return None
    low, high = band
    return int(round(low + _clip01_for_api(linked_score) * (high - low)))


def _apply_action_score_contracts_for_api(rows):
    quality_scores = _action_quality_scores_for_api(rows)
    for row in rows or []:
        raw_score = _raw_linked_final_score_for_api(row)
        quality_score = quality_scores.get(id(row))
        row["raw_linked_final_score"] = raw_score
        if quality_score is not None:
            row["action_quality_score"] = round(quality_score, 6)
        if quality_score is not None and raw_score <= 0.15:
            linked_score = round(quality_score, 6)
            row["score_driver_source"] = "action_quality_score"
        else:
            linked_score = raw_score
            row["score_driver_source"] = "linked_final_score"
        score_grade = _score_grade_for_api(row.get("recommendation_grade") or row.get("recommendationGrade"))
        row["linked_final_score"] = linked_score
        row["user_display_score"] = _display_score_from_linked_for_api(score_grade, linked_score)
        row["score_band"] = row.get("score_band") or row.get("scoreBand") or _score_band_label_for_api(score_grade)
        row["score_method_version"] = row.get("score_method_version") or row.get("scoreMethodVersion") or SCORE_METHOD_VERSION
    return rows


def _user_display_score_for_api(row, grade, linked_score):
    band = _score_band_for_api(grade)
    existing = row.get("user_display_score")
    if existing in (None, ""):
        existing = row.get("userDisplayScore")
    if existing not in (None, ""):
        score = int(round(_float_for_api(existing, 0.0) or 0.0))
        if band:
            return max(band[0], min(band[1], score))
        return score
    if not band:
        return None
    low, high = band
    return int(round(low + _clip01_for_api(linked_score) * (high - low)))


def _score_contract_for_api(row, grade):
    score_grade = _score_grade_for_api(grade)
    linked_score = _linked_final_score_for_api(row)
    return {
        "linked_final_score": linked_score,
        "user_display_score": _user_display_score_for_api(row, score_grade, linked_score),
        "score_band": row.get("score_band") or row.get("scoreBand") or _score_band_label_for_api(score_grade),
        "score_method_version": row.get("score_method_version") or row.get("scoreMethodVersion") or SCORE_METHOD_VERSION,
    }


def _bool_for_api(value, default=False):
    if isinstance(value, bool):
        return value
    if value in (None, ""):
        return default
    text = str(value).strip().upper()
    if text in {"1", "Y", "YES", "TRUE", "PASS", "OK"}:
        return True
    if text in {"0", "N", "NO", "FALSE", "FAIL", "BLOCK"}:
        return False
    return default


def _action_metric_positive(row, *keys):
    return any((_float_for_api(row.get(key), 0.0) or 0.0) > 0.0 for key in keys)


def _action_candidates_for_api(row):
    return {ticker.upper() for ticker in _split_action_list(row.get("candidate_tickers") or row.get("hedge_asset"))}


def _benchmark_action_for_api(row):
    candidates = _action_candidates_for_api(row)
    return bool(candidates) and candidates.issubset(DEFENSIVE_BENCHMARK_TICKERS)


def _direct_action_for_api(row):
    if not row.get("risk_sleeve"):
        return False
    if not _split_action_list(row.get("source_tickers") or row.get("source_asset")):
        return False
    if not _action_candidates_for_api(row):
        return False
    if (_float_for_api(row.get("vulnerability_delta"), 0.0) or 0.0) >= -1e-12:
        return False
    if str(row.get("action_type") or "").upper() == "DE_RISK_CASH":
        return _bool_for_api(row.get("source_trim_pass"), default=False)
    return _bool_for_api(row.get("risk_sleeve_offset_pass"), default=False)


def _basis_risk_for_api(row, direct):
    if direct and not _benchmark_action_for_api(row):
        return "LOW"
    if direct:
        return "MEDIUM"
    if _benchmark_action_for_api(row):
        return "BENCHMARK"
    return "HIGH"


def _prescription_score_for_api(row, direct, basis):
    score = 35.0 if direct else 0.0
    if _action_metric_positive(row, "expected_stress_delta_after_cost", "stress_delta"):
        score += 20.0
    if _action_metric_positive(row, "expected_cvar_delta_after_cost", "cvar_delta"):
        score += 7.5
    if _action_metric_positive(row, "expected_mdd_delta_after_cost", "mdd_delta"):
        score += 7.5
    score += {"LOW": 10.0, "MEDIUM": 6.0, "BENCHMARK": 2.0}.get(basis, 0.0)
    if str(row.get("constraint_status") or "").upper() == "PASS" and _bool_for_api(row.get("liquidity_pass"), default=True):
        score += 10.0
    if row.get("plain_korean_reason") or row.get("action_reason_ko"):
        score += 5.0
    if _benchmark_action_for_api(row) and not direct:
        score -= 18.0
    return round(max(0.0, min(100.0, score)), 4)


def _recommendation_grade_for_api(row, status):
    existing = str(row.get("recommendation_grade") or row.get("recommendationGrade") or "").strip().upper()
    if existing in RECOMMENDATION_GRADES:
        grade = existing
        label = row.get("recommendation_grade_label_ko") or row.get("recommendationGradeLabelKo") or ""
        reason = row.get("recommendation_grade_reason_ko") or row.get("recommendationGradeReasonKo") or ""
    else:
        direct = _direct_action_for_api(row)
        benchmark = _benchmark_action_for_api(row)
        metric_improved = any(
            _action_metric_positive(row, preferred, fallback)
            for preferred, fallback in [
                ("expected_cvar_delta_after_cost", "cvar_delta"),
                ("expected_mdd_delta_after_cost", "mdd_delta"),
                ("expected_stress_delta_after_cost", "stress_delta"),
            ]
        )
        action_type = str(row.get("action_type") or "").upper()
        if status == "FORMAL_ACTION" and direct and metric_improved:
            grade = "A"
            label = "A. 공식 실행 추천"
            reason = "formal/action gate 통과와 핵심 취약점 직접 완화가 같이 확인되었습니다."
        elif status == "REVIEW_ACTION" and direct and action_type in {"ADD_HEDGE", "TRIM_AND_HEDGE", "REPLACE_SLEEVE"}:
            grade = "B"
            label = "B. 조건부 처방"
            reason = "핵심 취약점은 줄이지만 실행 전 검증 조건이 남아 있습니다."
        elif status == "REVIEW_ACTION" and direct:
            grade = "C"
            label = "C. 검토 후보"
            reason = "방향성은 맞지만 공식 처방 근거가 부족합니다."
        elif benchmark and status in {"FORMAL_ACTION", "REVIEW_ACTION"}:
            grade = "D"
            label = "D. 참고 benchmark"
            reason = "방어 benchmark 성격이며 핵심 취약점 직접 처방은 아닙니다."
        elif status == "REVIEW_ACTION":
            grade = "C"
            label = "C. 검토 후보"
            reason = "리스크 개선 가능성은 있으나 직접 처방 근거가 제한적입니다."
        else:
            grade = ""
            label = ""
            reason = ""

    direct = _direct_action_for_api(row)
    basis = row.get("basis_risk_level") or row.get("basisRiskLevel") or _basis_risk_for_api(row, direct)
    score = row.get("prescription_score") or row.get("prescriptionScore")
    if score in (None, ""):
        score = _prescription_score_for_api(row, direct, basis)
    payload = {
        "recommendation_grade": grade,
        "recommendation_grade_label_ko": label,
        "recommendation_grade_reason_ko": reason,
        "direct_vulnerability_prescription": row.get("direct_vulnerability_prescription") or ("Y" if direct else "N"),
        "basis_risk_level": basis,
        "prescription_score": score,
    }
    payload.update(_score_contract_for_api(row, grade))
    return payload


def enrich_attribution_contract_aliases(row):
    if not isinstance(row, dict):
        return row
    row.setdefault("scenario", row.get("scenario_code") or row.get("risk_sleeve") or "")
    row.setdefault("asset_ticker", row.get("ticker") or row.get("holding_ticker") or "")
    row.setdefault("source_asset", row.get("ticker") if row.get("source_or_offset") == "source" else row.get("source_asset", ""))
    row.setdefault("current_weight", row.get("weight_pct") or row.get("current_weight_pct") or row.get("weight") or "")
    row.setdefault("current_weight_pct", row.get("weight_pct") or row.get("current_weight") or "")
    row.setdefault("scenario_activation_weight", row.get("scenario_weight") or row.get("scenario_context_weight") or "")
    row.setdefault("asset_scenario_beta", row.get("signed_sensitivity") or row.get("scenario_beta") or "")
    row.setdefault("weighted_contribution", row.get("vulnerability_contribution") or row.get("risk_contribution") or "")
    row.setdefault("contribution_pct", row.get("sleeve_contribution_pct") or row.get("contribution_pct_of_sleeve") or "")
    row.setdefault("contribution_pct_of_sleeve", row.get("sleeve_contribution_pct") or row.get("contribution_pct") or "")
    row.setdefault("contribution_pct_of_total", row.get("portfolio_contribution_pct") or "")
    row.setdefault("plain_korean_reason", row.get("plain_reason_ko") or row.get("reason_ko") or "")
    return row


def _action_expected_effect_for_api(row):
    if row.get("expected_effect"):
        return row["expected_effect"]
    pieces = []
    vuln_delta = _float_for_api(row.get("vulnerability_delta"), None)
    if vuln_delta is not None:
        pieces.append(f"취약성 {'감소' if vuln_delta < 0 else '증가'} {abs(vuln_delta):.4f}")
    for key, label, good_positive in [
        ("cvar_delta", "CVaR", True),
        ("mdd_delta", "MDD", True),
        ("stress_delta", "stress", True),
        ("sharpe_delta", "Sharpe", True),
    ]:
        delta = _float_for_api(row.get(key), None)
        if delta is None:
            continue
        improved = delta >= 0 if good_positive else delta < 0
        pieces.append(f"{label} {'개선' if improved else '악화'}")
    return "; ".join(pieces) if pieces else "전후 지표 계산값이 없어 정성 근거를 확인해야 합니다."


def _action_status_reason_for_api(row):
    if row.get("status_reason_ko"):
        return row["status_reason_ko"]
    status = normalize_action_status(row)
    if status == "FORMAL_ACTION":
        return "기존 formal recommendation gate를 통과한 실행 가능 액션입니다."
    if status == "REVIEW_ACTION":
        return "리스크 완화 효과는 있으나 기존 formal gate를 통과하지 못해 검토 후보로 유지합니다."
    if status == "FAIL_ACTION":
        return f"기준 미통과: {row.get('constraint_reasons') or row.get('rejected_reason_ko') or '취약성 또는 핵심 지표 개선이 부족합니다.'}"
    if status == "NO_ACTION":
        return "제약 조건 안에서 유효한 bounded action을 만들지 못했습니다."
    return "실행 추천과 분리된 리서치 전용 후보입니다."


def enrich_action_contract_aliases(row):
    if not isinstance(row, dict):
        return row
    status = normalize_action_status(row)
    before = _parse_weight_json_for_api(row.get("before_weights_json") or row.get("beforeWeightsJson"))
    after = _parse_weight_json_for_api(row.get("after_weights_json") or row.get("afterWeightsJson"))
    source_asset = row.get("source_asset") or row.get("holding_ticker") or (_split_action_list(row.get("source_tickers"))[:1] or [""])[0]
    hedge_asset = row.get("hedge_asset") or row.get("candidate_ticker") or (_split_action_list(row.get("candidate_tickers"))[:1] or [""])[0]
    row.setdefault("action_status", status)
    row.setdefault("scenario", row.get("risk_sleeve") or row.get("vulnerability_id") or "")
    row.setdefault("source_asset", source_asset)
    row.setdefault("hedge_asset", hedge_asset)
    row.setdefault("scenario_weight", row.get("scenario_activation_weight") or "")
    row.setdefault("contribution_pct", row.get("source_contribution_pct") or row.get("contribution_pct_of_sleeve") or "")
    row.setdefault("contribution_pct_of_sleeve", row.get("source_contribution_pct") or row.get("contribution_pct") or "")
    if source_asset:
        row.setdefault("current_weight", before.get(source_asset, row.get("source_current_weight_pct", "")))
        row.setdefault("proposed_weight", after.get(source_asset, row.get("source_proposed_weight_pct", "")))
        row.setdefault("source_current_weight_pct", before.get(source_asset, row.get("current_weight", "")))
        row.setdefault("source_proposed_weight_pct", after.get(source_asset, row.get("proposed_weight", "")))
    if hedge_asset:
        row.setdefault("hedge_current_weight_pct", before.get(hedge_asset, ""))
        row.setdefault("hedge_proposed_weight_pct", after.get(hedge_asset, ""))
    row.setdefault("action_reason_ko", row.get("plain_korean_reason") or row.get("reason_ko") or "")
    row.setdefault("plain_korean_reason", row.get("action_reason_ko") or "")
    row.setdefault("formal_action_type", normalize_formal_action_type(row))
    row.setdefault("action_family", row.get("action_family") or row.get("actionFamily") or "")
    row.setdefault("formal_gate_name", row.get("formal_gate_name") or row.get("formalGateName") or "")
    row.setdefault("formal_gate_status", row.get("formal_gate_status") or row.get("formalGateStatus") or "")
    row.setdefault("formal_gate_blockers", row.get("formal_gate_blockers") or row.get("formalGateBlockers") or "")
    row.setdefault("pre_backtest_linked_recommendation_status", row.get("preBacktestLinkedRecommendationStatus") or "")
    row.setdefault("linked_backtest_gate_status", row.get("linkedBacktestGateStatus") or "")
    row.setdefault("linked_formal_gate_blockers", row.get("linkedFormalGateBlockers") or "")
    row.setdefault("linked_formal_gate_blocker_summary", row.get("linkedFormalGateBlockerSummary") or "")
    row.setdefault("linked_target_evaluated_count", row.get("linkedTargetEvaluatedCount") or "")
    row.setdefault("linked_target_lags_cash_count", row.get("linkedTargetLagsCashCount") or "")
    row.setdefault("why_formal_ko", row.get("why_formal_ko") or row.get("whyFormalKo") or "")
    row.setdefault("why_review_only_ko", row.get("why_review_only_ko") or row.get("whyReviewOnlyKo") or "")
    row.setdefault("alternatives_compared_json", row.get("alternatives_compared_json") or row.get("alternativesComparedJson") or "")
    row.setdefault("alternatives_compared_count", row.get("alternatives_compared_count") or row.get("alternativesComparedCount") or 0)
    row.setdefault("cash_baseline_verdict", row.get("cash_baseline_verdict") or row.get("cashBaselineVerdict") or "")
    row.setdefault("bootstrap_verdict", row.get("bootstrap_verdict") or row.get("bootstrapVerdict") or row.get("action_bootstrap_confidence") or "")
    row.update(_recommendation_grade_for_api(row, status))
    row.setdefault("status_reason_ko", _action_status_reason_for_api(row))
    row.setdefault("expected_effect", _action_expected_effect_for_api(row))
    if status == "FORMAL_ACTION":
        row.setdefault("rejected_reason_ko", "")
    else:
        row.setdefault(
            "rejected_reason_ko",
            row.get("constraint_reasons")
            or "기존 formal gate, stress/backtest 근거, CVaR·MDD 안정성 중 일부가 부족해 정식 추천에서 제외했습니다.",
        )
    row.setdefault("can_execute_action", status == "FORMAL_ACTION")
    return row


def enrich_optional_rows_contract(key, rows):
    if key == "portfolioVulnerabilityAttribution":
        return [enrich_attribution_contract_aliases(row) for row in rows]
    if key in {"hedgeActionPlan", "hedgeActionCandidates"}:
        return _apply_action_score_contracts_for_api([enrich_action_contract_aliases(row) for row in rows])
    return rows


def load_optional_rows_artifact(manifest, key):
    path = resolve_product_artifact(manifest, key, default_dir=OUTPUT_REPORT_DIR)
    if not path:
        return [], None, f"missing action artifact: {key}"
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return enrich_optional_rows_contract(key, read_csv_rows(path)), scenario_artifact(path), ""
    if suffix == ".json":
        try:
            payload = read_json(path, [])
        except (OSError, json.JSONDecodeError) as exc:
            return [], scenario_artifact(path), f"failed to read action artifact: {key}={path.name}: {exc}"
        if isinstance(payload, list):
            return enrich_optional_rows_contract(key, payload), scenario_artifact(path), ""
        if isinstance(payload, dict):
            for rows_key in row_keys_for_optional_artifact(key):
                rows = payload.get(rows_key)
                if isinstance(rows, list):
                    return enrich_optional_rows_contract(key, rows), scenario_artifact(path), ""
        return [], scenario_artifact(path), f"action artifact has no row array: {key}"
    return [], scenario_artifact(path), f"action artifact is not a supported row artifact: {key}={path.name}"


def load_optional_summary_artifact(manifest, key):
    empty = {"text": "", "rows": [], "data": None, "artifact": None}
    path = resolve_product_artifact(manifest, key, default_dir=OUTPUT_REPORT_DIR)
    if not path:
        return empty, f"missing action artifact: {key}"
    artifact = scenario_artifact(path)
    suffix = path.suffix.lower()
    try:
        if suffix == ".csv":
            return {"text": "", "rows": read_csv_rows(path), "data": None, "artifact": artifact}, ""
        if suffix == ".json":
            return {"text": "", "rows": [], "data": read_json(path, {}), "artifact": artifact}, ""
        return {"text": path.read_text(encoding="utf-8"), "rows": [], "data": None, "artifact": artifact}, ""
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        payload = dict(empty)
        payload["artifact"] = artifact
        return payload, f"failed to read action artifact: {key}={path.name}: {exc}"


def load_action_plan_metadata(manifest):
    path = resolve_product_artifact(manifest, "hedgeActionPlan", default_dir=OUTPUT_REPORT_DIR)
    if not path or path.suffix.lower() != ".json":
        return {}
    try:
        payload = read_json(path, {})
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    row_keys = set(row_keys_for_optional_artifact("hedgeActionPlan"))
    return {key: value for key, value in payload.items() if key not in row_keys}


def normalize_action_status(row):
    if not isinstance(row, dict):
        return "NO_ACTION"
    for field in ACTION_STATUS_FIELDS:
        raw = row.get(field)
        if raw in (None, ""):
            continue
        status = str(raw).strip().upper().replace("-", "_").replace(" ", "_")
        if field == "recommendation_status" and status == "PASS_RECOMMEND":
            return "REVIEW_ACTION"
        return ACTION_STATUS_ALIASES.get(status, status if status in ACTION_STATUSES else "NO_ACTION")
    return "NO_ACTION"


FORMAL_ACTION_TYPES = (
    "FORMAL_REBALANCE_HEDGE",
    "FORMAL_DE_RISK_CASH",
    "FORMAL_HOLD",
    "REVIEW_REQUIRED",
)


def normalize_formal_action_type(row):
    if not isinstance(row, dict):
        return ""
    raw = row.get("formal_action_type") or row.get("formalActionType") or ""
    value = str(raw).strip().upper().replace("-", "_").replace(" ", "_")
    if value in FORMAL_ACTION_TYPES:
        return value
    return ""


def formal_action_type_counts(action_rows):
    counts = {name: 0 for name in FORMAL_ACTION_TYPES}
    for row in action_rows or []:
        formal_type = normalize_formal_action_type(row)
        if formal_type:
            counts[formal_type] = counts.get(formal_type, 0) + 1
    return dict(sorted(counts.items()))


def recommendation_grade_counts(action_rows):
    counts = {grade: 0 for grade in RECOMMENDATION_GRADES}
    for row in action_rows or []:
        grade = str(row.get("recommendation_grade") or row.get("recommendationGrade") or "").strip().upper()
        if grade in counts:
            counts[grade] += 1
    return dict(sorted(counts.items()))


def append_unique(values, value):
    if value and value not in values:
        values.append(value)


def selected_action_type_counts(action_rows):
    counts = {}
    for row in action_rows or []:
        action_type = str(row.get("action_type") or "UNKNOWN")
        counts[action_type] = counts.get(action_type, 0) + 1
    return dict(sorted(counts.items()))


def selected_risk_sleeve_counts(action_rows):
    counts = {}
    for row in action_rows or []:
        sleeve = str(row.get("risk_sleeve") or "UNKNOWN")
        counts[sleeve] = counts.get(sleeve, 0) + 1
    return dict(sorted(counts.items()))


def replace_sleeve_decision_for_api(action_rows, action_plan_metadata=None):
    action_plan_metadata = action_plan_metadata or {}
    raw = action_plan_metadata.get("replace_sleeve_decision") or {}
    type_counts = selected_action_type_counts(action_rows)
    selected_count = int(raw.get("selected_count") or type_counts.get("REPLACE_SLEEVE") or 0)
    candidate_count = int(raw.get("candidate_count") or 0)
    if selected_count > 0:
        absence_code = ""
        absence_ko = ""
    else:
        absence_code = raw.get("absence_reason_code") or "NO_SELECTED_REPLACE_SLEEVE"
        absence_ko = raw.get("absence_reason_ko") or "selected action plan에 REPLACE_SLEEVE가 없습니다."
    return {
        "actionType": "REPLACE_SLEEVE",
        "candidateCount": candidate_count,
        "selectedCount": selected_count,
        "presentInCandidates": bool(raw.get("present_in_candidates") or candidate_count > 0),
        "presentInSelected": selected_count > 0,
        "absenceReasonCode": absence_code,
        "absenceReasonKo": absence_ko,
    }


def build_action_plan_decision(action_rows, recommendation_decision=None, artifact_warnings=None, action_plan_metadata=None):
    recommendation_decision = recommendation_decision or {}
    artifact_warnings = [warning for warning in (artifact_warnings or []) if warning]
    action_plan_metadata = action_plan_metadata or {}
    status_counts = {status: 0 for status in ACTION_STATUSES}
    for row in action_rows or []:
        status_counts[normalize_action_status(row)] += 1

    formal_type_counts = formal_action_type_counts(action_rows)
    formal_rebalance_hedge_count = int(formal_type_counts.get("FORMAL_REBALANCE_HEDGE") or 0)
    formal_de_risk_cash_count = int(formal_type_counts.get("FORMAL_DE_RISK_CASH") or 0)
    formal_hold_count = int(formal_type_counts.get("FORMAL_HOLD") or 0)
    review_required_count = int(formal_type_counts.get("REVIEW_REQUIRED") or 0)
    grade_counts = recommendation_grade_counts(action_rows)
    grade_a_count = int(grade_counts.get("A") or 0)
    grade_b_count = int(grade_counts.get("B") or 0)
    grade_c_count = int(grade_counts.get("C") or 0)
    grade_d_count = int(grade_counts.get("D") or 0)
    formal_count = status_counts["FORMAL_ACTION"]
    review_count = status_counts["REVIEW_ACTION"]
    research_count = status_counts["RESEARCH_ONLY"]
    fail_count = status_counts["FAIL_ACTION"]
    no_action_count = status_counts["NO_ACTION"]
    blockers = []
    reasons = []
    reasons_ko = []
    upgrade_requirements = []

    if not action_rows:
        append_unique(blockers, "no_action_plan")
        reasons.append("No bounded hedge action plan is available for the active portfolio.")
        reasons_ko.append("현재 active run에 선택된 bounded hedge action plan이 없습니다.")
        upgrade_requirements.append("portfolioVulnerabilityAttribution, hedgeActionCandidates, hedgeActionPlan 산출물을 먼저 생성해야 합니다.")
    elif formal_count <= 0:
        append_unique(blockers, "no_formal_action")
        if review_count > 0:
            reasons.append("Review actions can reduce risk but are not formal executable recommendations.")
            reasons_ko.append("취약성을 낮추는 REVIEW_ACTION은 있지만 기존 formal recommendation gate를 통과한 FORMAL_ACTION은 없습니다.")
            upgrade_requirements.append("REVIEW_ACTION 후보가 stress/backtest, CVaR, MDD, 거래 제약 검증을 추가로 통과해야 합니다.")
        elif research_count > 0:
            reasons.append("Only research-only instruments are present; they are not executable hedge actions.")
            reasons_ko.append("현재 선택된 후보는 리서치 전용 성격이라 실행 추천으로 표시하지 않습니다.")
            upgrade_requirements.append("인버스·레버리지·옵션·변동성 상품이 아닌 실행 가능한 hedge 후보가 필요합니다.")
        elif fail_count > 0:
            reasons.append("Action candidates fail the vulnerability or gate checks.")
            reasons_ko.append("후보 액션이 취약성 개선 또는 gate 조건을 통과하지 못했습니다.")
            upgrade_requirements.append("CVaR/MDD/stress 악화 원인을 해소하거나 turnover·집중도 제약을 만족해야 합니다.")
        else:
            reasons.append("The active portfolio has no valid bounded hedge action.")
            reasons_ko.append("현재 포트폴리오 취약성에 대해 제약 조건 안에서 유효한 bounded action이 없습니다.")
            upgrade_requirements.append("헷지 후보 universe, 민감도 매핑, 또는 허용 turnover 조건을 재검토해야 합니다.")

    gate_allows_execution = True
    recommendation_blockers = recommendation_decision.get("blockers") or []
    if formal_count > 0 and recommendation_blockers and not recommendation_decision.get("canExecuteRecommendations"):
        for blocker in recommendation_blockers:
            append_unique(blockers, blocker)
        gate_allows_execution = False
        reasons.append("Formal actions are present but the existing recommendation gate blocks execution.")
        reasons_ko.append("기존 추천 gate blocker가 있어 FORMAL_ACTION도 실행 가능 상태로 표시하지 않습니다.")
        upgrade_requirements.append("recommendationDecision blocker와 데이터 freshness를 먼저 해소해야 합니다.")

    if research_count > 0:
        reasons.append("Research-only actions remain separated from executable recommendations.")
        reasons_ko.append("리서치 전용 후보는 실행 추천 수에 포함하지 않습니다.")
    if artifact_warnings:
        append_unique(blockers, "missing_action_artifact")
        gate_allows_execution = False
        reasons.append("Some action-plan artifacts are missing or unreadable; fallback payloads were returned.")
        reasons_ko.append("일부 action artifact가 없거나 읽히지 않아 fallback payload가 포함됐습니다.")
        upgrade_requirements.append("latest_manifest.json의 action artifact 경로와 active bundle을 확인해야 합니다.")

    if formal_count > 0 and grade_a_count <= 0:
        append_unique(blockers, "no_grade_a_direct_prescription")
        gate_allows_execution = False
        reasons.append("Formal-looking actions exist, but none is an A-grade direct vulnerability prescription.")
        reasons_ko.append("FORMAL_ACTION row는 있지만 핵심 취약점을 직접 줄이는 A등급 처방이 없어 실행 가능 상태로 표시하지 않습니다.")
        upgrade_requirements.append("risk_sleeve, source_tickers, candidate_tickers, vulnerability_delta, risk_sleeve_offset_pass가 모두 직접 처방 근거를 보여야 합니다.")

    can_execute = (formal_rebalance_hedge_count + formal_de_risk_cash_count) > 0 and grade_a_count > 0 and gate_allows_execution
    if can_execute and not reasons:
        reasons.append("At least one formal rebalance/de-risk action passed the action-level formal gate.")
        reasons_ko.append("최소 하나의 FORMAL_REBALANCE_HEDGE 또는 FORMAL_DE_RISK_CASH가 action formal gate를 통과했습니다.")

    if not upgrade_requirements and not can_execute:
        upgrade_requirements.append("추가 검증 결과가 충분해질 때까지 REVIEW_ACTION은 실행 전 검토 후보로만 표시합니다.")
    why_no_formal_ko = " ".join(reasons_ko[:4]) if formal_count <= 0 or not can_execute else ""

    return {
        "formalActionCount": formal_count,
        "formalActionTypeCounts": formal_type_counts,
        "formalRebalanceHedgeCount": formal_rebalance_hedge_count,
        "formalDeRiskCashCount": formal_de_risk_cash_count,
        "formalHoldCount": formal_hold_count,
        "reviewRequiredCount": review_required_count,
        "recommendationGradeCounts": grade_counts,
        "gradeAActionCount": grade_a_count,
        "gradeBActionCount": grade_b_count,
        "gradeCActionCount": grade_c_count,
        "gradeDActionCount": grade_d_count,
        "reviewActionCount": review_count,
        "researchOnlyCount": research_count,
        "failActionCount": fail_count,
        "noActionCount": no_action_count,
        "canExecuteAction": can_execute,
        "canExecuteFormalAction": can_execute,
        "blockers": blockers,
        "primaryReasons": reasons[:8],
        "primaryReasonsKo": reasons_ko[:8],
        "whyNoFormalRecommendationKo": why_no_formal_ko,
        "formalActionBlockersKo": reasons_ko[:8],
        "formalActionUpgradeRequirements": upgrade_requirements[:8],
        "userFacingDecisionKo": "정식 실행 가능" if can_execute else ("검토 액션만 있음" if review_count > 0 else "실행 액션 없음"),
        "statusCounts": status_counts,
        "selectedActionCount": len(action_rows or []),
        "candidateCount": len(action_rows or []),
        "countBasis": ACTION_DECISION_COUNT_BASIS,
        "countedRowSet": "hedgeActionPlan",
        "countedRowScope": ACTION_PLAN_SCOPE,
        "excludedRowSets": ["hedgeActionCandidates", "portfolioVulnerabilityAttribution"],
        "selectedActionTypeCounts": selected_action_type_counts(action_rows),
        "selectedRiskSleeveCounts": selected_risk_sleeve_counts(action_rows),
        "actionTypeCoverage": action_plan_metadata.get("action_type_coverage") or {},
        "sleeveSelectionCoverage": action_plan_metadata.get("sleeve_selection_coverage") or [],
        "replaceSleeveDecision": replace_sleeve_decision_for_api(action_rows, action_plan_metadata),
        "selectionPolicy": action_plan_metadata.get("selection_policy") or {},
        "artifactWarnings": artifact_warnings,
    }


def load_action_plan_payload(manifest, recommendation_decision=None):
    warnings = []
    artifacts = {}

    attribution, artifacts["portfolioVulnerabilityAttribution"], warning = load_optional_rows_artifact(
        manifest, "portfolioVulnerabilityAttribution"
    )
    if warning:
        warnings.append(warning)
    candidates, artifacts["hedgeActionCandidates"], warning = load_optional_rows_artifact(manifest, "hedgeActionCandidates")
    if warning:
        warnings.append(warning)
    action_plan, artifacts["hedgeActionPlan"], warning = load_optional_rows_artifact(manifest, "hedgeActionPlan")
    if warning:
        warnings.append(warning)
    action_plan_metadata = load_action_plan_metadata(manifest)
    vulnerability_summary, warning = load_optional_summary_artifact(manifest, "portfolioVulnerabilitySummary")
    artifacts["portfolioVulnerabilitySummary"] = vulnerability_summary.get("artifact")
    if warning:
        warnings.append(warning)
    action_plan_summary, warning = load_optional_summary_artifact(manifest, "hedgeActionPlanSummary")
    artifacts["hedgeActionPlanSummary"] = action_plan_summary.get("artifact")
    if warning:
        warnings.append(warning)

    return {
        "actionPayloadShape": action_payload_shape(),
        "hedgeActionCandidatesScope": ACTION_CANDIDATES_SCOPE,
        "hedgeActionPlanScope": ACTION_PLAN_SCOPE,
        "portfolioVulnerabilityAttribution": attribution,
        "portfolioVulnerabilitySummary": vulnerability_summary,
        "hedgeActionCandidates": candidates,
        "hedgeActionPlan": action_plan,
        "hedgeActionPlanMeta": action_plan_metadata,
        "hedgeActionPlanSummary": action_plan_summary,
        "actionPlanArtifacts": artifacts,
        "actionArtifactWarnings": warnings,
        "actionPlanDecision": build_action_plan_decision(action_plan, recommendation_decision, warnings, action_plan_metadata),
    }


def active_bundle_integrity(manifest):
    bundle = active_bundle(manifest)
    fingerprint = bundle_portfolio_fingerprint(bundle)
    tickers = active_bundle_ticker_list(manifest, bundle)
    input_sha = bundle.get("portfolioInputSha256") if isinstance(bundle, dict) else None
    missing = active_bundle_missing_artifacts(manifest)
    return {
        "ok": bool(bundle) and bool(fingerprint and fingerprint.get("hash")) and bool(tickers) and bool(input_sha) and not missing,
        "activeRunId": bundle.get("hedgemate_run") or manifest.get("active_hedgemate_run"),
        "portfolioFingerprintHash": fingerprint.get("hash") if isinstance(fingerprint, dict) else None,
        "portfolioInputSha256": input_sha,
        "tickers": tickers,
        "missingArtifacts": missing,
    }


def has_running_analysis_job():
    with RUN_JOBS_LOCK:
        job_ids = [
            job_id
            for job_id, job in RUN_JOBS.items()
            if not is_market_refresh_job(job)
            and not is_intraday_news_refresh_job(job)
            and job.get("status") in {"queued", "running"}
        ]
    for job_id in job_ids:
        snapshot = _snapshot_run_job(job_id)
        if snapshot and snapshot.get("status") in {"queued", "running"}:
            return True
    return False


def build_product_status(manifest, bundle, data_freshness, recommendation_decision, action_plan_decision, integrity):
    running_job = has_running_analysis_job()
    if not manifest or str(manifest.get("manifest_version") or "").endswith("_fallback_v1"):
        if running_job:
            return "RUNNING", ["analysis job is currently running"]
        return "NEEDS_ANALYSIS", ["formal product manifest is missing"]

    reasons = []
    if integrity.get("missingArtifacts"):
        reasons.append("missing required active artifacts: " + ", ".join(row["key"] for row in integrity["missingArtifacts"]))
        return "BLOCKED", reasons
    if not integrity.get("portfolioFingerprintHash"):
        return "BLOCKED", ["active bundle portfolio fingerprint is missing"]
    if not integrity.get("portfolioInputSha256"):
        return "BLOCKED", ["active bundle portfolio input sha256 is missing"]
    if not integrity.get("tickers"):
        return "BLOCKED", ["active bundle portfolio ticker list is missing"]

    if (
        data_freshness.get("portfolioInputMismatch")
        or data_freshness.get("recommendationPortfolioMismatch")
        or manifest.get("portfolio_input_mismatch")
        or bundle.get("portfolio_input_mismatch")
    ):
        reasons.extend(user_facing_freshness_reasons(data_freshness))
        return "MISMATCHED_PORTFOLIO", reasons[:8]

    freshness_status = str(
        data_freshness.get("freshnessStatus") or manifest.get("freshness_status") or bundle.get("freshness_status") or ""
    ).upper()
    if freshness_status == "STALE" or str(data_freshness.get("status") or "").lower() == "stale" or data_freshness.get("needsRefresh"):
        reasons.extend(user_facing_freshness_reasons(data_freshness) or manifest.get("stale_reasons") or bundle.get("stale_reasons") or [])
        return "STALE", reasons[:8]

    selected_action_count = sum(
        int(action_plan_decision.get(key, 0) or 0)
        for key in ("formalActionCount", "reviewActionCount", "researchOnlyCount", "failActionCount", "noActionCount")
    )
    if running_job and selected_action_count <= 0:
        return "RUNNING", ["analysis job is currently running"]

    if action_plan_decision.get("canExecuteAction"):
        return "ACTION_READY", action_plan_decision.get("primaryReasonsKo") or action_plan_decision.get("primaryReasons") or []

    if (
        action_plan_decision.get("formalActionCount", 0) > 0
        or action_plan_decision.get("reviewActionCount", 0) > 0
        or recommendation_decision.get("formalRecommendationCount", 0) > 0
    ):
        return "REVIEW_ONLY", action_plan_decision.get("formalActionBlockersKo") or recommendation_decision.get("primaryReasons") or []

    action_blockers = set(action_plan_decision.get("blockers") or [])
    recommendation_blockers = set(recommendation_decision.get("blockers") or [])
    if action_blockers or recommendation_blockers:
        severe_blockers = {"missing_action_artifact", "missing_required_active_artifact"}
        reasons = (action_plan_decision.get("primaryReasonsKo") or recommendation_decision.get("primaryReasons") or [])[:8]
        if action_blockers.intersection(severe_blockers):
            return "BLOCKED", reasons
        return "REVIEW_ONLY", reasons

    return "NEEDS_ANALYSIS", ["no current formal analysis is available for the active portfolio"]


def apply_product_action_safety(action_plan_decision, product_status, product_status_reasons, integrity):
    decision = dict(action_plan_decision or {})
    if product_status == "ACTION_READY":
        return decision

    blockers = list(decision.get("blockers") or [])
    if "product_status_not_action_ready" not in blockers:
        blockers.append("product_status_not_action_ready")
    if product_status == "STALE" and "stale_data" not in blockers:
        blockers.append("stale_data")
    if product_status == "MISMATCHED_PORTFOLIO" and "portfolio_input_mismatch" not in blockers:
        blockers.append("portfolio_input_mismatch")
    if integrity.get("missingArtifacts") and "missing_required_active_artifact" not in blockers:
        blockers.append("missing_required_active_artifact")

    reasons = list(decision.get("primaryReasons") or [])
    reason_text = f"Product status is {product_status}; action execution is disabled until the active dashboard is valid."
    if reason_text not in reasons:
        reasons.append(reason_text)

    reasons_ko = list(decision.get("primaryReasonsKo") or [])
    for reason in product_status_reasons or []:
        if reason and reason not in reasons_ko:
            reasons_ko.append(reason)

    decision.update(
        {
            "canExecuteAction": False,
            "canExecuteFormalAction": False,
            "blockers": blockers,
            "primaryReasons": reasons[:8],
            "primaryReasonsKo": reasons_ko[:8],
            "formalActionBlockersKo": reasons_ko[:8],
        }
    )
    return decision


def load_product_dashboard_data(manifest=None, compact=False):
    manifest = manifest if manifest is not None else read_product_manifest()
    if not manifest:
        manifest = fallback_product_manifest()
    product_manifest = strip_intraday_news_from_product_manifest(manifest)
    bundle = active_bundle(product_manifest)
    if not bundle:
        raise FileNotFoundError("HedgeMate active bundle manifest not found")
    hedge_run = bundle.get("hedgemate_run") or product_manifest.get("active_hedgemate_run")
    final_run = bundle.get("final_market_state_run") or product_manifest.get("active_final_run")
    if not hedge_run or not final_run:
        raise FileNotFoundError("Active bundle is missing hedge or scenario run")
    hedge = load_dashboard_data(hedge_run, product_manifest=product_manifest, include_execution_plan=not compact)
    try:
        scenario = load_scenario_dashboard_data(include_intraday_news=False)
    except FileNotFoundError:
        scenario = load_scenario_dashboard_data(final_run, include_intraday_news=False)
    data_freshness = load_data_freshness(manifest=product_manifest)
    backtest = load_backtest_payload(product_manifest)
    event_overlay_status = normalized_event_overlay_status(product_manifest.get("event_overlay_status"))
    recommendation_decision = build_recommendation_decision(hedge, backtest, data_freshness, event_overlay_status)
    action_payload = load_action_plan_payload(product_manifest, recommendation_decision)
    integrity = active_bundle_integrity(product_manifest)
    product_status, product_status_reasons = build_product_status(
        product_manifest,
        bundle,
        data_freshness,
        recommendation_decision,
        action_payload.get("actionPlanDecision") or {},
        integrity,
    )
    action_payload["actionPlanDecision"] = apply_product_action_safety(
        action_payload.get("actionPlanDecision") or {},
        product_status,
        product_status_reasons,
        integrity,
    )
    data_freshness_response = product_data_freshness_response(data_freshness)
    stale_reasons = user_facing_freshness_reasons(data_freshness)
    product_manifest_response = dict(product_manifest)
    product_manifest_response["stale_reasons"] = stale_reasons
    product_manifest_response["active_bundle"] = dict(bundle)
    product_manifest_response["active_bundle"]["stale_reasons"] = stale_reasons
    bundle_response = dict(bundle)
    bundle_response["stale_reasons"] = stale_reasons
    if isinstance(hedge, dict) and isinstance(hedge.get("activeManifest"), dict):
        hedge = dict(hedge)
        hedge_manifest = dict(hedge["activeManifest"])
        hedge_manifest["stale_reasons"] = stale_reasons
        if isinstance(hedge_manifest.get("active_bundle"), dict):
            hedge_manifest["active_bundle"] = dict(hedge_manifest["active_bundle"])
            hedge_manifest["active_bundle"]["stale_reasons"] = stale_reasons
        hedge["activeManifest"] = hedge_manifest
    return {
        "serverContractVersion": "action_contract_v3",
        "manifest": product_manifest_response,
        "activeBundle": bundle_response,
        "productStatus": product_status,
        "productStatusReasons": product_status_reasons,
        "activeBundleIntegrity": integrity,
        "freshnessStatus": product_manifest.get("freshness_status") or bundle.get("freshness_status"),
        "staleReasons": stale_reasons,
        "dataFreshness": data_freshness_response,
        "hedge": hedge,
        "scenario": scenario,
        "backtest": backtest,
        "recommendationDecision": recommendation_decision,
        "eventOverlayStatus": event_overlay_status,
        "formalGateBlockerSummary": (backtest.get("formalGateAuditSummary") or {}).get("blockerSummary")
        or build_formal_gate_blocker_summary([]),
        **action_payload,
    }


def normalize_product_status(status):
    raw = str(status or "").strip().upper()
    if raw in PRODUCT_STATUS_VALUES:
        return raw
    if raw in {"ACTION_READY", "READY_TO_ACT"}:
        return "READY"
    if raw in {"RUNNING", "QUEUED"}:
        return "REFRESHING"
    if raw in {"BLOCKED", "MISMATCHED_PORTFOLIO"}:
        return "ERROR"
    if raw in {"STALE"}:
        return "STALE"
    if raw in {"REVIEW_ONLY"}:
        return "REVIEW_ONLY"
    return "NEEDS_ANALYSIS" if not raw else "ERROR"


def product_dashboard_needs_analysis_payload(portfolio=None, running_run=None):
    status = "REFRESHING" if running_run else "NEEDS_ANALYSIS"
    return {
        "serverContractVersion": "action_contract_v4_portfolio_runs",
        "status": status,
        "productStatus": status,
        "selectedPortfolio": portfolio,
        "portfolioRun": run_row_response(running_run),
        "message": (
            "Selected portfolio analysis is running."
            if running_run
            else "No successful analysis run exists for the selected portfolio."
        ),
        "dataFreshness": {
            "selectedPortfolioStatus": status,
            "needsRefresh": status == "REFRESHING",
        },
    }


def manifest_from_portfolio_run(run_row):
    artifact_dir = (run_row or {}).get("artifact_dir")
    if not artifact_dir:
        return None, "portfolio run has no artifact_dir"
    path = Path(artifact_dir)
    if path.is_dir():
        for candidate in (path / "latest_manifest.json", path / "manifest.json"):
            if candidate.exists():
                path = candidate
                break
    if not path.exists() or not path.is_file():
        return None, f"portfolio run artifact is missing: {artifact_dir}"
    manifest = read_json(path, {})
    if not isinstance(manifest, dict) or not manifest:
        return None, f"portfolio run artifact is invalid: {artifact_dir}"
    return manifest, None


def load_product_dashboard_for_saved_portfolio(user_id, portfolio_id=None, portfolio_hash=None, compact=False):
    store = persistence_store()
    portfolio = None
    if portfolio_id is not None:
        portfolio = store.get_portfolio(user_id, portfolio_id)
    elif portfolio_hash:
        portfolio = store.get_portfolio_by_hash(user_id, portfolio_hash)
    if not portfolio:
        raise FileNotFoundError("Portfolio not found")

    running = store.latest_running_portfolio_run(
        user_id,
        portfolio_id=portfolio.get("portfolioId") if portfolio_id is not None else None,
        portfolio_hash=portfolio.get("portfolioHash") if portfolio_id is None else None,
    )
    if running:
        return product_dashboard_needs_analysis_payload(portfolio=portfolio, running_run=running)

    latest_run = store.latest_successful_portfolio_run(
        user_id,
        portfolio_id=portfolio.get("portfolioId") if portfolio_id is not None else None,
        portfolio_hash=portfolio.get("portfolioHash") if portfolio_id is None else None,
    )
    if not latest_run:
        return product_dashboard_needs_analysis_payload(portfolio=portfolio)

    manifest, error = manifest_from_portfolio_run(latest_run)
    if error:
        return {
            "serverContractVersion": "action_contract_v4_portfolio_runs",
            "status": "ERROR",
            "productStatus": "ERROR",
            "selectedPortfolio": portfolio,
            "portfolioRun": run_row_response(latest_run),
            "message": error,
            "dataFreshness": {"selectedPortfolioStatus": "ERROR", "needsRefresh": False},
        }
    dashboard = load_product_dashboard_data(manifest=manifest, compact=compact)
    raw_product_status = dashboard.get("productStatus")
    status = normalize_product_status(raw_product_status)
    dashboard.update(
        {
            "serverContractVersion": "action_contract_v4_portfolio_runs",
            "status": status,
            "productStatus": status,
            "rawProductStatus": raw_product_status,
            "selectedPortfolio": portfolio,
            "portfolioRun": run_row_response(latest_run),
        }
    )
    dashboard.setdefault("dataFreshness", {})
    dashboard["dataFreshness"]["selectedPortfolioStatus"] = status
    return dashboard


def load_product_dashboard_for_portfolio(payload, compact=False):
    manifest = read_product_manifest()
    mutate_active_bundle = bool((payload or {}).get("mutateActiveBundle"))
    scenario_context = latest_scenario_bundle_context(manifest)
    data_version = (payload or {}).get("dataVersion") or scenario_context.get("dataVersion") or active_data_version(manifest)
    scenario_vector = (scenario_context.get("artifacts") or {}).get("finalScenarioVector") or resolve_product_artifact(manifest, "finalScenarioVector", default_dir=SCENARIO_VECTOR_DIR)
    cache_meta = analysis_cache_key(payload or {}, data_version=data_version, scenario_vector=scenario_vector)
    dashboard_manifest = None
    cache_lookup = {
        "requested": bool(cache_meta),
        "matched": False,
        "reason": "no_portfolio_cache_key" if not cache_meta else "cache_miss",
        "cacheKey": cache_meta.get("hash") if cache_meta else None,
        "mutatedActiveBundle": False,
    }
    if cache_meta:
        entry, _ = find_analysis_cache_entry(
            cache_key=cache_meta.get("hash"),
            portfolio_request_hash=(cache_meta.get("portfolioRequestFingerprint") or {}).get("hash"),
        )
        if entry:
            entry_matched = True
            cache_reason = "cache_hit" if mutate_active_bundle else "cache_hit_read_only"
            if mutate_active_bundle:
                activate_cached_analysis(entry)
                cache_lookup["mutatedActiveBundle"] = True
            else:
                manifest_path = resolve_analysis_manifest_path(entry.get("manifestPath"))
                if manifest_path.exists():
                    cached_manifest = read_json(manifest_path, {})
                    if isinstance(cached_manifest, dict) and cached_manifest:
                        dashboard_manifest = cached_manifest
                    else:
                        entry_matched = False
                        cache_reason = "cache_hit_manifest_invalid"
                else:
                    entry_matched = False
                    cache_reason = "cache_hit_manifest_missing"
            cache_lookup.update(
                {
                    "matched": entry_matched,
                    "reason": cache_reason,
                    "runId": entry.get("runId"),
                    "portfolioFingerprintHash": entry.get("portfolioFingerprintHash"),
                    "portfolioInputSha256": entry.get("portfolioInputSha256"),
                }
            )
        elif mutate_active_bundle:
            backfilled = record_active_analysis_cache_for_payload(payload or {}, cache_meta)
            if backfilled:
                cache_lookup.update(
                    {
                        "matched": True,
                        "reason": "active_manifest_match_backfilled",
                        "runId": backfilled.get("runId"),
                        "portfolioFingerprintHash": backfilled.get("portfolioFingerprintHash"),
                        "portfolioInputSha256": backfilled.get("portfolioInputSha256"),
                    }
                )
    dashboard = load_product_dashboard_data(dashboard_manifest, compact=compact)
    dashboard["analysisCacheLookup"] = cache_lookup
    return dashboard


def load_service_status(selected_portfolio_id=None, selected_portfolio_hash=None, user_id=None):
    manifest = read_product_manifest()
    bundle = active_bundle(manifest)
    db_health = database_health()
    status = {
        "ok": True,
        "service": "HedgeMate dashboard",
        "database": "CONNECTED" if db_health.get("ok") else "DISCONNECTED",
        "databaseDetail": {"kind": db_health.get("kind"), "database": db_health.get("database")},
        "serverSafeMode": server_safe_mode(),
        "scheduler": scheduler_status_value(),
        "activeScenarioRun": bundle.get("scenario_run") or manifest.get("active_scenario_run"),
        "activeFinalRun": bundle.get("final_market_state_run") or manifest.get("active_final_run"),
        "activeHedgemateRun": bundle.get("hedgemate_run") or manifest.get("active_hedgemate_run"),
        "activeBacktestRun": bundle.get("backtest_run") or manifest.get("active_backtest_run"),
        "dataVersion": bundle.get("data_version") or manifest.get("data_version"),
        "freshnessStatus": manifest.get("freshness_status") or bundle.get("freshness_status"),
        "generatedAtUtc": bundle.get("generated_at_utc") or manifest.get("generated_at_utc"),
    }
    try:
        freshness = load_data_freshness(manifest=manifest)
        integrity = active_bundle_integrity(manifest)
    except FileNotFoundError as exc:
        status.update(
            {
                "ok": False,
                "error": str(exc),
                "market_data": "ERROR",
                "intraday_nowcast": "ERROR",
                "news_overlay": "ERROR",
                "selected_portfolio": "ERROR",
                "product_mode": "REVIEW_ONLY",
            }
        )
        return status

    blockers = []
    if integrity.get("missingArtifacts"):
        blockers.append("missing_required_active_artifact")
    if freshness.get("needsRefresh"):
        blockers.append("stale_data")
    if freshness.get("portfolioInputMismatch") or freshness.get("recommendationPortfolioMismatch"):
        blockers.append("portfolio_input_mismatch")
    if has_running_analysis_job():
        product_status = "RUNNING"
    elif blockers:
        product_status = "STALE" if "stale_data" in blockers else "BLOCKED"
    else:
        product_status = "READY"
    market_refreshing = bool(latest_running_market_refresh_job(mode="market_data_only"))
    intraday_refreshing = bool(latest_running_market_refresh_job(mode="intraday_nowcast"))
    news_refreshing = bool(latest_running_intraday_news_job())
    news_status = latest_intraday_news_overlay_status()
    selected_portfolio_status = "NEEDS_ANALYSIS"
    selected_product_status = None
    selected_raw_product_status = None
    if user_id and (selected_portfolio_id or selected_portfolio_hash):
        try:
            portfolio = (
                persistence_store().get_portfolio(user_id, selected_portfolio_id)
                if selected_portfolio_id
                else persistence_store().get_portfolio_by_hash(user_id, selected_portfolio_hash)
            )
            if portfolio:
                running = persistence_store().latest_running_portfolio_run(
                    user_id,
                    portfolio_id=portfolio.get("portfolioId") if selected_portfolio_id else None,
                    portfolio_hash=portfolio.get("portfolioHash") if not selected_portfolio_id else None,
                )
                latest_success = persistence_store().latest_successful_portfolio_run(
                    user_id,
                    portfolio_id=portfolio.get("portfolioId") if selected_portfolio_id else None,
                    portfolio_hash=portfolio.get("portfolioHash") if not selected_portfolio_id else None,
                )
                if running:
                    selected_portfolio_status = "REFRESHING"
                elif latest_success:
                    selected_dashboard = load_product_dashboard_for_saved_portfolio(
                        user_id,
                        portfolio_id=portfolio.get("portfolioId") if selected_portfolio_id else None,
                        portfolio_hash=portfolio.get("portfolioHash") if not selected_portfolio_id else None,
                        compact=True,
                    )
                    selected_portfolio_status = normalize_product_status(
                        selected_dashboard.get("status") or selected_dashboard.get("productStatus")
                    )
                    selected_product_status = selected_portfolio_status
                    selected_raw_product_status = selected_dashboard.get("rawProductStatus") or selected_dashboard.get("productStatus")
                else:
                    selected_portfolio_status = "NEEDS_ANALYSIS"
            else:
                selected_portfolio_status = "ERROR"
        except Exception:
            selected_portfolio_status = "ERROR"
    elif has_running_analysis_job():
        selected_portfolio_status = "REFRESHING"
    effective_product_status = normalize_product_status(selected_product_status or product_status)
    effective_raw_product_status = selected_raw_product_status or product_status
    status.update(
        {
            "freshnessStatus": freshness.get("freshnessStatus") or status.get("freshnessStatus"),
            "productStatus": effective_product_status,
            "rawProductStatus": effective_raw_product_status,
            "needsRefresh": freshness.get("needsRefresh"),
            "market_data": "REFRESHING" if market_refreshing else ("FRESH" if freshness.get("marketDataFresh") else "STALE"),
            "intraday_nowcast": "REFRESHING" if intraday_refreshing else ("FRESH" if freshness.get("intradayNowcastFresh") else "STALE"),
            "news_overlay": "REFRESHING" if news_refreshing else ("FRESH" if news_status.get("fresh") else ("DISABLED" if news_status.get("disabled") else "STALE")),
            "selected_portfolio": selected_portfolio_status,
            "product_mode": effective_product_status,
            "schedulerDetail": {
                "lastStartedAt": SCHEDULER_STATE.get("lastStartedAt"),
                "lastCycleAt": SCHEDULER_STATE.get("lastCycleAt"),
                "lastError": SCHEDULER_STATE.get("lastError"),
            },
            "recommendationState": "SEE_PRODUCT_DASHBOARD",
            "canExecuteRecommendations": None,
            "blockers": blockers,
            "formalRecommendationCount": None,
            "referenceOnlyCount": None,
            "failGateCount": None,
            "eventOverlayMode": (manifest.get("event_overlay_status") or {}).get("mode"),
            "eventOverlayTradeGateUsage": (manifest.get("event_overlay_status") or {}).get("trade_gate_usage"),
        }
    )
    return status


def path_writable_status(path):
    target = Path(path)
    status = {
        "path": str(target),
        "exists": target.exists(),
        "writable": False,
    }
    probe = None
    try:
        target.mkdir(parents=True, exist_ok=True)
        probe = target / f".write_check_{os.getpid()}_{uuid.uuid4().hex}.tmp"
        probe.write_text("ok", encoding="utf-8")
        status.update({"exists": True, "writable": True})
    except Exception as exc:
        status["error"] = tail_diagnostic_text(str(exc), max_chars=500, max_lines=4)
    finally:
        if probe:
            try:
                probe.unlink(missing_ok=True)
            except OSError:
                pass
    return status


def file_status(path):
    target = Path(path)
    payload = {
        "path": str(target),
        "exists": target.exists(),
        "mtimeUtc": None,
        "sizeBytes": None,
    }
    if target.exists():
        stat = target.stat()
        payload.update(
            {
                "mtimeUtc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                "sizeBytes": stat.st_size,
            }
        )
    return payload


def manifest_run_summary(manifest):
    manifest = manifest or {}
    bundle = active_bundle(manifest)
    return {
        "activeHedgemateRun": bundle.get("hedgemate_run") or manifest.get("active_hedgemate_run"),
        "activeScenarioRun": bundle.get("scenario_run") or manifest.get("active_scenario_run"),
        "activeFinalRun": bundle.get("final_market_state_run") or manifest.get("active_final_run"),
        "activeBacktestRun": bundle.get("backtest_run") or manifest.get("active_backtest_run"),
        "dataVersion": bundle.get("data_version") or manifest.get("data_version"),
        "generatedAtUtc": bundle.get("generated_at_utc") or manifest.get("generated_at_utc"),
        "freshnessStatus": bundle.get("freshness_status") or manifest.get("freshness_status"),
    }


def safe_database_status():
    health = database_health()
    payload = {
        "ok": bool(health.get("ok")),
        "status": "CONNECTED" if health.get("ok") else "DISCONNECTED",
        "kind": health.get("kind"),
        "database": health.get("database"),
    }
    if health.get("fallbackReason"):
        payload["fallbackReason"] = tail_diagnostic_text(health.get("fallbackReason"), max_chars=500, max_lines=4)
    if health.get("error"):
        payload["error"] = tail_diagnostic_text(health.get("error"), max_chars=500, max_lines=4)
    return payload


def runtime_debug_payload():
    hedgemate_manifest_path = ROOT / "outputs" / "latest_manifest.json"
    scenario_manifest_path = SCENARIO_OUTPUT_DIR / "latest_manifest.json"
    hedgemate_manifest = read_json(hedgemate_manifest_path, {}) if hedgemate_manifest_path.exists() else {}
    scenario_manifest = read_json(scenario_manifest_path, {}) if scenario_manifest_path.exists() else {}
    hedgemate_runs = find_available_run_ids(ROOT / "outputs" / "processed")
    scenario_runs = find_scenario_run_ids(SCENARIO_OUTPUT_DIR / "final")
    return {
        "process": {
            "cwd": os.getcwd(),
            "sysExecutable": sys.executable,
            "pythonVersion": sys.version.split()[0],
        },
        "paths": {
            "ROOT": str(ROOT),
            "SCENARIO_RESEARCH_ROOT": str(SCENARIO_RESEARCH_ROOT),
        },
        "manifests": {
            "HEDGEMATE_MANIFEST_PATH": file_status(hedgemate_manifest_path),
            "SCENARIO_MANIFEST_PATH": file_status(scenario_manifest_path),
        },
        "writable": {
            "hedgemateOutputs": path_writable_status(ROOT / "outputs"),
            "hedgemateInputs": path_writable_status(ROOT / "inputs"),
            "hedgemateRunInputs": path_writable_status(ROOT / "outputs" / "run_inputs"),
            "scenarioResearchOutputs": path_writable_status(SCENARIO_OUTPUT_DIR),
        },
        "runs": {
            "hedgemateManifest": manifest_run_summary(hedgemate_manifest),
            "scenarioManifest": manifest_run_summary(scenario_manifest),
            "latestAvailableHedgemateRun": hedgemate_runs[0] if hedgemate_runs else None,
            "latestAvailableScenarioRun": scenario_runs[0] if scenario_runs else None,
        },
        "database": safe_database_status(),
        "scheduler": {
            "status": scheduler_status_value(),
            "enabled": bool(SCHEDULER_STATE.get("enabled")),
            "running": bool(SCHEDULER_STATE.get("running")),
            "lastStartedAt": SCHEDULER_STATE.get("lastStartedAt"),
            "lastCycleAt": SCHEDULER_STATE.get("lastCycleAt"),
            "lastError": tail_diagnostic_text(SCHEDULER_STATE.get("lastError"), max_chars=500, max_lines=4)
            if SCHEDULER_STATE.get("lastError")
            else None,
        },
    }


def log_runtime_startup_summary():
    try:
        print(
            "HedgeMate runtime startup: "
            + json.dumps(runtime_debug_payload(), ensure_ascii=False),
            flush=True,
        )
    except Exception as exc:
        print(f"HedgeMate runtime startup diagnostics failed: {sanitize_diagnostic_text(exc)}", file=sys.stderr, flush=True)


def count_by_field(rows, field, default="unknown"):
    counts = {}
    for row in rows or []:
        key = str(row.get(field) if isinstance(row, dict) else "").strip() or default
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def scenario_sensitivity_as_of(manifest, rows):
    bundle = active_bundle(manifest)
    for key in ("as_of_date", "asOfDate", "date", "data_version", "dataVersion"):
        for row in rows or []:
            value = row.get(key) if isinstance(row, dict) else None
            if value not in (None, ""):
                return str(value)
    return (
        bundle.get("scenario_vector_as_of_date")
        or manifest.get("scenario_vector_as_of_date")
        or bundle.get("data_version")
        or manifest.get("data_version")
    )


def load_scenario_sensitivities_payload(ticker=None):
    manifest = read_product_manifest()
    path = resolve_product_artifact(manifest, "assetScenarioSensitivity", OUTPUT_PROCESSED_DIR)
    all_rows = read_csv_rows(path) if path else []
    requested_ticker = str(ticker or "").strip()
    rows = all_rows
    if requested_ticker:
        normalized_ticker = normalize_asset_query(requested_ticker)
        rows = [
            row for row in all_rows
            if normalize_asset_query(
                row.get("ticker")
                or row.get("asset_ticker")
                or row.get("symbol")
                or row.get("asset")
            ) == normalized_ticker
        ]
    return {
        "rows": rows,
        "rowCount": len(rows),
        "totalRowCount": len(all_rows),
        "requestedTicker": requested_ticker or None,
        "asOfDate": scenario_sensitivity_as_of(manifest, rows),
        "sourceQualityCounts": count_by_field(rows, "source_quality"),
        "gateEligibleCounts": count_by_field(rows, "gate_eligible"),
        "eventOrSeedDependentCounts": count_by_field(rows, "event_or_seed_dependent"),
        "artifactPath": scenario_artifact(path),
        "artifactSha256": file_sha256(path) if path else None,
    }


def save_portfolio_for_user(user_id, payload, portfolio_id=None):
    normalized = normalize_portfolio_api_payload(payload)
    if portfolio_id is None:
        return persistence_store().create_portfolio(user_id, normalized)
    return persistence_store().update_portfolio(user_id, portfolio_id, normalized)


def launch_saved_portfolio_analysis(user_id, portfolio_id, payload=None, runner=subprocess.run, thread_factory=threading.Thread):
    store = persistence_store()
    portfolio = store.get_portfolio(user_id, portfolio_id)
    if not portfolio:
        raise FileNotFoundError("Portfolio not found")
    extra = dict(payload or {})
    extra.pop("portfolioRows", None)
    extra.pop("assets", None)
    extra.pop("portfolioId", None)
    extra.pop("portfolio_id", None)
    job_id = extra.get("jobId") or uuid.uuid4().hex
    run_payload = portfolio_record_to_run_payload(portfolio, extra)
    run_payload["jobId"] = job_id
    prepared = prepare_run_request(run_payload, job_id=job_id)
    run_db_id = store.create_portfolio_run(
        user_id,
        portfolio.get("portfolioId"),
        portfolio.get("portfolioHash"),
        prepared.get("runId"),
        data_version=prepared.get("dataVersion"),
        status="RUNNING",
    )
    prepared.update(
        {
            "userId": int(user_id),
            "portfolioId": int(portfolio.get("portfolioId")),
            "portfolioHash": portfolio.get("portfolioHash"),
            "portfolioRunDbId": run_db_id,
            "forceReanalysis": bool(run_payload.get("forceReanalysis")),
            "ignoreAnalysisCache": bool(run_payload.get("ignoreAnalysisCache")),
        }
    )
    job = launch_run_job(prepared, runner=runner, thread_factory=thread_factory)
    db_run = store.get_portfolio_run_by_run_id(user_id, prepared.get("runId"))
    job["portfolioId"] = str(portfolio.get("portfolioId"))
    job["portfolioHash"] = portfolio.get("portfolioHash")
    job["portfolioRun"] = run_row_response(db_run)
    return job


class RequestEntityTooLarge(ValueError):
    pass


class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def _is_local_client(self):
        return self.client_address[0] in LOCALHOST_CLIENTS

    def _reject_non_local_client(self):
        if self._is_local_client():
            return False
        self._json_response({"error": "local requests only"}, status=HTTPStatus.FORBIDDEN)
        return True

    def _current_user(self):
        return current_user_from_headers(self.headers)

    def _require_user(self):
        user = self._current_user()
        if user:
            return user
        self._json_response({"error": "Authentication required", "authenticated": False}, status=HTTPStatus.UNAUTHORIZED)
        return None

    def _send_common_security_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Content-Security-Policy", CONTENT_SECURITY_POLICY)

    def _proxy_yahoo_request(self, parsed):
        rel_path = parsed.path[len("/api/yahoo/"):]
        if not rel_path or rel_path.startswith("/") or ".." in rel_path.split("/"):
            return self._json_response({"error": "Invalid Yahoo proxy path"}, status=HTTPStatus.BAD_REQUEST)
        target = f"{YAHOO_FINANCE_BASE_URL}/{rel_path}"
        if parsed.query:
            target = f"{target}?{parsed.query}"
        request = urllib.request.Request(
            target,
            headers={
                "User-Agent": "Mozilla/5.0 HedgeMate/1.0",
                "Accept": "application/json,text/plain,*/*",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=YAHOO_PROXY_TIMEOUT_SECONDS) as response:
                body = response.read()
                content_type = response.headers.get("Content-Type", "application/json")
                return self._binary_response(body, content_type=content_type, status=response.status)
        except urllib.error.HTTPError as exc:
            body = exc.read()
            content_type = exc.headers.get("Content-Type", "application/json") if exc.headers else "application/json"
            return self._binary_response(body, content_type=content_type, status=exc.code)
        except urllib.error.URLError as exc:
            return self._json_response({"error": f"Yahoo proxy request failed: {exc.reason}"}, status=HTTPStatus.BAD_GATEWAY)

    def do_GET(self):
        parsed = urlparse(self.path)
        if self._reject_non_local_client():
            return
        if parsed.path.startswith("/api/yahoo/"):
            return self._proxy_yahoo_request(parsed)
        if parsed.path == "/api/health":
            return self._json_response({"ok": True})
        if parsed.path == "/api/auth/me":
            user = self._current_user()
            return self._json_response({"authenticated": bool(user), "user": public_user(user)})
        if parsed.path == "/api/status":
            params = parse_qs(parsed.query)
            user = self._current_user()
            status = load_service_status(
                selected_portfolio_id=params.get("portfolio_id", [None])[0],
                selected_portfolio_hash=params.get("portfolio_hash", [None])[0],
                user_id=user.get("user_id") if user else None,
            )
            http_status = HTTPStatus.OK if status.get("ok") else HTTPStatus.SERVICE_UNAVAILABLE
            return self._json_response(status, status=http_status)
        if parsed.path == "/api/debug/runtime":
            return self._json_response(runtime_debug_payload())
        if parsed.path == "/api/portfolios":
            user = self._require_user()
            if not user:
                return
            return self._json_response({"portfolios": persistence_store().list_portfolios(user["user_id"])})
        portfolio_match = re.fullmatch(r"/api/portfolios/(\d+)", parsed.path)
        if portfolio_match:
            user = self._require_user()
            if not user:
                return
            portfolio = persistence_store().get_portfolio(user["user_id"], portfolio_match.group(1))
            if not portfolio:
                return self._json_response({"error": "Portfolio not found"}, status=HTTPStatus.NOT_FOUND)
            return self._json_response({"portfolio": portfolio})
        portfolio_runs_match = re.fullmatch(r"/api/portfolios/(\d+)/runs", parsed.path)
        if portfolio_runs_match:
            user = self._require_user()
            if not user:
                return
            portfolio = persistence_store().get_portfolio(user["user_id"], portfolio_runs_match.group(1))
            if not portfolio:
                return self._json_response({"error": "Portfolio not found"}, status=HTTPStatus.NOT_FOUND)
            runs = persistence_store().list_portfolio_runs(user["user_id"], portfolio_runs_match.group(1))
            return self._json_response({"runs": [run_row_response(row) for row in runs]})
        run_match = re.fullmatch(r"/api/portfolio-runs/([^/]+)", parsed.path)
        if run_match:
            user = self._require_user()
            if not user:
                return
            run = persistence_store().get_portfolio_run_by_run_id(user["user_id"], urllib.parse.unquote(run_match.group(1)))
            if not run:
                return self._json_response({"error": "Portfolio run not found"}, status=HTTPStatus.NOT_FOUND)
            return self._json_response({"run": run_row_response(run)})
        if parsed.path == "/api/runs":
            runs = find_available_run_ids()
            return self._json_response({"runs": runs, "latestRunId": runs[0] if runs else None})
        if parsed.path == "/api/scenario-runs":
            runs = find_scenario_run_ids()
            return self._json_response({"runs": runs, "latestRunId": runs[0] if runs else None})
        if parsed.path == "/api/assets":
            return self._json_response({"assets": asset_options()})
        if parsed.path == "/api/data-freshness":
            return self._json_response(load_data_freshness())
        if parsed.path == "/api/scenario-sensitivities":
            params = parse_qs(parsed.query)
            return self._json_response(load_scenario_sensitivities_payload(params.get("ticker", [None])[0]))
        if parsed.path == "/api/active-bundle":
            manifest = read_product_manifest()
            if not manifest:
                return self._json_response({"error": "No active bundle available"}, status=HTTPStatus.NOT_FOUND)
            return self._json_response(manifest)
        if parsed.path == "/api/product-dashboard":
            try:
                params = parse_qs(parsed.query)
                compact = _bool_for_api(params.get("compact", [False])[0], default=False)
                portfolio_id = params.get("portfolio_id", [None])[0]
                portfolio_hash = params.get("portfolio_hash", [None])[0]
                if portfolio_id or portfolio_hash:
                    user = self._require_user()
                    if not user:
                        return
                    dashboard = load_product_dashboard_for_saved_portfolio(
                        user["user_id"],
                        portfolio_id=portfolio_id,
                        portfolio_hash=portfolio_hash,
                        compact=compact,
                    )
                else:
                    dashboard = load_product_dashboard_data(compact=compact)
                if compact:
                    dashboard = compact_product_dashboard_payload(dashboard)
                return self._json_response(dashboard)
            except FileNotFoundError as exc:
                return self._json_response({"error": str(exc)}, status=HTTPStatus.NOT_FOUND)
        if parsed.path == "/api/dashboard":
            params = parse_qs(parsed.query)
            requested = params.get("run_id", [None])[0]
            runs = find_available_run_ids()
            run_id = requested or (runs[0] if runs else None)
            if not run_id:
                return self._json_response({"error": "No runs available"}, status=HTTPStatus.NOT_FOUND)
            try:
                return self._json_response(load_dashboard_data(run_id))
            except FileNotFoundError as exc:
                return self._json_response({"error": str(exc)}, status=HTTPStatus.NOT_FOUND)
        if parsed.path == "/api/scenario-dashboard":
            params = parse_qs(parsed.query)
            requested = params.get("run_id", [None])[0]
            try:
                return self._json_response(load_scenario_dashboard_data(requested))
            except FileNotFoundError as exc:
                return self._json_response({"error": str(exc)}, status=HTTPStatus.NOT_FOUND)
        if parsed.path == "/api/run-status":
            params = parse_qs(parsed.query)
            job_id = params.get("job_id", [None])[0]
            if not job_id:
                return self._json_response({"error": "job_id is required"}, status=HTTPStatus.BAD_REQUEST)
            job = _snapshot_run_job(job_id)
            if not job:
                return self._json_response({"error": f"Job not found: {job_id}"}, status=HTTPStatus.NOT_FOUND)
            return self._json_response(job)
        if parsed.path.startswith("/artifact/"):
            rel_path = unquote(parsed.path[len("/artifact/"):])
            artifact_path = safe_rel_artifact(rel_path)
            if not artifact_path:
                self.send_error(HTTPStatus.NOT_FOUND, "Artifact not found")
                return
            return self._serve_file(artifact_path)
        if parsed.path == "/favicon.ico":
            self.send_response(HTTPStatus.NO_CONTENT)
            self.send_header("Cache-Control", "public, max-age=86400")
            self.end_headers()
            return
        frontend_redirects = {
            "/": "/",
            "/index.html": "/",
            "/scenario.html": "/market-state",
            "/logic.html": "/report",
        }
        if parsed.path in frontend_redirects:
            return self._redirect_to_frontend(frontend_redirects[parsed.path])
        frontend_assets = {"/app.js", "/unified.js", "/styles.css", "/scenario.js", "/logic.js"}
        if parsed.path in frontend_assets:
            return self._json_response(
                {
                    "error": "Frontend static assets are served by the Vite app, not the API server.",
                    "frontendUrl": FRONTEND_UI_BASE,
                },
                status=HTTPStatus.GONE,
            )
        return self._json_response(
            {
                "error": "Unknown API endpoint. The HedgeMate frontend is served on port 5173.",
                "frontendUrl": FRONTEND_UI_BASE,
            },
            status=HTTPStatus.NOT_FOUND,
        )

    def do_POST(self):
        parsed = urlparse(self.path)
        analyze_match = re.fullmatch(r"/api/portfolios/(\d+)/analyze", parsed.path)
        allowed_paths = {
            "/api/auth/register",
            "/api/auth/login",
            "/api/auth/logout",
            "/api/portfolios",
            "/api/run",
            "/api/price-lookup",
            "/api/portfolio/preview",
            "/api/refresh-market-data",
            "/api/refresh-intraday-news",
            "/api/product-dashboard",
        }
        if parsed.path not in allowed_paths and not analyze_match:
            self.send_error(HTTPStatus.NOT_FOUND, "Unknown endpoint")
            return
        if self._reject_non_local_client():
            return
        if parsed.path == "/api/auth/logout":
            payload, cookie = auth_logout(self.headers)
            return self._json_response(payload, extra_headers={"Set-Cookie": cookie})
        content_type = (self.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            return self._json_response({"error": "application/json 요청만 허용됩니다."}, status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
        try:
            payload = self._read_json_body()
            if parsed.path == "/api/auth/register":
                try:
                    body, cookie = auth_register(payload)
                except DuplicateEmailError:
                    return self._json_response({"error": "Email is already registered."}, status=HTTPStatus.CONFLICT)
                return self._json_response(body, status=HTTPStatus.CREATED, extra_headers={"Set-Cookie": cookie})
            if parsed.path == "/api/auth/login":
                try:
                    body, cookie = auth_login(payload)
                except PermissionError as exc:
                    return self._json_response({"error": str(exc)}, status=HTTPStatus.UNAUTHORIZED)
                return self._json_response(body, extra_headers={"Set-Cookie": cookie})
            if parsed.path == "/api/portfolios":
                user = self._require_user()
                if not user:
                    return
                portfolio = save_portfolio_for_user(user["user_id"], payload)
                return self._json_response({"portfolio": portfolio}, status=HTTPStatus.CREATED)
            if analyze_match:
                user = self._require_user()
                if not user:
                    return
                result = launch_saved_portfolio_analysis(user["user_id"], analyze_match.group(1), payload)
                return self._json_response(result, status=HTTPStatus.ACCEPTED)
            if parsed.path == "/api/price-lookup":
                return self._json_response(
                    lookup_price(
                        payload.get("asset") or payload.get("ticker"),
                        quantity=payload.get("quantity"),
                        amount_krw=payload.get("amountKrw"),
                        use_live=bool(payload.get("useLivePrices")),
                    )
                )
            if parsed.path == "/api/portfolio/preview":
                return self._json_response(preview_portfolio(payload))
            if parsed.path == "/api/product-dashboard":
                compact = _bool_for_api(payload.get("compact"), default=False)
                portfolio_id = payload.get("portfolioId") or payload.get("portfolio_id")
                portfolio_hash = payload.get("portfolioHash") or payload.get("portfolio_hash")
                if portfolio_id or portfolio_hash:
                    user = self._require_user()
                    if not user:
                        return
                    dashboard = load_product_dashboard_for_saved_portfolio(
                        user["user_id"],
                        portfolio_id=portfolio_id,
                        portfolio_hash=portfolio_hash,
                        compact=compact,
                    )
                else:
                    dashboard = load_product_dashboard_for_portfolio(payload, compact=compact)
                if compact:
                    dashboard = compact_product_dashboard_payload(dashboard)
                return self._json_response(dashboard)
            if parsed.path == "/api/refresh-market-data":
                result = launch_refresh_market_data_job(payload)
                status = HTTPStatus.OK if result.get("status") == "skipped_latest" else HTTPStatus.ACCEPTED
                return self._json_response(result, status=status)
            if parsed.path == "/api/refresh-intraday-news":
                result = launch_intraday_news_overlay_job(payload)
                status = HTTPStatus.OK if result.get("status") == "skipped_latest" else HTTPStatus.ACCEPTED
                return self._json_response(result, status=status)
            portfolio_id = payload.get("portfolioId") or payload.get("portfolio_id")
            if portfolio_id:
                user = self._require_user()
                if not user:
                    return
                result = launch_saved_portfolio_analysis(user["user_id"], portfolio_id, payload)
                return self._json_response(result, status=HTTPStatus.ACCEPTED)
            prepared_request = prepare_run_request(payload)
            result = launch_run_job(prepared_request)
            return self._json_response(result, status=HTTPStatus.ACCEPTED)
        except RequestEntityTooLarge as exc:
            return self._json_response({"error": str(exc)}, status=HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        except ValueError as exc:
            return self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except RuntimeError as exc:
            return self._json_response({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_PUT(self):
        parsed = urlparse(self.path)
        portfolio_match = re.fullmatch(r"/api/portfolios/(\d+)", parsed.path)
        if not portfolio_match:
            self.send_error(HTTPStatus.NOT_FOUND, "Unknown endpoint")
            return
        if self._reject_non_local_client():
            return
        user = self._require_user()
        if not user:
            return
        content_type = (self.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            return self._json_response({"error": "application/json requests only"}, status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
        try:
            payload = self._read_json_body()
            portfolio = save_portfolio_for_user(user["user_id"], payload, portfolio_id=portfolio_match.group(1))
            if not portfolio:
                return self._json_response({"error": "Portfolio not found"}, status=HTTPStatus.NOT_FOUND)
            return self._json_response({"portfolio": portfolio})
        except RequestEntityTooLarge as exc:
            return self._json_response({"error": str(exc)}, status=HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        except ValueError as exc:
            return self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        portfolio_match = re.fullmatch(r"/api/portfolios/(\d+)", parsed.path)
        if not portfolio_match:
            self.send_error(HTTPStatus.NOT_FOUND, "Unknown endpoint")
            return
        if self._reject_non_local_client():
            return
        user = self._require_user()
        if not user:
            return
        deleted = persistence_store().delete_portfolio(user["user_id"], portfolio_match.group(1))
        if not deleted:
            return self._json_response({"error": "Portfolio not found"}, status=HTTPStatus.NOT_FOUND)
        return self._json_response({"ok": True})

    def _read_json_body(self):
        raw_length = self.headers.get("Content-Length")
        if raw_length in (None, ""):
            raise ValueError("Content-Length header is required")
        try:
            length = int(raw_length)
        except (TypeError, ValueError) as exc:
            raise ValueError("Content-Length header must be an integer") from exc
        if length < 0:
            raise ValueError("Content-Length header must be non-negative")
        if length > MAX_JSON_BODY_BYTES:
            raise RequestEntityTooLarge(f"JSON body exceeds {MAX_JSON_BODY_BYTES} bytes")
        try:
            return json.loads(self.rfile.read(length).decode("utf-8")) if length > 0 else {}
        except json.JSONDecodeError as exc:
            raise ValueError("잘못된 JSON 요청입니다.") from exc

    def _json_response(self, payload, status=HTTPStatus.OK, extra_headers=None):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        return self._binary_response(body, content_type="application/json; charset=utf-8", status=status, extra_headers=extra_headers)

    def _binary_response(self, body, content_type, status=HTTPStatus.OK, extra_headers=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self._send_common_security_headers()
        for key, value in (extra_headers or {}).items():
            if isinstance(value, (list, tuple)):
                for item in value:
                    self.send_header(key, str(item))
            else:
                self.send_header(key, str(value))
        self.send_header("Content-Length", str(len(body)))
        try:
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            return

    def _redirect_to_frontend(self, frontend_path):
        target = f"{FRONTEND_UI_BASE}{frontend_path}"
        self.send_response(HTTPStatus.TEMPORARY_REDIRECT)
        self.send_header("Location", target)
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self._send_common_security_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _serve_file(self, path):
        content = path.read_bytes()
        mime, _ = mimetypes.guess_type(str(path))
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", (mime or "application/octet-stream") + ("; charset=utf-8" if mime and mime.startswith("text/") else ""))
        if path.suffix in {".html", ".js", ".css"}:
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
        self._send_common_security_headers()
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format, *args):
        return


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Serve HedgeMate dashboard UI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument(
        "--allow-remote-dashboard",
        action="store_true",
        help="Allow binding the dashboard to a non-loopback interface.",
    )
    parser.add_argument(
        "--no-startup-refresh",
        action="store_true",
        help="Do not auto-refresh stale market/scenario/product outputs when the server starts.",
    )
    parser.add_argument(
        "--no-scheduler",
        action="store_true",
        help="Do not start the 3-hour common data refresh scheduler thread.",
    )
    return parser.parse_args(argv)


def is_loopback_host(host):
    normalized = str(host or "").strip().lower()
    if normalized in {"localhost"}:
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def main(argv=None):
    args = parse_args(argv)
    if not is_loopback_host(args.host) and not args.allow_remote_dashboard:
        raise SystemExit(
            "Refusing to expose the dashboard on a non-loopback host without --allow-remote-dashboard."
        )
    persistence_store().init_db()
    log_runtime_startup_summary()
    server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    print(f"HedgeMate dashboard running at http://{args.host}:{args.port}")
    if not args.no_startup_refresh:
        startup_job = launch_startup_market_refresh_if_needed()
        if startup_job.get("status") == "skipped_latest":
            print("Startup market refresh skipped: outputs are already current.")
        elif startup_job.get("attachedToExisting"):
            print(f"Startup market refresh attached to existing job {startup_job.get('jobId')}.")
        else:
            print(f"Startup market refresh job {startup_job.get('jobId')} queued.")
    if not args.no_scheduler:
        start_scheduler_thread()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
