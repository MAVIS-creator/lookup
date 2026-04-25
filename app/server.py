import json
import mimetypes
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from app.config import (
    HOST,
    PORT,
    WEB_DIR,
    DB_PATH,
    API_KEY,
    API_KEY_HEADER,
    REQUIRE_API_KEY,
    RATE_LIMIT_PER_MINUTE,
    RETENTION_TIERS,
)
from app.phone_utils import normalize_phone
from app.service import LookupService
from app.storage import Storage


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(body)


class AppHandler(BaseHTTPRequestHandler):
    storage = Storage(str(DB_PATH))
    service = LookupService(storage)
    _request_log = {}

    def _client_token(self) -> str:
        key = self.headers.get(API_KEY_HEADER, "").strip()
        if key:
            return f"key:{key}"
        return f"ip:{self.client_address[0]}"

    def _authorize(self):
        if not REQUIRE_API_KEY:
            return True
        supplied = self.headers.get(API_KEY_HEADER, "").strip()
        return supplied == API_KEY

    def _rate_limited(self) -> bool:
        token = self._client_token()
        now = time.time()
        window_start = now - 60
        bucket = self._request_log.get(token, [])
        bucket = [ts for ts in bucket if ts >= window_start]
        if len(bucket) >= RATE_LIMIT_PER_MINUTE:
            self._request_log[token] = bucket
            return True
        bucket.append(now)
        self._request_log[token] = bucket
        return False

    def _guard_api_request(self):
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/api/") or parsed.path == "/api/health":
            return True

        if not self._authorize():
            _json_response(self, HTTPStatus.UNAUTHORIZED, {"error": "Unauthorized API key"})
            return False

        if self._rate_limited():
            _json_response(self, HTTPStatus.TOO_MANY_REQUESTS, {"error": "Rate limit exceeded"})
            return False

        return True

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def _serve_static(self, path: str):
        target = "index.html" if path == "/" else path.lstrip("/")
        full_path = (WEB_DIR / target).resolve()
        if not str(full_path).startswith(str(Path(WEB_DIR).resolve())):
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        if not full_path.exists() or not full_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        content_type, _ = mimetypes.guess_type(str(full_path))
        content_type = content_type or "application/octet-stream"
        data = full_path.read_bytes()

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if not self._guard_api_request():
            return

        parsed = urlparse(self.path)

        if parsed.path == "/api/health":
            _json_response(
                self,
                HTTPStatus.OK,
                {
                    "status": "ok",
                    "service": "Phone Intelligence Platform",
                    "api_key_required": REQUIRE_API_KEY,
                },
            )
            return

        if parsed.path == "/api/policies":
            _json_response(
                self,
                HTTPStatus.OK,
                {
                    "retention_tiers": RETENTION_TIERS,
                    "rate_limit_per_minute": RATE_LIMIT_PER_MINUTE,
                    "api_key_header": API_KEY_HEADER,
                },
            )
            return

        if parsed.path == "/api/history":
            query = parse_qs(parsed.query)
            phone = query.get("phone", [None])[0]
            limit_raw = query.get("limit", ["50"])[0]
            try:
                limit = int(limit_raw)
            except ValueError:
                limit = 50

            normalized_phone = None
            if phone:
                try:
                    normalized_phone = normalize_phone(phone)
                except ValueError as exc:
                    _json_response(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                    return

            history = self.storage.get_history(normalized_phone=normalized_phone, limit=limit)
            _json_response(self, HTTPStatus.OK, {"items": history})
            return

        if parsed.path == "/api/audit":
            query = parse_qs(parsed.query)
            limit_raw = query.get("limit", ["50"])[0]
            try:
                limit = int(limit_raw)
            except ValueError:
                limit = 50
            events = self.storage.get_audit_events(limit)
            _json_response(self, HTTPStatus.OK, {"items": events})
            return

        self._serve_static(parsed.path)

    def do_POST(self):
        if not self._guard_api_request():
            return

        parsed = urlparse(self.path)
        try:
            payload = self._read_json_body()
        except json.JSONDecodeError:
            _json_response(self, HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON body"})
            return

        if parsed.path == "/api/lookup":
            phone = payload.get("phone", "")
            retention_tier = payload.get("retention_tier", "standard")
            try:
                result = self.service.lookup_phone(phone, retention_tier=retention_tier)
            except ValueError as exc:
                _json_response(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
            event = self.storage.append_audit_event(
                action="lookup",
                subject=result["normalized_phone"],
                actor=self._client_token(),
                details={
                    "lookup_id": result["lookup_id"],
                    "retention_tier": result["compliance_flags"]["retention_tier"],
                    "risk_score": result["risk_score"],
                },
            )
            result["audit_event"] = {
                "id": event["id"],
                "event_hash": event["event_hash"],
            }
            _json_response(self, HTTPStatus.OK, result)
            return

        if parsed.path == "/api/report":
            phone = payload.get("phone", "")
            category = payload.get("category", "other")
            note = payload.get("note", "")
            try:
                result = self.service.add_report(phone, category, note)
            except ValueError as exc:
                _json_response(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
            event = self.storage.append_audit_event(
                action="report",
                subject=result["normalized_phone"],
                actor=self._client_token(),
                details={"category": category, "report_id": result["report_id"]},
            )
            result["audit_event"] = {
                "id": event["id"],
                "event_hash": event["event_hash"],
            }
            _json_response(self, HTTPStatus.OK, result)
            return

        _json_response(self, HTTPStatus.NOT_FOUND, {"error": "Endpoint not found"})

    def log_message(self, format, *args):
        return


def run_server(host: str = HOST, port: int = PORT):
    purged = AppHandler.storage.purge_expired()
    server = ThreadingHTTPServer((host, port), AppHandler)
    print(f"Server running on http://{host}:{port}")
    print(f"Purged expired lookup records: {purged}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
