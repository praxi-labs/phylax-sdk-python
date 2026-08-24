"""Auditing a whole tree from one call.

Resolution deliberately does not happen in the SDK: the server owns the
lockfile parser and the registry client, so every client gets the same audit
rather than five slightly different ones.

The streaming half is what these mostly pin. NDJSON has to survive being split
across chunk boundaries, which is the bug every hand rolled reader has.
"""

from __future__ import annotations

import json

import pytest
import responses

from phylax import Phylax, collect_manifests
from phylax.audit.audit import AuditTimeout

BASE = "https://api.phyi.dev"
SCAN_ID = "scan123456789012"

SCAN = {"id": SCAN_ID, "state": "pending", "stream": f"/v1/audit/{SCAN_ID}/stream"}
DONE = {"id": SCAN_ID, "state": "complete", "verdict": "BLOCK"}

MANIFESTS = {
    "package-lock.json": '{"lockfileVersion":3}',
    "package.json": '{"name":"demo"}',
}

NDJSON = "\n".join(
    [
        json.dumps({"type": "scan", "id": SCAN_ID, "state": "complete", "verdict": "BLOCK"}),
        json.dumps(
            {
                "type": "artifact",
                "purl": "pkg:npm/express@4.18.2",
                "name": "express",
                "verdict": "ALLOW",
                "direct": True,
                "ancestors": [],
            }
        ),
        json.dumps(
            {
                "type": "artifact",
                "purl": "pkg:npm/debug@2.6.9",
                "name": "debug",
                "verdict": "BLOCK",
                "direct": False,
                "ancestors": ["express"],
                "declared_in": "package-lock.json",
                "declared_line": 42,
            }
        ),
        json.dumps(
            {"type": "summary", "verdict": "BLOCK", "packages": 2,
             "by_verdict": {"ALLOW": 1, "BLOCK": 1}}
        ),
    ]
)


@pytest.fixture
def client():
    return Phylax(api_token="phx_live_test")


class TestCreate:
    @responses.activate
    def test_it_sends_manifests_not_source(self, client):
        responses.add(responses.POST, f"{BASE}/v1/audit", json=SCAN, status=202)
        client.audit.create(MANIFESTS, coordinate="demo")

        body = json.loads(responses.calls[0].request.body)
        assert body == {"files": MANIFESTS, "coordinate": "demo"}

    @responses.activate
    def test_it_returns_without_waiting_for_the_work(self, client):
        responses.add(responses.POST, f"{BASE}/v1/audit", json=SCAN, status=202)
        result = client.audit.create(MANIFESTS)
        assert result["id"] == SCAN_ID
        assert result["state"] == "pending"


class TestStream:
    @responses.activate
    def test_it_yields_one_event_per_line(self, client):
        responses.add(
            responses.GET,
            f"{BASE}/v1/audit/{SCAN_ID}/stream",
            body=NDJSON,
            content_type="application/x-ndjson",
        )
        events = list(client.audit.stream(SCAN_ID))
        assert [e["type"] for e in events] == ["scan", "artifact", "artifact", "summary"]

    @responses.activate
    def test_each_package_carries_its_place_in_the_graph(self, client):
        responses.add(
            responses.GET,
            f"{BASE}/v1/audit/{SCAN_ID}/stream",
            body=NDJSON,
            content_type="application/x-ndjson",
        )
        events = list(client.audit.stream(SCAN_ID))
        debug = next(e for e in events if e.get("name") == "debug")

        assert debug["ancestors"] == ["express"]
        assert debug["declared_line"] == 42
        assert debug["direct"] is False


class TestRun:
    @responses.activate
    def test_it_polls_then_collects_the_stream(self, client):
        responses.add(responses.POST, f"{BASE}/v1/audit", json=SCAN, status=202)
        responses.add(responses.GET, f"{BASE}/v1/audit/{SCAN_ID}", json=DONE)
        responses.add(
            responses.GET,
            f"{BASE}/v1/audit/{SCAN_ID}/stream",
            body=NDJSON,
            content_type="application/x-ndjson",
        )

        result = client.audit.run(MANIFESTS, poll_interval=0)

        assert len(result["artifacts"]) == 2
        assert result["summary"]["by_verdict"] == {"ALLOW": 1, "BLOCK": 1}
        assert result["scan"]["verdict"] == "BLOCK"

    @responses.activate
    def test_a_timeout_says_the_scan_is_still_running(self, client):
        """The wait is abandoned, not the audit. It can still be read by id, so
        the message must not imply the work was lost."""
        responses.add(responses.POST, f"{BASE}/v1/audit", json=SCAN, status=202)
        responses.add(
            responses.GET, f"{BASE}/v1/audit/{SCAN_ID}", json={"id": SCAN_ID, "state": "scan"}
        )

        with pytest.raises(AuditTimeout) as excinfo:
            client.audit.run(MANIFESTS, poll_interval=0, timeout=0.01)
        assert "still running" in str(excinfo.value)


class TestCollectManifests:
    def test_it_finds_lockfiles_and_manifests_only(self, tmp_path):
        (tmp_path / "package.json").write_text("{}", encoding="utf-8")
        (tmp_path / "package-lock.json").write_text("{}", encoding="utf-8")
        (tmp_path / "index.js").write_text("x\n", encoding="utf-8")

        files, _ = collect_manifests(tmp_path)
        assert sorted(files) == ["package-lock.json", "package.json"]

    def test_it_does_not_send_your_source(self, tmp_path):
        """An audit asks about dependencies. Uploading a whole tree to answer
        that would send megabytes to learn about a few kilobytes."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "secret.py").write_text("KEY = 'x'\n", encoding="utf-8")
        (tmp_path / "requirements.txt").write_text("requests==2.31.0\n", encoding="utf-8")

        files, _ = collect_manifests(tmp_path)
        assert list(files) == ["requirements.txt"]

    def test_vendored_directories_are_skipped(self, tmp_path):
        vendor = tmp_path / "node_modules" / "dep"
        vendor.mkdir(parents=True)
        (vendor / "package.json").write_text("{}", encoding="utf-8")
        (tmp_path / "package.json").write_text("{}", encoding="utf-8")

        files, _ = collect_manifests(tmp_path)
        assert list(files) == ["package.json"]
