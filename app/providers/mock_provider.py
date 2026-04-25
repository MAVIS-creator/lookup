from datetime import datetime, timezone
from typing import Dict, List

from app.providers.base import PEPProvider


class MockPEPProvider(PEPProvider):
    """Deterministic provider for local testing when no external vendor is configured."""

    def _matches_for(self, full_name: str, country_code: str) -> List[Dict]:
        key = (full_name or "").strip().lower()
        if not key:
            return []

        demo_match_names = {"john okafor", "jane doe", "ibrahim musa"}
        if key in demo_match_names:
            return [
                {
                    "name": full_name,
                    "country": country_code or "UNK",
                    "role": "Politically Exposed Person",
                    "source": "Mock Watchlist",
                    "match_confidence": 0.82,
                }
            ]
        return []

    def screen(self, subject: Dict) -> Dict:
        full_name = subject.get("full_name", "")
        country_code = subject.get("country_code", "")
        matches = self._matches_for(full_name, country_code)

        return {
            "provider": "mock",
            "provider_request_id": f"mock-{int(datetime.now(timezone.utc).timestamp())}",
            "scanned_at": datetime.now(timezone.utc).isoformat(),
            "subject": subject,
            "match_count": len(matches),
            "matches": matches,
            "risk_level": "high" if matches else "low",
            "disclaimer": "Mock provider data for development only.",
        }
