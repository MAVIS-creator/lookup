import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from app.config import HOST, PORT, WEB_DIR, DB_PATH
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
        parsed = urlparse(self.path)

        if parsed.path == "/api/health":
            _json_response(self, HTTPStatus.OK, {"status": "ok"})
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

        self._serve_static(parsed.path)

    def do_POST(self):
        parsed = urlparse(self.path)
        try:
            payload = self._read_json_body()
        except json.JSONDecodeError:
            _json_response(self, HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON body"})
            return

        if parsed.path == "/api/lookup":
            phone = payload.get("phone", "")
            try:
                result = self.service.lookup_phone(phone)
            except ValueError as exc:
                _json_response(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
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
