"""Auditing everything a project installs.

Send the manifests and lockfiles; the server resolves the transitive tree,
consults the index, fetches whatever is new from its registry and runs the
engine over it. Resolution deliberately does not happen here: a lockfile parser
and a registry client in every SDK is the same code written five times and
wrong in five different ways.
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from typing import Any

from phylax.core.api import API

TERMINAL = frozenset({"complete", "failed"})


class AuditTimeout(TimeoutError):
    """The wait was abandoned. The scan itself keeps running server side."""


class Audit:
    def __init__(self, api: API) -> None:
        self.api = api

    def create(
        self,
        files: dict[str, str],
        coordinate: str | None = None,
    ) -> dict[str, Any]:
        """Start an audit and return immediately with a scan id.

        The work is accepted, not finished: a tree of a few thousand packages
        takes minutes. Poll `get`, read `stream`, or call `run` to wait.
        """
        body: dict[str, Any] = {"files": files}
        if coordinate:
            body["coordinate"] = coordinate
        return self.api.post("/v1/audit", json=body)

    def get(self, scan_id: str) -> dict[str, Any]:
        """Where a scan has got to."""
        return self.api.get(f"/v1/audit/{scan_id}")

    def stream(self, scan_id: str, timeout: float | None = None) -> Iterator[dict]:
        """Every event, one at a time, as the server sends them.

        The first is the scan, then one per artifact, then a summary. Reading
        it this way lets a caller render a large tree progressively rather than
        holding all of it before showing anything.
        """
        for line in self.api.stream_lines(f"/v1/audit/{scan_id}/stream", timeout):
            try:
                yield json.loads(line)
            except ValueError:
                continue

    def run(
        self,
        files: dict[str, str],
        coordinate: str | None = None,
        poll_interval: float = 5.0,
        timeout: float = 900.0,
        on_progress=None,
    ) -> dict[str, Any]:
        """Start an audit and wait for it, collecting everything.

        The convenience path for a script or a CI job. A timeout here abandons
        the wait, not the scan: it keeps running and can still be read by id,
        so the error says so rather than implying the work was lost.
        """
        created = self.create(files, coordinate)
        scan_id = created["id"]
        deadline = time.monotonic() + timeout
        scan = created

        while str(scan.get("state")) not in TERMINAL:
            if time.monotonic() > deadline:
                raise AuditTimeout(
                    f"audit {scan_id} did not finish within {timeout}s. "
                    "It is still running; read it by id."
                )
            time.sleep(poll_interval)
            scan = self.get(scan_id)
            if on_progress:
                on_progress(scan)

        artifacts: list[dict] = []
        summary: dict | None = None
        for event in self.stream(scan_id):
            kind = event.get("type")
            if kind == "artifact":
                artifacts.append(event)
            elif kind == "summary":
                summary = event
            elif kind == "scan":
                scan = event

        return {"scan": scan, "artifacts": artifacts, "summary": summary}
