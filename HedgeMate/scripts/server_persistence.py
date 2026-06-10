#!/usr/bin/env python3
"""Small persistence layer for the Bee-cast HedgeMate server.

The server uses SQLite by default so the packaged app keeps working on a
student laptop. When DATABASE_URL points at MySQL, the same repository methods
use PyMySQL and leave secrets inside environment variables only.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


DEFAULT_SQLITE_PATH = Path(__file__).resolve().parents[1] / "outputs" / "server" / "hedgemate.sqlite3"


class PersistenceError(RuntimeError):
    pass


class DuplicateEmailError(PersistenceError):
    pass


class DuplicateRefreshJobError(PersistenceError):
    pass


def utc_now_iso():
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0).isoformat(sep=" ")


def _json_dumps(value):
    return json.dumps(value or {}, ensure_ascii=False, sort_keys=True)


def _json_loads(value, fallback=None):
    if value in (None, ""):
        return {} if fallback is None else fallback
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return {} if fallback is None else fallback


def _as_optional_float(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class PersistenceStore:
    def __init__(self, database_url=None, sqlite_path=None):
        self.database_url = database_url if database_url is not None else os.environ.get("DATABASE_URL")
        explicit_sqlite = sqlite_path if sqlite_path is not None else os.environ.get("HEDGEMATE_DB_PATH")
        self.sqlite_path = Path(explicit_sqlite) if explicit_sqlite else DEFAULT_SQLITE_PATH
        self.kind = self._detect_kind(self.database_url)
        self._initialized = False
        self._lock = threading.RLock()

    @staticmethod
    def _detect_kind(database_url):
        if not database_url:
            return "sqlite"
        scheme = urlparse(database_url).scheme.lower()
        if scheme.startswith("mysql"):
            return "mysql"
        if scheme.startswith("sqlite"):
            return "sqlite"
        raise PersistenceError("Unsupported DATABASE_URL scheme")

    @property
    def safe_database_label(self):
        if self.kind == "sqlite":
            return f"sqlite:{self.sqlite_path}"
        parsed = urlparse(self.database_url or "")
        host = parsed.hostname or "localhost"
        db_name = parsed.path.lstrip("/") or ""
        return f"mysql://{host}/{db_name}"

    def _connect(self):
        if self.kind == "sqlite":
            self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(self.sqlite_path), timeout=30, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            return conn

        try:
            import pymysql
            import pymysql.cursors
        except ImportError as exc:
            raise PersistenceError("PyMySQL is required when DATABASE_URL uses MySQL") from exc

        parsed = urlparse(self.database_url or "")
        query = parse_qs(parsed.query)
        charset = (query.get("charset") or ["utf8mb4"])[0]
        return pymysql.connect(
            host=parsed.hostname or "localhost",
            port=parsed.port or 3306,
            user=unquote(parsed.username or ""),
            password=unquote(parsed.password or ""),
            database=parsed.path.lstrip("/"),
            charset=charset,
            autocommit=False,
            cursorclass=pymysql.cursors.DictCursor,
        )

    def _sql(self, sql):
        return sql.replace("?", "%s") if self.kind == "mysql" else sql

    def init_db(self):
        with self._lock:
            if self._initialized:
                return
            conn = self._connect()
            try:
                for statement in self._schema_statements():
                    conn.execute(self._sql(statement)) if self.kind == "sqlite" else conn.cursor().execute(self._sql(statement))
                conn.commit()
                self._initialized = True
            finally:
                conn.close()

    def _schema_statements(self):
        if self.kind == "mysql":
            return [
                """
                CREATE TABLE IF NOT EXISTS users (
                  id BIGINT PRIMARY KEY AUTO_INCREMENT,
                  email VARCHAR(255) NOT NULL UNIQUE,
                  password_hash VARCHAR(255) NOT NULL,
                  display_name VARCHAR(100),
                  created_at DATETIME NOT NULL,
                  updated_at DATETIME NOT NULL
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS sessions (
                  id CHAR(64) PRIMARY KEY,
                  user_id BIGINT NOT NULL,
                  expires_at DATETIME NOT NULL,
                  created_at DATETIME NOT NULL,
                  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS portfolios (
                  id BIGINT PRIMARY KEY AUTO_INCREMENT,
                  user_id BIGINT NOT NULL,
                  name VARCHAR(120) NOT NULL,
                  portfolio_hash CHAR(64) NOT NULL,
                  normalized_input_json JSON,
                  created_at DATETIME NOT NULL,
                  updated_at DATETIME NOT NULL,
                  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                  INDEX idx_portfolios_user (user_id),
                  INDEX idx_portfolios_hash (portfolio_hash)
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS portfolio_assets (
                  id BIGINT PRIMARY KEY AUTO_INCREMENT,
                  portfolio_id BIGINT NOT NULL,
                  ticker VARCHAR(32) NOT NULL,
                  asset_name VARCHAR(255),
                  quantity DECIMAL(24, 8),
                  avg_price DECIMAL(24, 8),
                  currency VARCHAR(8),
                  weight DECIMAL(18, 8),
                  created_at DATETIME NOT NULL,
                  FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE,
                  INDEX idx_assets_portfolio (portfolio_id)
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS portfolio_runs (
                  id BIGINT PRIMARY KEY AUTO_INCREMENT,
                  user_id BIGINT NOT NULL,
                  portfolio_id BIGINT NOT NULL,
                  portfolio_hash CHAR(64) NOT NULL,
                  run_id VARCHAR(120) NOT NULL,
                  status VARCHAR(32) NOT NULL,
                  artifact_dir TEXT,
                  data_version VARCHAR(32),
                  market_snapshot_id BIGINT,
                  scenario_snapshot_id BIGINT,
                  started_at DATETIME,
                  finished_at DATETIME,
                  error_message TEXT,
                  created_at DATETIME NOT NULL,
                  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                  FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE,
                  INDEX idx_runs_portfolio_status (portfolio_id, status),
                  INDEX idx_runs_hash_status (portfolio_hash, status)
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS refresh_jobs (
                  id BIGINT PRIMARY KEY AUTO_INCREMENT,
                  job_id VARCHAR(120) NOT NULL UNIQUE,
                  job_type VARCHAR(64) NOT NULL,
                  status VARCHAR(32) NOT NULL,
                  trigger_type VARCHAR(32) NOT NULL,
                  started_at DATETIME,
                  finished_at DATETIME,
                  error_message TEXT,
                  created_at DATETIME NOT NULL,
                  INDEX idx_refresh_jobs_type_status (job_type, status)
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS data_snapshots (
                  id BIGINT PRIMARY KEY AUTO_INCREMENT,
                  snapshot_type VARCHAR(64) NOT NULL,
                  data_version VARCHAR(32),
                  as_of_kst DATETIME,
                  artifact_path TEXT,
                  freshness_status VARCHAR(32) NOT NULL,
                  created_at DATETIME NOT NULL,
                  INDEX idx_snapshots_type_created (snapshot_type, created_at)
                )
                """,
            ]

        return [
            """
            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              email TEXT NOT NULL UNIQUE,
              password_hash TEXT NOT NULL,
              display_name TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS sessions (
              id TEXT PRIMARY KEY,
              user_id INTEGER NOT NULL,
              expires_at TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS portfolios (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL,
              name TEXT NOT NULL,
              portfolio_hash TEXT NOT NULL,
              normalized_input_json TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_portfolios_user ON portfolios (user_id)",
            "CREATE INDEX IF NOT EXISTS idx_portfolios_hash ON portfolios (portfolio_hash)",
            """
            CREATE TABLE IF NOT EXISTS portfolio_assets (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              portfolio_id INTEGER NOT NULL,
              ticker TEXT NOT NULL,
              asset_name TEXT,
              quantity REAL,
              avg_price REAL,
              currency TEXT,
              weight REAL,
              created_at TEXT NOT NULL,
              FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_assets_portfolio ON portfolio_assets (portfolio_id)",
            """
            CREATE TABLE IF NOT EXISTS portfolio_runs (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL,
              portfolio_id INTEGER NOT NULL,
              portfolio_hash TEXT NOT NULL,
              run_id TEXT NOT NULL,
              status TEXT NOT NULL,
              artifact_dir TEXT,
              data_version TEXT,
              market_snapshot_id INTEGER,
              scenario_snapshot_id INTEGER,
              started_at TEXT,
              finished_at TEXT,
              error_message TEXT,
              created_at TEXT NOT NULL,
              FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
              FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_runs_portfolio_status ON portfolio_runs (portfolio_id, status)",
            "CREATE INDEX IF NOT EXISTS idx_runs_hash_status ON portfolio_runs (portfolio_hash, status)",
            """
            CREATE TABLE IF NOT EXISTS refresh_jobs (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              job_id TEXT NOT NULL UNIQUE,
              job_type TEXT NOT NULL,
              status TEXT NOT NULL,
              trigger_type TEXT NOT NULL,
              started_at TEXT,
              finished_at TEXT,
              error_message TEXT,
              created_at TEXT NOT NULL
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_refresh_jobs_type_status ON refresh_jobs (job_type, status)",
            """
            CREATE TABLE IF NOT EXISTS data_snapshots (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              snapshot_type TEXT NOT NULL,
              data_version TEXT,
              as_of_kst TEXT,
              artifact_path TEXT,
              freshness_status TEXT NOT NULL,
              created_at TEXT NOT NULL
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_snapshots_type_created ON data_snapshots (snapshot_type, created_at)",
        ]

    def health(self):
        try:
            self.init_db()
            conn = self._connect()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
            finally:
                conn.close()
            return {"ok": True, "kind": self.kind, "database": self.safe_database_label}
        except Exception as exc:
            return {"ok": False, "kind": self.kind, "database": self.safe_database_label, "error": str(exc)}

    def _fetchone(self, sql, args=()):
        self.init_db()
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute(self._sql(sql), args)
            row = cursor.fetchone()
            return dict(row) if row is not None else None
        finally:
            conn.close()

    def _fetchall(self, sql, args=()):
        self.init_db()
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute(self._sql(sql), args)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def _execute(self, sql, args=()):
        self.init_db()
        with self._lock:
            conn = self._connect()
            try:
                cursor = conn.cursor()
                cursor.execute(self._sql(sql), args)
                conn.commit()
                return cursor.lastrowid
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def create_user(self, email, password_hash, display_name=None):
        email_key = str(email or "").strip().lower()
        if not email_key:
            raise ValueError("email is required")
        now = utc_now_iso()
        try:
            user_id = self._execute(
                """
                INSERT INTO users (email, password_hash, display_name, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (email_key, password_hash, display_name, now, now),
            )
        except Exception as exc:
            if "UNIQUE" in str(exc).upper() or "DUPLICATE" in str(exc).upper():
                raise DuplicateEmailError("email already registered") from exc
            raise
        return self.get_user_by_id(user_id)

    def get_user_by_email(self, email):
        return self._fetchone("SELECT * FROM users WHERE email = ?", (str(email or "").strip().lower(),))

    def get_user_by_id(self, user_id):
        return self._fetchone("SELECT * FROM users WHERE id = ?", (int(user_id),))

    def create_session(self, session_id, user_id, expires_at):
        now = utc_now_iso()
        self._execute(
            "INSERT INTO sessions (id, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)",
            (session_id, int(user_id), expires_at, now),
        )
        return self.get_session(session_id)

    def get_session(self, session_id):
        row = self._fetchone(
            """
            SELECT sessions.id, sessions.user_id, sessions.expires_at, sessions.created_at,
                   users.email, users.display_name
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.id = ?
            """,
            (session_id,),
        )
        if not row:
            return None
        expires_at = str(row.get("expires_at") or "")
        if expires_at and expires_at <= utc_now_iso():
            self.delete_session(session_id)
            return None
        return row

    def delete_session(self, session_id):
        self._execute("DELETE FROM sessions WHERE id = ?", (session_id,))

    def create_portfolio(self, user_id, payload):
        self.init_db()
        normalized = payload.get("normalizedInput") or {}
        assets = payload.get("assets") or []
        now = utc_now_iso()
        with self._lock:
            conn = self._connect()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    self._sql(
                        """
                        INSERT INTO portfolios (user_id, name, portfolio_hash, normalized_input_json, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """
                    ),
                    (
                        int(user_id),
                        payload["name"],
                        payload["portfolioHash"],
                        _json_dumps(normalized),
                        now,
                        now,
                    ),
                )
                portfolio_id = cursor.lastrowid
                self._insert_assets(cursor, portfolio_id, assets, now)
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
        return self.get_portfolio(user_id, portfolio_id)

    def _insert_assets(self, cursor, portfolio_id, assets, now):
        for asset in assets:
            cursor.execute(
                self._sql(
                    """
                    INSERT INTO portfolio_assets
                      (portfolio_id, ticker, asset_name, quantity, avg_price, currency, weight, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """
                ),
                (
                    int(portfolio_id),
                    asset["ticker"],
                    asset.get("name"),
                    _as_optional_float(asset.get("quantity")),
                    _as_optional_float(asset.get("avgPrice")),
                    asset.get("currency"),
                    _as_optional_float(asset.get("weight")),
                    now,
                ),
            )

    def list_portfolios(self, user_id):
        rows = self._fetchall(
            "SELECT * FROM portfolios WHERE user_id = ? ORDER BY updated_at DESC, id DESC",
            (int(user_id),),
        )
        return [self._portfolio_with_assets(row) for row in rows]

    def get_portfolio(self, user_id, portfolio_id):
        row = self._fetchone(
            "SELECT * FROM portfolios WHERE id = ? AND user_id = ?",
            (int(portfolio_id), int(user_id)),
        )
        return self._portfolio_with_assets(row) if row else None

    def get_portfolio_by_hash(self, user_id, portfolio_hash):
        row = self._fetchone(
            """
            SELECT * FROM portfolios
            WHERE user_id = ? AND portfolio_hash = ?
            ORDER BY updated_at DESC, id DESC
            LIMIT 1
            """,
            (int(user_id), str(portfolio_hash or "")),
        )
        return self._portfolio_with_assets(row) if row else None

    def update_portfolio(self, user_id, portfolio_id, payload):
        self.init_db()
        if not self.get_portfolio(user_id, portfolio_id):
            return None
        normalized = payload.get("normalizedInput") or {}
        assets = payload.get("assets") or []
        now = utc_now_iso()
        with self._lock:
            conn = self._connect()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    self._sql(
                        """
                        UPDATE portfolios
                        SET name = ?, portfolio_hash = ?, normalized_input_json = ?, updated_at = ?
                        WHERE id = ? AND user_id = ?
                        """
                    ),
                    (
                        payload["name"],
                        payload["portfolioHash"],
                        _json_dumps(normalized),
                        now,
                        int(portfolio_id),
                        int(user_id),
                    ),
                )
                cursor.execute(self._sql("DELETE FROM portfolio_assets WHERE portfolio_id = ?"), (int(portfolio_id),))
                self._insert_assets(cursor, portfolio_id, assets, now)
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
        return self.get_portfolio(user_id, portfolio_id)

    def delete_portfolio(self, user_id, portfolio_id):
        existing = self.get_portfolio(user_id, portfolio_id)
        if not existing:
            return False
        self._execute("DELETE FROM portfolios WHERE id = ? AND user_id = ?", (int(portfolio_id), int(user_id)))
        return True

    def _portfolio_with_assets(self, row):
        if not row:
            return None
        assets = self._fetchall(
            "SELECT * FROM portfolio_assets WHERE portfolio_id = ? ORDER BY id ASC",
            (int(row["id"]),),
        )
        normalized = _json_loads(row.get("normalized_input_json"), {})
        frontend_assets = []
        for asset in assets:
            quantity = _as_optional_float(asset.get("quantity"))
            avg_price = _as_optional_float(asset.get("avg_price"))
            weight = _as_optional_float(asset.get("weight"))
            frontend_assets.append(
                {
                    "id": str(asset.get("id")),
                    "ticker": asset.get("ticker"),
                    "name": asset.get("asset_name") or asset.get("ticker"),
                    "qty": quantity or 0,
                    "quantity": quantity,
                    "cost": avg_price or 0,
                    "price": avg_price,
                    "currency": asset.get("currency"),
                    "weight": round(weight or 0),
                    "weightPct": weight,
                }
            )
        return {
            "id": str(row["id"]),
            "portfolioId": int(row["id"]),
            "userId": int(row["user_id"]),
            "name": row.get("name"),
            "purpose": normalized.get("purpose") or "",
            "portfolioHash": row.get("portfolio_hash"),
            "normalizedInput": normalized,
            "totalValue": normalized.get("totalValue") or normalized.get("totalValueKrw") or 0,
            "returnRate": normalized.get("returnRate", 0),
            "riskLevel": normalized.get("riskLevel", "Moderate"),
            "status": normalized.get("status", "server"),
            "assets": frontend_assets,
            "createdAt": row.get("created_at"),
            "updatedAt": row.get("updated_at"),
        }

    def create_portfolio_run(self, user_id, portfolio_id, portfolio_hash, run_id, data_version=None, status="RUNNING"):
        now = utc_now_iso()
        return self._execute(
            """
            INSERT INTO portfolio_runs
              (user_id, portfolio_id, portfolio_hash, run_id, status, data_version, started_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (int(user_id), int(portfolio_id), portfolio_hash, run_id, status, data_version, now, now),
        )

    def update_portfolio_run(self, run_db_id, status, artifact_dir=None, error_message=None, finished=True):
        finished_at = utc_now_iso() if finished else None
        self._execute(
            """
            UPDATE portfolio_runs
            SET status = ?, artifact_dir = COALESCE(?, artifact_dir),
                error_message = ?, finished_at = COALESCE(?, finished_at)
            WHERE id = ?
            """,
            (status, artifact_dir, error_message, finished_at, int(run_db_id)),
        )

    def latest_successful_portfolio_run(self, user_id, portfolio_id=None, portfolio_hash=None):
        if portfolio_id is not None:
            return self._fetchone(
                """
                SELECT * FROM portfolio_runs
                WHERE user_id = ? AND portfolio_id = ? AND status = 'SUCCESS'
                ORDER BY id DESC LIMIT 1
                """,
                (int(user_id), int(portfolio_id)),
            )
        return self._fetchone(
            """
            SELECT * FROM portfolio_runs
            WHERE user_id = ? AND portfolio_hash = ? AND status = 'SUCCESS'
            ORDER BY id DESC LIMIT 1
            """,
            (int(user_id), str(portfolio_hash or "")),
        )

    def latest_running_portfolio_run(self, user_id, portfolio_id=None, portfolio_hash=None):
        if portfolio_id is not None:
            return self._fetchone(
                """
                SELECT * FROM portfolio_runs
                WHERE user_id = ? AND portfolio_id = ? AND status = 'RUNNING'
                ORDER BY id DESC LIMIT 1
                """,
                (int(user_id), int(portfolio_id)),
            )
        return self._fetchone(
            """
            SELECT * FROM portfolio_runs
            WHERE user_id = ? AND portfolio_hash = ? AND status = 'RUNNING'
            ORDER BY id DESC LIMIT 1
            """,
            (int(user_id), str(portfolio_hash or "")),
        )

    def list_portfolio_runs(self, user_id, portfolio_id):
        return self._fetchall(
            """
            SELECT * FROM portfolio_runs
            WHERE user_id = ? AND portfolio_id = ?
            ORDER BY id DESC
            """,
            (int(user_id), int(portfolio_id)),
        )

    def get_portfolio_run_by_run_id(self, user_id, run_id):
        return self._fetchone(
            "SELECT * FROM portfolio_runs WHERE user_id = ? AND run_id = ? ORDER BY id DESC LIMIT 1",
            (int(user_id), str(run_id or "")),
        )

    def create_refresh_job(self, job_id, job_type, trigger_type="manual", status="PENDING"):
        now = utc_now_iso()
        try:
            return self._execute(
                """
                INSERT INTO refresh_jobs
                  (job_id, job_type, status, trigger_type, started_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (job_id, job_type, status, trigger_type, now if status == "RUNNING" else None, now),
            )
        except Exception as exc:
            if "UNIQUE" in str(exc).upper() or "DUPLICATE" in str(exc).upper():
                raise DuplicateRefreshJobError("refresh job already exists") from exc
            raise

    def update_refresh_job(self, job_id, status, error_message=None, finished=True):
        finished_at = utc_now_iso() if finished else None
        started_at = utc_now_iso() if status == "RUNNING" else None
        self._execute(
            """
            UPDATE refresh_jobs
            SET status = ?,
                started_at = COALESCE(started_at, ?),
                finished_at = COALESCE(?, finished_at),
                error_message = ?
            WHERE job_id = ?
            """,
            (status, started_at, finished_at, error_message, job_id),
        )

    def latest_refresh_job(self, job_type=None):
        if job_type:
            return self._fetchone(
                "SELECT * FROM refresh_jobs WHERE job_type = ? ORDER BY id DESC LIMIT 1",
                (job_type,),
            )
        return self._fetchone("SELECT * FROM refresh_jobs ORDER BY id DESC LIMIT 1")

    def has_running_refresh_job(self, job_type):
        row = self._fetchone(
            """
            SELECT * FROM refresh_jobs
            WHERE job_type = ? AND status IN ('PENDING', 'RUNNING')
            ORDER BY id DESC LIMIT 1
            """,
            (job_type,),
        )
        return row

    def list_refresh_jobs(self, job_type=None, limit=20):
        if job_type:
            return self._fetchall(
                "SELECT * FROM refresh_jobs WHERE job_type = ? ORDER BY id DESC LIMIT ?",
                (job_type, int(limit)),
            )
        return self._fetchall("SELECT * FROM refresh_jobs ORDER BY id DESC LIMIT ?", (int(limit),))

    def record_data_snapshot(self, snapshot_type, data_version=None, as_of_kst=None, artifact_path=None, freshness_status="UNKNOWN"):
        now = utc_now_iso()
        return self._execute(
            """
            INSERT INTO data_snapshots
              (snapshot_type, data_version, as_of_kst, artifact_path, freshness_status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (snapshot_type, data_version, as_of_kst, artifact_path, freshness_status, now),
        )
