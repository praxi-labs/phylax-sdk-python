import json

import pytest
import requests

from phylax import (
    APIAccessDenied,
    APIAuthenticationError,
    APIPlanRequired,
    APIQuotaExceeded,
    APIRateLimited,
    APIResourceNotFound,
    APIServerError,
    APITokenMissing,
    Phylax,
)
from phylax.core.api import is_retryable, redact, retry_delay


class FakeResponse:
    def __init__(self, status=200, payload=None, headers=None, text=None):
        self.status_code = status
        self._payload = payload
        self.headers = headers or {}
        self.text = text if text is not None else json.dumps(payload or {})
        self.content = self.text.encode()

    @property
    def ok(self):
        return 200 <= self.status_code < 300

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, params=None, json=None, headers=None, timeout=None):
        self.calls.append(
            {"method": method, "url": url, "params": params, "json": json, "headers": headers}
        )
        if not self.responses:
            raise AssertionError("no more fake responses")
        result = self.responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def client(responses, **kwargs):
    return Phylax(api_token="phx_live_test", session=FakeSession(responses), **kwargs)


class TestConstruction:
    def test_requires_a_token(self, monkeypatch):
        monkeypatch.delenv("PHYLAX_API_TOKEN", raising=False)
        monkeypatch.delenv("PHYLAX_API_KEY", raising=False)
        with pytest.raises(APITokenMissing):
            Phylax()

    def test_reads_the_token_from_the_environment(self, monkeypatch):
        monkeypatch.setenv("PHYLAX_API_TOKEN", "from-env")
        assert Phylax().api.api_token == "from-env"

    def test_accepts_the_alternate_env_name(self, monkeypatch):
        monkeypatch.delenv("PHYLAX_API_TOKEN", raising=False)
        monkeypatch.setenv("PHYLAX_API_KEY", "from-key")
        assert Phylax().api.api_token == "from-key"

    def test_sends_a_bearer_token(self):
        c = client([FakeResponse(payload={"status": "ok"})])
        c.health()
        assert c.api.session.calls[0]["headers"]["Authorization"] == "Bearer phx_live_test"

    def test_identifies_itself(self):
        c = client([FakeResponse(payload={})], user_agent="phylax-agent/1.0")
        c.health()
        assert c.api.session.calls[0]["headers"]["User-Agent"].startswith("phylax-agent/1.0 ")


class TestExceptions:
    @pytest.mark.parametrize(
        "status,expected",
        [
            (401, APIAuthenticationError),
            (402, APIPlanRequired),
            (403, APIAccessDenied),
            (404, APIResourceNotFound),
            (500, APIServerError),
        ],
    )
    def test_raises_a_typed_exception_per_status(self, status, expected):
        c = client([FakeResponse(status=status, text="denied")], max_retries=1)
        with pytest.raises(expected):
            c.health()

    def test_rate_limited_carries_retry_after(self):
        c = client(
            [FakeResponse(status=429, text="slow down", headers={"Retry-After": "12"})],
            max_retries=1,
        )
        with pytest.raises(APIRateLimited) as info:
            c.health()
        assert info.value.retry_after == 12

    def test_quota_exhaustion_is_distinct_from_rate_limiting(self):
        c = client([FakeResponse(status=429, text="quota exhausted")], max_retries=1)
        with pytest.raises(APIQuotaExceeded):
            c.health()

    def test_never_leaks_the_token_into_an_error(self):
        token = "phx_live_supersecret"
        session = FakeSession([FakeResponse(status=401, text=f"bad token {token}")])
        c = Phylax(api_token=token, session=session, max_retries=1)
        with pytest.raises(APIAuthenticationError) as info:
            c.health()
        assert token not in str(info.value)
        assert "***" in str(info.value)


class TestRetries:
    def test_retries_idempotent_requests_on_5xx(self):
        c = client(
            [
                FakeResponse(status=503, text="busy", headers={"Retry-After": "0"}),
                FakeResponse(payload={"status": "ok"}),
            ]
        )
        assert c.health() == {"status": "ok"}
        assert len(c.api.session.calls) == 2

    def test_does_not_retry_a_write_on_5xx(self):
        c = client([FakeResponse(status=502, text="bad gateway")])
        with pytest.raises(APIServerError):
            c.artifacts.verify("pkg:npm/x@1")
        assert len(c.api.session.calls) == 1

    def test_retries_a_write_on_429(self):
        c = client(
            [
                FakeResponse(status=429, text="slow", headers={"Retry-After": "0"}),
                FakeResponse(payload={"verdict": "ALLOW"}),
            ]
        )
        assert c.artifacts.verify("pkg:npm/x@1")["verdict"] == "ALLOW"

    def test_retry_policy_by_method(self):
        assert is_retryable("GET", 503) is True
        assert is_retryable("POST", 502) is False
        assert is_retryable("POST", 429) is True
        assert is_retryable("GET", 404) is False

    def test_retry_after_wins_over_backoff(self):
        assert retry_delay(0, "5") == 5

    def test_backoff_is_jittered_not_fixed(self):
        assert retry_delay(3, None, rand=lambda: 1.0) == 8
        assert retry_delay(3, None, rand=lambda: 0.0) == 0

    def test_backoff_is_capped(self):
        assert retry_delay(20, None, rand=lambda: 1.0) == 30

    def test_connection_errors_surface_as_typed_failures(self):
        from phylax import APIConnectionError

        c = client([requests.ConnectionError("refused")], max_retries=1)
        with pytest.raises(APIConnectionError):
            c.health()


class TestResources:
    def test_verify_posts_the_artifact(self):
        c = client([FakeResponse(payload={"verdict": "ALLOW"})])
        c.artifacts.verify("pkg:npm/express@4.18.2")
        call = c.api.session.calls[0]
        assert call["method"] == "POST"
        assert call["url"].endswith("/v1/artifacts/verify")
        assert call["json"] == {"artifact": "pkg:npm/express@4.18.2"}

    def test_verify_many_batches(self):
        c = client([FakeResponse(payload=[])])
        c.artifacts.verify_many(["pkg:npm/a@1", "pkg:pypi/b@2"])
        assert len(c.api.session.calls) == 1
        assert len(c.api.session.calls[0]["json"]["artifacts"]) == 2

    def test_path_segments_are_encoded(self):
        c = client([FakeResponse(payload={})])
        c.artifacts.get("pkg:npm/@scope/pkg@1.0.0")
        assert "pkg%3Anpm%2F%40scope%2Fpkg%401.0.0" in c.api.session.calls[0]["url"]

    def test_none_params_are_dropped(self):
        c = client([FakeResponse(payload={})])
        c.artifacts.search("express")
        assert c.api.session.calls[0]["params"] == {"q": "express"}

    def test_policy_evaluate(self):
        c = client([FakeResponse(payload={"verdict": "allow", "score": 92})])
        result = c.policies.evaluate("pkg:npm/x@1", policy="prod")
        assert result["score"] == 92
        assert c.api.session.calls[0]["url"].endswith("/v1/policies/evaluate")

    def test_empty_body_returns_none(self):
        c = client([FakeResponse(status=204, text="")])
        assert c.webhooks.delete("wh_1") is None


class TestRedaction:
    def test_short_tokens_are_left_alone(self):
        assert redact("value", "abc") == "value"

    def test_long_tokens_are_masked(self):
        assert redact("see phx_live_1234567890 here", "phx_live_1234567890") == "see *** here"
