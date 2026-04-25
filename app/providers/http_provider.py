import json
from datetime import datetime, timezone
from typing import Dict
from urllib import error, request

from app.providers.base import PEPProvider


class HTTPPEPProvider(PEPProvider):
    """Provider adapter for authorized external PEP screening APIs."""

    def __init__(self, endpoint: str, token: str, timeout_seconds: int = 12):
        self.endpoint = endpoint
        self.token = token
        self.timeout_seconds = timeout_seconds

    def screen(self, subject: Dict) -> Dict:
        payload = json.dumps({"subject": subject}).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
        }
        req = request.Request(self.endpoint, data=payload, headers=headers, method="POST")

        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
                data = json.loads(body) if body else {}
        except error.HTTPError as exc:
            raise ValueError(f"PEP provider HTTP error: {exc.code}") from exc
        except error.URLError as exc:
            raise ValueError("PEP provider unreachable") from exc
        except json.JSONDecodeError as exc:
            raise ValueError("PEP provider returned invalid JSON") from exc

        matches = data.get("matches", []) if isinstance(data.get("matches"), list) else []
        return {
            "provider": "http",
            "provider_request_id": data.get("provider_request_id") or data.get("request_id") or "",
            "scanned_at": data.get("scanned_at") or datetime.now(timezone.utc).isoformat(),
            "subject": subject,
            "match_count": data.get("match_count", len(matches)),
            "matches": matches,
            "risk_level": data.get("risk_level", "medium" if matches else "low"),
            "disclaimer": data.get("disclaimer", "Response relayed from configured authorized provider."),
        }
