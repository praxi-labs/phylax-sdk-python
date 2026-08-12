from typing import Any, NamedTuple

from phylax.core.api import API
from phylax.quota.requirements import METHOD_REQUIREMENTS, plan_at_least


class AccessCheck(NamedTuple):
    allowed: bool
    reasons: list[str]
    requirement: dict[str, Any] | None


class Quota:
    def __init__(self, api: API) -> None:
        self.api = api

    def entitlements(self) -> dict[str, Any]:
        return self.api.get("/v1/account/entitlements")

    def get_requirement(self, method: str) -> dict[str, Any] | None:
        return METHOD_REQUIREMENTS.get(method)

    def total_quota_cost(self, methods: list[str]) -> int:
        return sum(METHOD_REQUIREMENTS.get(m, {}).get("quota_cost", 0) for m in methods)

    def check_access(self, method: str, entitlements: dict[str, Any]) -> AccessCheck:
        requirement = METHOD_REQUIREMENTS.get(method)
        if requirement is None:
            return AccessCheck(False, [f"unknown method: {method}"], None)

        reasons: list[str] = []
        held = set(entitlements.get("permissions") or [])

        missing = [p for p in requirement["permissions"] if p not in held]
        if missing:
            reasons.append(f"missing permissions: {', '.join(missing)}")

        plan = str(entitlements.get("plan", ""))
        if not plan_at_least(plan, requirement["minimum_plan"]):
            reasons.append(
                f"requires the {requirement['minimum_plan']} plan or above, current plan is {plan}"
            )

        remaining = entitlements.get("quota_remaining")
        if isinstance(remaining, int) and remaining < requirement["quota_cost"]:
            reasons.append(
                f"quota exhausted, {remaining} remaining but {requirement['quota_cost']} required"
            )

        return AccessCheck(not reasons, reasons, requirement)

    def methods_for_plan(self, plan: str) -> list[str]:
        return [
            method
            for method, req in METHOD_REQUIREMENTS.items()
            if plan_at_least(plan, req["minimum_plan"])
        ]

    def methods_requiring_permission(self, permission: str) -> list[str]:
        return [
            method
            for method, req in METHOD_REQUIREMENTS.items()
            if permission in req["permissions"]
        ]
