from typing import Any, Dict, List, NamedTuple, Optional

from phylax.core.api import API

PLAN_ORDER = ["free", "team", "business", "enterprise"]

METHOD_REQUIREMENTS: Dict[str, Dict[str, Any]] = {
    "artifacts.verify": {"quota_cost": 1, "permissions": ["artifacts:verify"], "minimum_plan": "free"},
    "artifacts.get": {"quota_cost": 1, "permissions": ["artifacts:read"], "minimum_plan": "free"},
    "artifacts.search": {"quota_cost": 1, "permissions": ["artifacts:read"], "minimum_plan": "free"},
    "attestations.list": {"quota_cost": 1, "permissions": ["attestations:read"], "minimum_plan": "free"},
    "attestations.get": {"quota_cost": 1, "permissions": ["attestations:read"], "minimum_plan": "free"},
    "artifacts.verify_many": {"quota_cost": 1, "permissions": ["artifacts:verify"], "minimum_plan": "team"},
    "artifacts.list": {"quota_cost": 1, "permissions": ["artifacts:read"], "minimum_plan": "team"},
    "attestations.verify": {"quota_cost": 2, "permissions": ["attestations:verify"], "minimum_plan": "team"},
    "policies.list": {"quota_cost": 1, "permissions": ["policies:read"], "minimum_plan": "team"},
    "policies.get": {"quota_cost": 1, "permissions": ["policies:read"], "minimum_plan": "team"},
    "policies.evaluate": {"quota_cost": 2, "permissions": ["policies:evaluate"], "minimum_plan": "team"},
    "repositories.list": {"quota_cost": 1, "permissions": ["repositories:read"], "minimum_plan": "team"},
    "repositories.verify": {"quota_cost": 2, "permissions": ["repositories:read"], "minimum_plan": "team"},
    "policies.create": {"quota_cost": 1, "permissions": ["policies:write"], "minimum_plan": "business"},
    "policies.update": {"quota_cost": 1, "permissions": ["policies:write"], "minimum_plan": "business"},
    "policies.delete": {"quota_cost": 1, "permissions": ["policies:write"], "minimum_plan": "business"},
    "repositories.add": {"quota_cost": 1, "permissions": ["repositories:write"], "minimum_plan": "business"},
    "webhooks.list": {"quota_cost": 1, "permissions": ["webhooks:read"], "minimum_plan": "business"},
    "webhooks.create": {"quota_cost": 1, "permissions": ["webhooks:write"], "minimum_plan": "business"},
}


class AccessCheck(NamedTuple):
    allowed: bool
    reasons: List[str]
    requirement: Optional[Dict[str, Any]]


def plan_at_least(actual: str, required: str) -> bool:
    try:
        return PLAN_ORDER.index(actual) >= PLAN_ORDER.index(required)
    except ValueError:
        return False


class Quota:
    def __init__(self, api: API) -> None:
        self.api = api

    def entitlements(self) -> Dict[str, Any]:
        return self.api.get("/v1/account/entitlements")

    def get_requirement(self, method: str) -> Optional[Dict[str, Any]]:
        return METHOD_REQUIREMENTS.get(method)

    def total_quota_cost(self, methods: List[str]) -> int:
        return sum(METHOD_REQUIREMENTS.get(m, {}).get("quota_cost", 0) for m in methods)

    def check_access(self, method: str, entitlements: Dict[str, Any]) -> AccessCheck:
        requirement = METHOD_REQUIREMENTS.get(method)
        if requirement is None:
            return AccessCheck(True, [], None)

        reasons: List[str] = []
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

    def methods_for_plan(self, plan: str) -> List[str]:
        return [
            method
            for method, req in METHOD_REQUIREMENTS.items()
            if plan_at_least(plan, req["minimum_plan"])
        ]

    def methods_requiring_permission(self, permission: str) -> List[str]:
        return [
            method
            for method, req in METHOD_REQUIREMENTS.items()
            if permission in req["permissions"]
        ]
