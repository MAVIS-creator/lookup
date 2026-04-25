from datetime import datetime, timezone
from typing import Dict

from app.config import RETENTION_TIERS
from app.phone_utils import infer_country, infer_line_type, normalize_phone
from app.storage import Storage


class LookupService:
    def __init__(self, storage: Storage):
        self.storage = storage

    def _compute_risk_score(self, line_type_guess: str, report_counts: Dict[str, int]) -> int:
        score = 5
        if line_type_guess == "short_or_special":
            score += 10
        score += (report_counts.get("spam", 0) * 12)
        score += (report_counts.get("scam", 0) * 20)
        score -= (report_counts.get("safe", 0) * 4)
        return max(0, min(score, 100))

    def _risk_profile(self, risk_score: int) -> str:
        if risk_score >= 60:
            return "HIGH"
        if risk_score >= 25:
            return "MEDIUM"
        return "LOW"

    def _source_attribution(self, normalized_phone: str, country_code: str) -> Dict:
        return {
            "telecom_registry": {
                "type": "carrier_metadata",
                "status": "available",
                "country": country_code,
                "attribution": "Local heuristic source model",
            },
            "business_intelligence": {
                "type": "public_business_profile",
                "status": "placeholder",
                "country": country_code,
                "attribution": "Connector ready for authorized registry APIs",
            },
            "risk_signals": {
                "type": "community_reports",
                "status": "available",
                "country": "GLOBAL",
                "attribution": "Local report aggregation",
            },
            "query_scope": {
                "normalized_phone": normalized_phone,
                "privacy_mode": "PII-minimized",
            },
        }

    def lookup_phone(self, raw_phone: str, retention_tier: str = "standard") -> Dict:
        normalized_phone = normalize_phone(raw_phone)
        country = infer_country(normalized_phone)
        line_type_guess = infer_line_type(normalized_phone)
        report_counts = self.storage.get_report_counts(normalized_phone)
        if retention_tier not in RETENTION_TIERS:
            raise ValueError("Invalid retention tier")

        result = {
            "raw_phone": raw_phone,
            "normalized_phone": normalized_phone,
            "country": country,
            "line_type_guess": line_type_guess,
            "report_counts": report_counts,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        result["risk_score"] = self._compute_risk_score(line_type_guess, report_counts)
        result["risk_profile"] = self._risk_profile(result["risk_score"])

        source_summary = self._source_attribution(normalized_phone, country["code"])
        compliance_flags = {
            "consent_required": True,
            "pii_stored": False,
            "retention_tier": retention_tier,
            "retention_days": RETENTION_TIERS[retention_tier],
            "source_attribution": True,
        }

        lookup_id = self.storage.save_lookup(
            result,
            retention_days=RETENTION_TIERS[retention_tier],
            retention_tier=retention_tier,
            source_summary=source_summary,
            compliance_flags=compliance_flags,
        )
        result["lookup_id"] = lookup_id
        result["source_summary"] = source_summary
        result["compliance_flags"] = compliance_flags
        return result

    def add_report(self, raw_phone: str, category: str, note: str = "") -> Dict:
        normalized_phone = normalize_phone(raw_phone)
        if category not in {"spam", "scam", "safe", "other"}:
            raise ValueError("Invalid category")

        report_id = self.storage.add_report(normalized_phone, category, note)
        counts = self.storage.get_report_counts(normalized_phone)
        return {
            "report_id": report_id,
            "normalized_phone": normalized_phone,
            "report_counts": counts,
        }
