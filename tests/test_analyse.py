"""Analysing supplied bytes, rather than looking up a name.

`verify` answers from what the network has already recorded, so an artifact
nobody has attested returns coverage "none" and a verdict of ALLOW. Safe for a
catalogue, wrong for a gate. These pin the distinction, and that a caller can
tell a champion-backed verdict from a regex pass.
"""

from __future__ import annotations

import json

import pytest
import responses

from phylax import Phylax, collect_files

BASE = "https://api.phyi.dev"

CHAMPION = {
    "artifact": "demo",
    "artifact_type": "package",
    "verdict": "BLOCK",
    "confidence": 0.9,
    "coverage": "champion",
    "engine": {"version": "abc123", "analysers": 3, "dissent": True},
    "identity": "sha256:" + "a" * 64,
    "findings": [
        {"signal": "shell_execution", "severity": "medium", "file": "src/index.ts"}
    ],
    "reasons": ["shell_execution in src/index.ts: spawns a shell"],
}

FILES = {"package.json": '{"name":"demo"}', "src/index.ts": "export const x = 1\n"}


@pytest.fixture
def client():
    return Phylax(api_token="phx_live_test")


class TestAnalyse:
    @responses.activate
    def test_it_posts_the_files_to_the_analyse_endpoint(self, client):
        responses.add(responses.POST, f"{BASE}/v1/artifacts/analyse", json=CHAMPION)

        client.artifacts.analyse(
            FILES, artifact_type="package", coordinate="npm:demo@1.0.0"
        )

        body = json.loads(responses.calls[0].request.body)
        assert body == {
            "files": FILES,
            "artifact_type": "package",
            "coordinate": "npm:demo@1.0.0",
        }

    @responses.activate
    def test_it_omits_a_type_or_coordinate_that_was_not_given(self, client):
        responses.add(responses.POST, f"{BASE}/v1/artifacts/analyse", json=CHAMPION)
        client.artifacts.analyse(FILES)
        assert json.loads(responses.calls[0].request.body) == {"files": FILES}

    @responses.activate
    def test_it_surfaces_the_champion_verdict_and_engine_detail(self, client):
        responses.add(responses.POST, f"{BASE}/v1/artifacts/analyse", json=CHAMPION)

        result = client.artifacts.analyse(FILES)
        assert result["verdict"] == "BLOCK"
        assert result["coverage"] == "champion"
        assert result["engine"]["analysers"] == 3
        assert result["engine"]["dissent"] is True
        assert result["identity"].startswith("sha256:")

    @responses.activate
    def test_a_caller_can_tell_a_champion_run_from_a_static_pass(self, client):
        """A WARN from three champions and a WARN from a regex pass are
        identical if you only read the verdict. Coverage is how they differ."""
        responses.add(
            responses.POST,
            f"{BASE}/v1/artifacts/analyse",
            json={
                **CHAMPION,
                "verdict": "WARN",
                "coverage": "static",
                "engine": {"version": "none", "analysers": 0, "dissent": False},
            },
        )
        result = client.artifacts.analyse(FILES)
        assert result["coverage"] == "static"
        assert result["engine"]["analysers"] == 0


class TestTheGapAnalyseCloses:
    @responses.activate
    def test_verify_answers_about_a_name_and_may_have_no_coverage(self, client):
        responses.add(
            responses.POST,
            f"{BASE}/v1/artifacts/verify",
            json={
                "artifact": "npm:unseen",
                "verdict": "ALLOW",
                "coverage": "none",
                "reason": "This artifact has not been evaluated by the network.",
            },
        )
        result = client.artifacts.verify("pkg:npm/unseen@1.0.0")

        # ALLOW with no coverage is the fail-open default a gate must not trust.
        assert result["verdict"] == "ALLOW"
        assert result["coverage"] == "none"


class TestCollect:
    def test_source_is_collected_with_posix_paths(self, tmp_path):
        """The server keys findings by these paths, so a backslash on Windows
        would produce findings nobody can locate."""
        nested = tmp_path / "src" / "deep"
        nested.mkdir(parents=True)
        (nested / "a.ts").write_text("export const x = 1\n", encoding="utf-8")
        (tmp_path / "package.json").write_text("{}", encoding="utf-8")

        files, skipped = collect_files(tmp_path)
        assert "src/deep/a.ts" in files
        assert "package.json" in files
        assert skipped == []

    def test_vendored_directories_are_excluded(self, tmp_path):
        vendor = tmp_path / "node_modules"
        vendor.mkdir()
        (vendor / "dep.js").write_text("module.exports = 1\n", encoding="utf-8")
        (tmp_path / "index.js").write_text("require('dep')\n", encoding="utf-8")

        files, _ = collect_files(tmp_path)
        assert list(files) == ["index.js"]

    def test_binaries_are_left_out(self, tmp_path):
        (tmp_path / "logo.png").write_bytes(b"\x89PNG\r\n")
        (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
        files, _ = collect_files(tmp_path)
        assert list(files) == ["a.py"]

    def test_an_oversized_file_is_skipped_and_named(self, tmp_path):
        """Reported, never silent: a truncated artifact that presents itself as
        fully analysed is worse than one that says what it left out."""
        (tmp_path / "big.py").write_text("x" * (600 * 1024), encoding="utf-8")
        (tmp_path / "small.py").write_text("y = 1\n", encoding="utf-8")

        files, skipped = collect_files(tmp_path)
        assert "big.py" not in files
        assert any("big.py" in line for line in skipped)
