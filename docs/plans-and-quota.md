# Plans and quota

Access to the Phylax API is controlled by subscription plan, by token permissions and by a period allowance. All three are enforced on the server. The helpers in `phylax.quota` exist so your application can anticipate a rejection rather than discover it, which is the difference between a clear message at startup and a failed deploy at three in the morning.

Nothing here grants access. A client cannot decide what it is entitled to.

## The plans

| Plan | Who it is for | API access |
| --- | --- | --- |
| `anonymous` | The public, with no account | None |
| `builder` | Individual developers and researchers | Keys, with a daily allowance |
| `marketplace` | Engineering teams with private code | Unlimited, on a priority queue |
| `enterprise` | Organizations needing governance and compliance | Custom volume |

`anonymous` is the only free plan and it has no programmatic access at all. It covers the public catalog, search and public scores through the web, at a capped rate. Every method in this SDK requires `builder` or above, so a token is always attached to a paid subscription.

Plans are cumulative, so a `marketplace` token satisfies every `builder` requirement.

```python
from phylax.quota import is_paid_plan, plan_at_least

is_paid_plan("anonymous")  # False
plan_at_least("marketplace", "builder")  # True
```

## Reading entitlements

```python
entitlements = phylax.quota.entitlements()

print(entitlements["plan"])
print(entitlements["permissions"])
print(entitlements["quota_remaining"])
```

This is the authoritative view. Read it at startup rather than per call, and cache it for the life of the process. It changes when a subscription changes, not between requests.

## Checking before you call

`check_access` compares a method against a set of entitlements and tells you whether it would succeed.

```python
entitlements = phylax.quota.entitlements()
check = phylax.quota.check_access("policies.evaluate", entitlements)

if not check.allowed:
    raise SystemExit("; ".join(check.reasons))
    # requires the marketplace plan or above, current plan is builder
```

`AccessCheck` is a named tuple:

| Field | Type | Meaning |
| --- | --- | --- |
| `allowed` | `bool` | Whether every requirement is met. |
| `reasons` | `list[str]` | Human readable failures. Empty when allowed. |
| `requirement` | `dict` or `None` | Cost, permissions and minimum plan. `None` when the method is unknown. |

Three conditions are checked: the token holds every required permission, the plan is at or above the minimum, and the remaining allowance covers the cost. All failures are collected, so a token that is short a permission and short of allowance reports both rather than reporting one and then the other on the next attempt.

An unrecognised method name is refused rather than waved through, so a typo or a method from a newer SDK version fails closed.

## Planning a batch

Before a run that will spend many calls, price it first.

```python
planned = ["artifacts.verify"] * len(dependencies)
cost = phylax.quota.total_quota_cost(planned)

if cost > phylax.quota.entitlements()["quota_remaining"]:
    raise SystemExit(f"{cost} units needed, not enough remaining")
```

A job that stops before it starts is easier to reason about than one that fails partway with half its work committed. This matters most on `builder`, where the allowance is daily.

This is also the argument for `artifacts.verify_many`. One batch call costs a single unit where the loop above costs one per dependency.

## Introspection

`methods_for_plan` and `methods_requiring_permission` answer the questions that come up when you are provisioning a token or writing an upgrade prompt.

```python
phylax.quota.methods_for_plan("builder")
phylax.quota.methods_requiring_permission("policies:write")
```

`methods_for_plan("anonymous")` returns an empty list, which is the honest answer rather than an oversight.

Use them to mint a token with the narrowest permission set that covers what your integration actually calls, rather than reaching for a token that can do everything.

## What each method requires

Costs are relative units. A verification is one unit; anything that runs a policy or a signature check is two.

| Method | Cost | Permissions | Minimum plan |
| --- | --- | --- | --- |
| `artifacts.verify` | 1 | `artifacts:verify` | builder |
| `artifacts.verify_many` | 1 | `artifacts:verify` | builder |
| `artifacts.get` | 1 | `artifacts:read` | builder |
| `artifacts.list` | 1 | `artifacts:read` | builder |
| `artifacts.search` | 1 | `artifacts:read` | builder |
| `attestations.list` | 1 | `attestations:read` | builder |
| `attestations.get` | 1 | `attestations:read` | builder |
| `attestations.verify` | 2 | `attestations:verify` | builder |
| `repositories.list` | 1 | `repositories:read` | builder |
| `repositories.get` | 1 | `repositories:read` | builder |
| `repositories.add` | 1 | `repositories:write` | builder |
| `repositories.remove` | 1 | `repositories:write` | builder |
| `webhooks.list` | 1 | `webhooks:read` | builder |
| `webhooks.get` | 1 | `webhooks:read` | builder |
| `webhooks.create` | 1 | `webhooks:write` | builder |
| `webhooks.update` | 1 | `webhooks:write` | builder |
| `webhooks.delete` | 1 | `webhooks:write` | builder |
| `policies.list` | 1 | `policies:read` | marketplace |
| `policies.get` | 1 | `policies:read` | marketplace |
| `policies.create` | 1 | `policies:write` | marketplace |
| `policies.update` | 1 | `policies:write` | marketplace |
| `policies.delete` | 1 | `policies:write` | marketplace |
| `policies.evaluate` | 2 | `policies:evaluate` | marketplace |

Policy controls are the `marketplace` boundary, because a policy is how a team enforces one decision across everyone. Everything else in the SDK is available to an individual `builder` subscription.

Some limits are not expressible in this table and are enforced by the server. A `builder` subscription may hold one webhook rather than many, and may run CI against public repositories rather than private ones. The method is available at `builder`; the specific request may still be refused.

## When the server disagrees

The requirement table is a local copy and the server is the authority. If a plan changes, or a method is regraded, the table can be stale until you upgrade the SDK.

So treat `check_access` as a fast path that avoids a doomed request, and still handle `APIPlanRequired`, `APIAccessDenied` and `APIQuotaExceeded` at the call site. A check that passes is not a guarantee, and the SDK never treats it as one.

## Handling a rejection

```python
from phylax import APIAccessDenied, APIPlanRequired, APIQuotaExceeded

try:
    phylax.policies.create(policy)
except APIPlanRequired:
    ...  # the subscription does not include policy controls
except APIAccessDenied:
    ...  # the plan covers it but this token lacks policies:write
except APIQuotaExceeded:
    ...  # the allowance is spent for this period
```

These three failures look alike from the outside and need different responses. A plan failure calls for an upgrade, a permission failure calls for a better scoped token, and an allowance failure calls for waiting or for a larger subscription.
