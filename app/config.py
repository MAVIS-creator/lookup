from pathlib import Path
import os

ROOT_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT_DIR / "web"
DB_PATH = ROOT_DIR / "phone_retention.db"
HOST = os.getenv("PHONE_INTEL_HOST", "127.0.0.1")
PORT = int(os.getenv("PHONE_INTEL_PORT", "8080"))

# Security and access
API_KEY = os.getenv("PHONE_INTEL_API_KEY", "change-me-enterprise-key")
API_KEY_HEADER = "x-api-key"
REQUIRE_API_KEY = os.getenv("PHONE_INTEL_REQUIRE_API_KEY", "true").lower() == "true"

# Request controls
RATE_LIMIT_PER_MINUTE = int(os.getenv("PHONE_INTEL_RATE_LIMIT_PER_MIN", "1000"))

# Compliance retention tiers in days
RETENTION_TIERS = {
	"standard": 90,
	"extended": 365,
}

# PEP provider integration
PEP_PROVIDER_MODE = os.getenv("PHONE_INTEL_PEP_PROVIDER", "mock").lower()
PEP_PROVIDER_ENDPOINT = os.getenv("PHONE_INTEL_PEP_ENDPOINT", "")
PEP_PROVIDER_TOKEN = os.getenv("PHONE_INTEL_PEP_TOKEN", "")
PEP_PROVIDER_TIMEOUT_SECONDS = int(os.getenv("PHONE_INTEL_PEP_TIMEOUT_SECONDS", "12"))
