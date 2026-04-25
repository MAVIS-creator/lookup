import sqlite3
import hashlib
import json
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
            self._ensure_lookup_columns(conn)
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
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    details_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    prev_hash TEXT,
                    event_hash TEXT NOT NULL
                )
                """
            )

    def _ensure_lookup_columns(self, conn):
        rows = conn.execute("PRAGMA table_info(lookups)").fetchall()
        existing = {row[1] for row in rows}

        additions = [
            ("retention_tier", "TEXT NOT NULL DEFAULT 'standard'"),
            ("source_summary", "TEXT NOT NULL DEFAULT '{}'"),
            ("compliance_flags", "TEXT NOT NULL DEFAULT '{}'"),
        ]
        for name, ddl in additions:
            if name not in existing:
                conn.execute(f"ALTER TABLE lookups ADD COLUMN {name} {ddl}")

    def purge_expired(self) -> int:
        now = _utc_now_iso()
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM lookups WHERE expires_at <= ?", (now,))
            return cur.rowcount

    def save_lookup(
        self,
        lookup: Dict,
        retention_days: int,
        retention_tier: str,
        source_summary: Dict,
        compliance_flags: Dict,
    ) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO lookups (
                    raw_phone, normalized_phone, country_code, country_name,
                    line_type_guess, risk_score, created_at, expires_at,
                    retention_tier, source_summary, compliance_flags
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    retention_tier,
                    json.dumps(source_summary, ensure_ascii=False),
                    json.dumps(compliance_flags, ensure_ascii=False),
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
                   line_type_guess, risk_score, created_at, expires_at,
                   retention_tier, source_summary, compliance_flags
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

        output = []
        for row in rows:
            item = dict(row)
            item["source_summary"] = json.loads(item.get("source_summary") or "{}")
            item["compliance_flags"] = json.loads(item.get("compliance_flags") or "{}")
            output.append(item)
        return output

    def _latest_audit_hash(self) -> Optional[str]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT event_hash FROM audit_events ORDER BY id DESC LIMIT 1"
            ).fetchone()
        return row["event_hash"] if row else None

    def append_audit_event(self, action: str, subject: str, actor: str, details: Dict) -> Dict:
        created_at = _utc_now_iso()
        prev_hash = self._latest_audit_hash()
        details_json = json.dumps(details, sort_keys=True, ensure_ascii=False)
        payload = f"{action}|{subject}|{actor}|{details_json}|{created_at}|{prev_hash or ''}"
        event_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO audit_events (
                    action, subject, actor, details_json, created_at, prev_hash, event_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (action, subject, actor, details_json, created_at, prev_hash, event_hash),
            )
            event_id = cur.lastrowid

        return {
            "id": event_id,
            "action": action,
            "subject": subject,
            "actor": actor,
            "created_at": created_at,
            "prev_hash": prev_hash,
            "event_hash": event_hash,
        }

    def get_audit_events(self, limit: int = 50) -> List[Dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, action, subject, actor, details_json, created_at, prev_hash, event_hash
                FROM audit_events
                ORDER BY id DESC
                LIMIT ?
                """,
                (max(1, min(limit, 500)),),
            ).fetchall()

        events = []
        for row in rows:
            event = dict(row)
            event["details"] = json.loads(event.pop("details_json") or "{}")
            events.append(event)
        return events
