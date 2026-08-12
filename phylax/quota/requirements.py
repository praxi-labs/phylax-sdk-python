from typing import Any

PLAN_ORDER: list[str] = ["anonymous", "builder", "marketplace", "enterprise"]

PAID_PLANS: list[str] = ["builder", "marketplace", "enterprise"]

METHOD_REQUIREMENTS: dict[str, dict[str, Any]] = {
    "artifacts.verify": {
        "quota_cost": 1,
        "permissions": ["artifacts:verify"],
        "minimum_plan": "builder",
    },
    "artifacts.verify_many": {
        "quota_cost": 1,
        "permissions": ["artifacts:verify"],
        "minimum_plan": "builder",
    },
    "artifacts.get": {
        "quota_cost": 1,
        "permissions": ["artifacts:read"],
        "minimum_plan": "builder",
    },
    "artifacts.list": {
        "quota_cost": 1,
        "permissions": ["artifacts:read"],
        "minimum_plan": "builder",
    },
    "artifacts.search": {
        "quota_cost": 1,
        "permissions": ["artifacts:read"],
        "minimum_plan": "builder",
    },
    "attestations.list": {
        "quota_cost": 1,
        "permissions": ["attestations:read"],
        "minimum_plan": "builder",
    },
    "attestations.get": {
        "quota_cost": 1,
        "permissions": ["attestations:read"],
        "minimum_plan": "builder",
    },
    "attestations.verify": {
        "quota_cost": 2,
        "permissions": ["attestations:verify"],
        "minimum_plan": "builder",
    },
    "policies.list": {
        "quota_cost": 1,
        "permissions": ["policies:read"],
        "minimum_plan": "marketplace",
    },
    "policies.get": {
        "quota_cost": 1,
        "permissions": ["policies:read"],
        "minimum_plan": "marketplace",
    },
    "policies.create": {
        "quota_cost": 1,
        "permissions": ["policies:write"],
        "minimum_plan": "marketplace",
    },
    "policies.update": {
        "quota_cost": 1,
        "permissions": ["policies:write"],
        "minimum_plan": "marketplace",
    },
    "policies.delete": {
        "quota_cost": 1,
        "permissions": ["policies:write"],
        "minimum_plan": "marketplace",
    },
    "policies.evaluate": {
        "quota_cost": 2,
        "permissions": ["policies:evaluate"],
        "minimum_plan": "marketplace",
    },
    "repositories.list": {
        "quota_cost": 1,
        "permissions": ["repositories:read"],
        "minimum_plan": "builder",
    },
    "repositories.get": {
        "quota_cost": 1,
        "permissions": ["repositories:read"],
        "minimum_plan": "builder",
    },
    "repositories.add": {
        "quota_cost": 1,
        "permissions": ["repositories:write"],
        "minimum_plan": "builder",
    },
    "repositories.remove": {
        "quota_cost": 1,
        "permissions": ["repositories:write"],
        "minimum_plan": "builder",
    },
    "repositories.verify": {
        "quota_cost": 1,
        "permissions": ["repositories:read"],
        "minimum_plan": "builder",
    },
    "webhooks.list": {
        "quota_cost": 1,
        "permissions": ["webhooks:read"],
        "minimum_plan": "builder",
    },
    "webhooks.get": {
        "quota_cost": 1,
        "permissions": ["webhooks:read"],
        "minimum_plan": "builder",
    },
    "webhooks.create": {
        "quota_cost": 1,
        "permissions": ["webhooks:write"],
        "minimum_plan": "builder",
    },
    "webhooks.update": {
        "quota_cost": 1,
        "permissions": ["webhooks:write"],
        "minimum_plan": "builder",
    },
    "webhooks.delete": {
        "quota_cost": 1,
        "permissions": ["webhooks:write"],
        "minimum_plan": "builder",
    },
}


def plan_at_least(actual: str, required: str) -> bool:
    try:
        return PLAN_ORDER.index(actual) >= PLAN_ORDER.index(required)
    except ValueError:
        return False


def is_paid_plan(plan: str) -> bool:
    return plan in PAID_PLANS
