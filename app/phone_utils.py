import re
from typing import Dict

COUNTRY_PREFIXES = {
    "+234": {"code": "NG", "name": "Nigeria"},
    "+1": {"code": "US/CA", "name": "United States / Canada"},
    "+44": {"code": "GB", "name": "United Kingdom"},
    "+233": {"code": "GH", "name": "Ghana"},
    "+254": {"code": "KE", "name": "Kenya"},
    "+27": {"code": "ZA", "name": "South Africa"},
    "+91": {"code": "IN", "name": "India"},
}


def normalize_phone(phone: str) -> str:
    """Normalize common phone inputs into a conservative E.164-like format."""
    if not isinstance(phone, str):
        raise ValueError("Phone must be a string")

    value = phone.strip()
    if not value:
        raise ValueError("Phone is required")

    value = re.sub(r"[\s\-().]", "", value)
    if value.startswith("00"):
        value = "+" + value[2:]

    if value.startswith("+"):
        digits = value[1:]
    else:
        digits = value
        value = "+" + digits

    if not digits.isdigit():
        raise ValueError("Phone contains invalid characters")

    if len(digits) < 7 or len(digits) > 15:
        raise ValueError("Phone length is invalid")

    return value


def infer_country(normalized_phone: str) -> Dict[str, str]:
    """Infer country metadata by longest matching international prefix."""
    for prefix in sorted(COUNTRY_PREFIXES.keys(), key=len, reverse=True):
        if normalized_phone.startswith(prefix):
            return COUNTRY_PREFIXES[prefix]
    return {"code": "UNK", "name": "Unknown"}


def infer_line_type(normalized_phone: str) -> str:
    """Heuristic line type classification for simple risk scoring."""
    digit_count = len(normalized_phone.replace("+", ""))
    if digit_count <= 9:
        return "short_or_special"
    if digit_count in (10, 11):
        return "mobile_or_fixed"
    return "unknown"
