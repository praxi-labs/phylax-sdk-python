import hashlib
import hmac
import json
import time

from phylax import Phylax, verify_signature
from phylax.quota import plan_at_least

FREE = {
    "plan": "free",
    "permissions": ["artifacts:read", "artifacts:verify"],
    "quota_remaining": 100,
}
BUSINESS = {
    "plan": "business",
    "permissions": [
        "artifacts:read",
        "artifacts:verify",
        "policies:read",
        "policies:write",
        "policies:evaluate",
        "webhooks:read",
        "webhooks:write",
    ],
    "quota_remaining": 10000,
}


def sdk():
    return Phylax(api_token="phx_live_test")


class TestPlans:
    def test_plan_ordering_is_cumulative(self):
        assert plan_at_least("business", "team") is True
        assert plan_at_least("free", "team") is False
        assert plan_at_least("unknown", "free") is False

    def test_free_plan_allows_what_it_pays_for(self):
        check = sdk().quota.check_access("artifacts.verify", FREE)
        assert check.allowed is True
        assert check.reasons == []

    def test_free_plan_is_refused_a_business_method_with_reasons(self):
        check = sdk().quota.check_access("webhooks.create", FREE)
        assert check.allowed is False
        joined = " ".join(check.reasons)
        assert "business plan or above" in joined
        assert "missing permissions" in joined

    def test_exhausted_quota_blocks_a_sufficient_plan(self):
        entitlements = dict(BUSINESS, quota_remaining=1)
        check = sdk().quota.check_access("policies.evaluate", entitlements)
        assert check.allowed is False
        assert "quota exhausted" in " ".join(check.reasons)

    def test_ungated_method_passes_through(self):
        check = sdk().quota.check_access("health", FREE)
        assert check.allowed is True
        assert check.requirement is None

    def test_total_cost_of_a_batch(self):
        assert (
            sdk().quota.total_quota_cost(
                ["artifacts.verify", "policies.evaluate", "attestations.verify"]
            )
            == 5
        )

    def test_methods_for_plan_grow_with_the_plan(self):
        free_methods = sdk().quota.methods_for_plan("free")
        business_methods = sdk().quota.methods_for_plan("business")
        assert "artifacts.verify" in free_methods
        assert "webhooks.create" not in free_methods
        assert "webhooks.create" in business_methods
        assert len(business_methods) > len(free_methods)

    def test_reverse_permission_lookup(self):
        methods = sdk().quota.methods_requiring_permission("policies:write")
        assert set(methods) >= {"policies.create", "policies.update", "policies.delete"}


BODY = json.dumps({"event": "verdict.changed"})
TS = 1786240895


def sign(ts, body, secret="whsec"):
    return (
        "sha256="
        + hmac.new(secret.encode(), f"{ts}.".encode() + body.encode(), hashlib.sha256).hexdigest()
    )


class TestSignature:
    def test_accepts_a_valid_delivery(self):
        assert verify_signature(BODY, sign(TS, BODY), TS, "whsec", now=TS).valid is True

    def test_accepts_bytes_identically(self):
        assert verify_signature(BODY.encode(), sign(TS, BODY), TS, "whsec", now=TS).valid is True

    def test_rejects_a_reserialised_body(self):
        reordered = json.dumps({"event": "verdict.changed", "extra": 1})
        assert verify_signature(reordered, sign(TS, BODY), TS, "whsec", now=TS).valid is False

    def test_rejects_the_wrong_secret(self):
        result = verify_signature(BODY, sign(TS, BODY, "other"), TS, "whsec", now=TS)
        assert result.valid is False
        assert result.reason == "Signature mismatch"

    def test_rejects_a_replay_outside_tolerance(self):
        result = verify_signature(BODY, sign(TS, BODY), TS, "whsec", now=TS + 600)
        assert result.valid is False
        assert "tolerance" in result.reason

    def test_tolerates_skew_in_both_directions(self):
        assert verify_signature(BODY, sign(TS, BODY), TS, "whsec", now=TS + 120).valid is True
        assert verify_signature(BODY, sign(TS, BODY), TS, "whsec", now=TS - 120).valid is True

    def test_reports_missing_headers_distinctly(self):
        assert verify_signature(BODY, None, TS, "whsec").reason == "Missing signature header"
        assert verify_signature(BODY, "sig", None, "whsec").reason == "Missing timestamp header"

    def test_does_not_raise_on_a_truncated_signature(self):
        result = verify_signature(BODY, "sha256=dead", TS, "whsec", now=TS)
        assert result.valid is False

    def test_uses_wall_clock_when_now_is_omitted(self):
        now = int(time.time())
        assert verify_signature(BODY, sign(now, BODY), now, "whsec").valid is True
