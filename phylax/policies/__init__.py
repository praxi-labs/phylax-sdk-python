from typing import Any, Dict, List, Optional
from urllib.parse import quote

from phylax.core.api import API


class Policies:
    def __init__(self, api: API) -> None:
        self.api = api

    def list(self) -> Dict[str, Any]:
        return self.api.get("/v1/policies")

    def get(self, policy_id: str) -> Dict[str, Any]:
        return self.api.get(f"/v1/policies/{quote(policy_id, safe='')}")

    def create(self, policy: Dict[str, Any]) -> Dict[str, Any]:
        return self.api.post("/v1/policies", json=policy)

    def update(self, policy_id: str, policy: Dict[str, Any]) -> Dict[str, Any]:
        return self.api.patch(f"/v1/policies/{quote(policy_id, safe='')}", json=policy)

    def delete(self, policy_id: str) -> None:
        return self.api.delete(f"/v1/policies/{quote(policy_id, safe='')}")

    def evaluate(
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
        return self.api.post("/v1/policies/evaluate", json=body)
