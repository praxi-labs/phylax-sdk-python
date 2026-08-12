from typing import Any
from urllib.parse import quote

from phylax.core.api import API


class Repositories:
    def __init__(self, api: API) -> None:
        self.api = api

    def list(self) -> dict[str, Any]:
        return self.api.get("/v1/repositories")

    def get(self, repository_id: str) -> dict[str, Any]:
        return self.api.get(f"/v1/repositories/{quote(repository_id, safe='')}")

    def add(
        self,
        url: str,
        provider: str | None = None,
        policy: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"url": url}
        if provider:
            body["provider"] = provider
        if policy:
            body["policy"] = policy
        return self.api.post("/v1/repositories", json=body)

    def remove(self, repository_id: str) -> None:
        return self.api.delete(f"/v1/repositories/{quote(repository_id, safe='')}")

    def verify(
        self,
        files: dict[str, str],
        url: str | None = None,
        policy: str | None = None,
    ) -> dict[str, Any]:
        """Scan a repository by verifying every dependency its lockfiles install.

        Pass the lockfile contents keyed by filename. Nothing about the
        repository is fetched, so scanning a private repository never requires
        giving Phylax a token for it.
        """
        body: dict[str, Any] = {"files": files}
        if url:
            body["url"] = url
        if policy:
            body["policy"] = policy
        return self.api.post("/v1/repositories/verify", json=body)
