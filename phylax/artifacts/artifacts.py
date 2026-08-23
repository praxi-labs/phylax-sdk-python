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

    def analyse(
        self,
        files: dict[str, str],
        artifact_type: str | None = None,
        coordinate: str | None = None,
    ) -> dict[str, Any]:
        """Analyse an artifact you supply, rather than looking one up.

        `verify` and `get` answer from what the network has already recorded, so
        an artifact nobody has attested comes back with coverage "none" and a
        verdict of ALLOW. That default is safe for a catalogue and wrong for a
        gate: the artifact most worth judging is the one nobody has seen.

        This sends the source itself. The server classifies it, resolves the
        champions promoted for that track, runs them against these bytes in its
        sandbox, and fuses their opinions with a static pass.

        Read `coverage` on the result before acting on `verdict`. "champion"
        means the network's agents ran; "static" means only the signal scanner
        did, which is a much weaker claim and looks identical if you read the
        verdict alone.

        Args:
            files: Relative path to file contents. Text only.
            artifact_type: Hint the classifier. It decides for itself and flags
                a disagreement rather than taking this on trust.
            coordinate: A name for the artifact, echoed back on the result.
        """
        body: dict[str, Any] = {"files": files}
        if artifact_type:
            body["artifact_type"] = artifact_type
        if coordinate:
            body["coordinate"] = coordinate
        return self.api.post("/v1/artifacts/analyse", json=body)

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
