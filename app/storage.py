import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _expiry_iso(days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


class Storage:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS lookups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    raw_phone TEXT NOT NULL,
                    normalized_phone TEXT NOT NULL,
                    country_code TEXT NOT NULL,
                    country_name TEXT NOT NULL,
                    line_type_guess TEXT NOT NULL,
                    risk_score INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    normalized_phone TEXT NOT NULL,
                    category TEXT NOT NULL,
                    note TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )

    def purge_expired(self) -> int:
        now = _utc_now_iso()
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM lookups WHERE expires_at <= ?", (now,))
            return cur.rowcount

    def save_lookup(self, lookup: Dict, retention_days: int = 30) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO lookups (
                    raw_phone, normalized_phone, country_code, country_name,
                    line_type_guess, risk_score, created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    lookup["raw_phone"],
                    lookup["normalized_phone"],
                    lookup["country"]["code"],
                    lookup["country"]["name"],
                    lookup["line_type_guess"],
                    lookup["risk_score"],
                    lookup["created_at"],
                    _expiry_iso(retention_days),
                ),
            )
            return cur.lastrowid

    def add_report(self, normalized_phone: str, category: str, note: Optional[str] = None) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO reports (normalized_phone, category, note, created_at) VALUES (?, ?, ?, ?)",
                (normalized_phone, category, note or "", _utc_now_iso()),
            )
            return cur.lastrowid

    def get_report_counts(self, normalized_phone: str) -> Dict[str, int]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT category, COUNT(*) AS count
                FROM reports
                WHERE normalized_phone = ?
                GROUP BY category
                """,
                (normalized_phone,),
            ).fetchall()

        counts = {"spam": 0, "scam": 0, "safe": 0, "other": 0}
        for row in rows:
            category = row["category"] if row["category"] in counts else "other"
            counts[category] += row["count"]
        return counts

    def get_history(self, normalized_phone: Optional[str] = None, limit: int = 50) -> List[Dict]:
        query = """
            SELECT id, raw_phone, normalized_phone, country_code, country_name,
                   line_type_guess, risk_score, created_at, expires_at
            FROM lookups
        """
        params = []
        if normalized_phone:
            query += " WHERE normalized_phone = ?"
            params.append(normalized_phone)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(max(1, min(limit, 500)))

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()

        return [dict(row) for row in rows]
