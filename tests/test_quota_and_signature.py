import hashlib
import hmac
import json
import time

from phylax import Phylax, verify_signature
from phylax.quota import METHOD_REQUIREMENTS, is_paid_plan, plan_at_least

ANONYMOUS = {
    "plan": "anonymous",
    "permissions": [],
    "quota_remaining": 0,
}
BUILDER = {
    "plan": "builder",
    "permissions": ["artifacts:read", "artifacts:verify"],
    "quota_remaining": 100,
}
MARKETPLACE = {
    "plan": "marketplace",
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
        assert plan_at_least("marketplace", "builder") is True
        assert plan_at_least("builder", "marketplace") is False
        assert plan_at_least("anonymous", "builder") is False
        assert plan_at_least("unknown", "builder") is False

    def test_anonymous_is_the_only_unpaid_plan(self):
        assert is_paid_plan("anonymous") is False
        assert is_paid_plan("builder") is True
        assert is_paid_plan("marketplace") is True
        assert is_paid_plan("enterprise") is True

    def test_no_method_is_reachable_without_paying(self):
        for method in METHOD_REQUIREMENTS:
            check = sdk().quota.check_access(method, ANONYMOUS)
            assert check.allowed is False, f"{method} is reachable on the anonymous plan"

    def test_every_method_requires_a_paid_plan(self):
        for method, requirement in METHOD_REQUIREMENTS.items():
            assert is_paid_plan(requirement["minimum_plan"]), (
                f"{method} declares the unpaid plan {requirement['minimum_plan']}"
            )

    def test_builder_allows_what_it_pays_for(self):
        check = sdk().quota.check_access("artifacts.verify", BUILDER)
        assert check.allowed is True
        assert check.reasons == []

    def test_builder_is_refused_a_marketplace_method_with_reasons(self):
        check = sdk().quota.check_access("policies.evaluate", BUILDER)
        assert check.allowed is False
        joined = " ".join(check.reasons)
        assert "marketplace plan or above" in joined
        assert "missing permissions" in joined

    def test_exhausted_quota_blocks_a_sufficient_plan(self):
        entitlements = dict(MARKETPLACE, quota_remaining=1)
        check = sdk().quota.check_access("policies.evaluate", entitlements)
        assert check.allowed is False
        assert "quota exhausted" in " ".join(check.reasons)

    def test_unknown_method_is_refused_rather_than_waved_through(self):
        check = sdk().quota.check_access("health", MARKETPLACE)
        assert check.allowed is False
        assert check.requirement is None
        assert "unknown method" in " ".join(check.reasons)

    def test_total_cost_of_a_batch(self):
        assert (
            sdk().quota.total_quota_cost(
                ["artifacts.verify", "policies.evaluate", "attestations.verify"]
            )
            == 5
        )

    def test_methods_for_plan_grow_with_the_plan(self):
        anonymous_methods = sdk().quota.methods_for_plan("anonymous")
        builder_methods = sdk().quota.methods_for_plan("builder")
        marketplace_methods = sdk().quota.methods_for_plan("marketplace")
        assert anonymous_methods == []
        assert "artifacts.verify" in builder_methods
        assert "policies.evaluate" not in builder_methods
        assert "policies.evaluate" in marketplace_methods
        assert len(marketplace_methods) > len(builder_methods)

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
