from typing import Any, Dict, List, Optional
from urllib.parse import quote

from phylax.core.api import API


class Webhooks:
    def __init__(self, api: API) -> None:
        self.api = api

    def list(self) -> Dict[str, Any]:
        return self.api.get("/v1/webhooks")

    def get(self, webhook_id: str) -> Dict[str, Any]:
        return self.api.get(f"/v1/webhooks/{quote(webhook_id, safe='')}")

    def create(
        self,
        url: str,
        events: List[str],
        secret: Optional[str] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {"url": url, "events": events}
        if secret:
            body["secret"] = secret
        return self.api.post("/v1/webhooks", json=body)

    def update(self, webhook_id: str, **fields: Any) -> Dict[str, Any]:
        return self.api.patch(f"/v1/webhooks/{quote(webhook_id, safe='')}", json=fields)

    def delete(self, webhook_id: str) -> None:
        return self.api.delete(f"/v1/webhooks/{quote(webhook_id, safe='')}")
