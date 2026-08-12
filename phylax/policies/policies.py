import builtins
from typing import Any
from urllib.parse import quote

from phylax.core.api import API


class Policies:
    def __init__(self, api: API) -> None:
        self.api = api

    def list(self) -> dict[str, Any]:
        return self.api.get("/v1/policies")

    def get(self, policy_id: str) -> dict[str, Any]:
        return self.api.get(f"/v1/policies/{quote(policy_id, safe='')}")

    def create(self, policy: dict[str, Any]) -> dict[str, Any]:
        return self.api.post("/v1/policies", json=policy)

    def update(self, policy_id: str, policy: dict[str, Any]) -> dict[str, Any]:
        return self.api.patch(f"/v1/policies/{quote(policy_id, safe='')}", json=policy)

    def delete(self, policy_id: str) -> None:
        return self.api.delete(f"/v1/policies/{quote(policy_id, safe='')}")

    def evaluate(
        self,
        artifact: str,
        policy: str | None = None,
        include: builtins.list[str] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"artifact": artifact}
        if policy:
            body["policy"] = policy
        if include:
            body["include"] = include
        return self.api.post("/v1/policies/evaluate", json=body)
