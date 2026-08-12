from typing import Any
from urllib.parse import quote

from phylax.core.api import API


class Attestations:
    def __init__(self, api: API) -> None:
        self.api = api

    def list(
        self,
        artifact: str,
        limit: int | None = None,
        page: int | None = None,
    ) -> dict[str, Any]:
        return self.api.get(
            "/v1/attestations",
            params={"artifact": artifact, "limit": limit, "page": page},
        )

    def get(self, attestation_id: str) -> dict[str, Any]:
        return self.api.get(f"/v1/attestations/{quote(attestation_id, safe='')}")

    def verify(self, bundle: Any) -> dict[str, Any]:
        return self.api.post("/v1/attestations/verify", json=bundle)
