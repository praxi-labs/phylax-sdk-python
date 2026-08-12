from typing import Any, Dict, List

PLAN_ORDER: List[str] = ["free", "team", "business", "enterprise"]

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


def plan_at_least(actual: str, required: str) -> bool:
    try:
        return PLAN_ORDER.index(actual) >= PLAN_ORDER.index(required)
    except ValueError:
        return False
