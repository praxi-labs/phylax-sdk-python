from typing import Any
from urllib.parse import quote

from phylax.core.api import API


class Artifacts:
    def __init__(self, api: API) -> None:
        self.api = api

    def verify(
        self,
        artifact: str,
        policy: str | None = None,
        include: list[str] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"artifact": artifact}
        if policy:
            body["policy"] = policy
        if include:
            body["include"] = include
        return self.api.post("/v1/artifacts/verify", json=body)

    def verify_many(
        self,
        artifacts: list[str],
        policy: str | None = None,
        include: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        body: dict[str, Any] = {"artifacts": artifacts}
        if policy:
            body["policy"] = policy
        if include:
            body["include"] = include
        return self.api.post("/v1/artifacts/verify", json=body)

    def get(self, artifact: str) -> dict[str, Any]:
        return self.api.get(f"/v1/artifacts/{quote(artifact, safe='')}")

    def list(
        self,
        ecosystem: str | None = None,
        limit: int | None = None,
        page: int | None = None,
    ) -> dict[str, Any]:
        return self.api.get(
            "/v1/artifacts",
            params={"ecosystem": ecosystem, "limit": limit, "page": page},
        )

    def search(
        self,
        query: str,
        ecosystem: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        return self.api.get(
            "/v1/search",
            params={"q": query, "ecosystem": ecosystem, "limit": limit},
        )
