from datetime import datetime, timezone
from typing import Dict

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

    def lookup_phone(self, raw_phone: str) -> Dict:
        normalized_phone = normalize_phone(raw_phone)
        country = infer_country(normalized_phone)
        line_type_guess = infer_line_type(normalized_phone)
        report_counts = self.storage.get_report_counts(normalized_phone)

        result = {
            "raw_phone": raw_phone,
            "normalized_phone": normalized_phone,
            "country": country,
            "line_type_guess": line_type_guess,
            "report_counts": report_counts,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        result["risk_score"] = self._compute_risk_score(line_type_guess, report_counts)

        lookup_id = self.storage.save_lookup(result)
        result["lookup_id"] = lookup_id
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
