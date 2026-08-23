import os
from typing import Any

import requests

from phylax.artifacts import Artifacts
from phylax.attestations import Attestations
from phylax.core.api import API, DEFAULT_BASE_URL, DEFAULT_MAX_RETRIES, DEFAULT_TIMEOUT
from phylax.exceptions import (
    APIAccessDenied,
    APIAuthenticationError,
    APIConnectionError,
    APIFailure,
    APIInvalidRequest,
    APIPlanRequired,
    APIQuotaExceeded,
    APIRateLimited,
    APIResourceNotFound,
    APIServerError,
    APITimeout,
    APITokenMissing,
    PhylaxError,
)
from phylax.policies import Policies
from phylax.quota import Quota
from phylax.repositories import Repositories
from phylax.utils.collect import collect_files
from phylax.utils.signature import SignatureResult, verify_signature
from phylax.version import __version__
from phylax.webhooks import Webhooks

__all__ = [
    "APIAccessDenied",
    "APIAuthenticationError",
    "APIConnectionError",
    "APIFailure",
    "APIInvalidRequest",
    "APIPlanRequired",
    "APIQuotaExceeded",
    "APIRateLimited",
    "APIResourceNotFound",
    "APIServerError",
    "APITimeout",
    "APITokenMissing",
    "Phylax",
    "PhylaxError",
    "SignatureResult",
    "__version__",
    "collect_files",
    "verify_signature",
]


class Phylax:
    def __init__(
        self,
        api_token: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        user_agent: str | None = None,
        session: requests.Session | None = None,
    ) -> None:
        token = api_token or os.getenv("PHYLAX_API_TOKEN") or os.getenv("PHYLAX_API_KEY")
        if not token or not token.strip():
            raise APITokenMissing()

        self.api = API(
            api_token=token.strip(),
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            user_agent=user_agent,
            session=session,
        )

        self.artifacts = Artifacts(self.api)
        self.attestations = Attestations(self.api)
        self.policies = Policies(self.api)
        self.repositories = Repositories(self.api)
        self.webhooks = Webhooks(self.api)
        self.quota = Quota(self.api)

    def health(self) -> dict[str, Any]:
        return self.api.get("/v1/health")

    def server_identity(self) -> dict[str, Any]:
        return self.api.get("/v1/server-identity")

    def me(self) -> dict[str, Any]:
        return self.api.get("/v1/account/me")
