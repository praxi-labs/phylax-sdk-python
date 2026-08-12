from typing import Any, Dict, List, Optional
from urllib.parse import quote

from phylax.core.api import API


class Artifacts:
    def __init__(self, api: API) -> None:
        self.api = api

    def verify(
        self,
        artifact: str,
        policy: Optional[str] = None,
        include: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {"artifact": artifact}
        if policy:
            body["policy"] = policy
        if include:
            body["include"] = include
        return self.api.post("/v1/artifacts/verify", json=body)

    def verify_many(
        self,
        artifacts: List[str],
        policy: Optional[str] = None,
        include: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        body: Dict[str, Any] = {"artifacts": artifacts}
        if policy:
            body["policy"] = policy
        if include:
            body["include"] = include
        return self.api.post("/v1/artifacts/verify", json=body)

    def get(self, artifact: str) -> Dict[str, Any]:
        return self.api.get(f"/v1/artifacts/{quote(artifact, safe='')}")

    def list(
        self,
        ecosystem: Optional[str] = None,
        limit: Optional[int] = None,
        page: Optional[int] = None,
    ) -> Dict[str, Any]:
        return self.api.get(
            "/v1/artifacts",
            params={"ecosystem": ecosystem, "limit": limit, "page": page},
        )

    def search(
        self,
        query: str,
        ecosystem: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        return self.api.get(
            "/v1/search",
            params={"q": query, "ecosystem": ecosystem, "limit": limit},
        )
