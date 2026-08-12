from typing import Any, Dict, Optional
from urllib.parse import quote

from phylax.core.api import API


class Repositories:
    def __init__(self, api: API) -> None:
        self.api = api

    def list(self) -> Dict[str, Any]:
        return self.api.get("/v1/repositories")

    def get(self, repository_id: str) -> Dict[str, Any]:
        return self.api.get(f"/v1/repositories/{quote(repository_id, safe='')}")

    def add(
        self,
        url: str,
        provider: Optional[str] = None,
        policy: Optional[str] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {"url": url}
        if provider:
            body["provider"] = provider
        if policy:
            body["policy"] = policy
        return self.api.post("/v1/repositories", json=body)

    def remove(self, repository_id: str) -> None:
        return self.api.delete(f"/v1/repositories/{quote(repository_id, safe='')}")

    def verify(self, url: str) -> Dict[str, Any]:
        return self.api.post("/v1/repositories/verify", json={"url": url})
