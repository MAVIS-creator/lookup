from app.config import (
    PEP_PROVIDER_MODE,
    PEP_PROVIDER_ENDPOINT,
    PEP_PROVIDER_TOKEN,
    PEP_PROVIDER_TIMEOUT_SECONDS,
)
from app.providers.http_provider import HTTPPEPProvider
from app.providers.mock_provider import MockPEPProvider


def get_pep_provider():
    if PEP_PROVIDER_MODE == "http":
        if not PEP_PROVIDER_ENDPOINT or not PEP_PROVIDER_TOKEN:
            raise ValueError(
                "PEP provider mode is http but endpoint/token is missing in environment configuration"
            )
        return HTTPPEPProvider(
            endpoint=PEP_PROVIDER_ENDPOINT,
            token=PEP_PROVIDER_TOKEN,
            timeout_seconds=PEP_PROVIDER_TIMEOUT_SECONDS,
        )

    return MockPEPProvider()
