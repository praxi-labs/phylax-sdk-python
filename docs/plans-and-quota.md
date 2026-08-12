# Plans and quota

Access to the Phylax API is controlled by subscription plan, by token permissions and by a period quota. All three are enforced on the server. The helpers in `phylax.quota` exist so your application can anticipate a rejection rather than discover it, which is the difference between a clear message at startup and a failed deploy at three in the morning.

Nothing here grants access. A client cannot decide what it is entitled to.

## Plans

| Plan | Adds |
| --- | --- |
| `free` | Single artifact verification, artifact and attestation reads, search. |
| `team` | Batch verification, artifact listing, policy read and evaluate, attestation verification, repository read and verify. |
| `business` | Policy authoring, repository registration, webhooks. |
| `enterprise` | Everything, with negotiated limits. |

Plans are ordered, so a business token satisfies every team requirement.

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
```

`AccessCheck` is a named tuple:

| Field | Type | Meaning |
| --- | --- | --- |
| `allowed` | `bool` | Whether every requirement is met. |
| `reasons` | `list[str]` | Human readable failures. Empty when allowed. |
| `requirement` | `dict` or `None` | Cost, permissions and minimum plan. `None` for unmetered methods. |

Three conditions are checked: the token holds every required permission, the plan is at or above the minimum, and remaining quota covers the cost. All failures are collected, so a token that is short a permission and short of quota reports both rather than reporting one and then the other on the next attempt.

## Planning a batch

Before a run that will spend many calls, price it first.

```python
planned = ["artifacts.verify"] * len(dependencies)
cost = phylax.quota.total_quota_cost(planned)

if cost > phylax.quota.entitlements()["quota_remaining"]:
    raise SystemExit(f"{cost} units needed, not enough remaining")
```

A job that stops before it starts is easier to reason about than one that fails partway with half its work committed.

This is also the argument for `artifacts.verify_many`. One batch call costs a single unit where the loop above costs one per dependency.

## Introspection

`methods_for_plan` and `methods_requiring_permission` answer the questions that come up when you are provisioning a token or writing an upgrade prompt.

```python
phylax.quota.methods_for_plan("team")
phylax.quota.methods_requiring_permission("policies:write")
```

Use them to mint a token with the narrowest permission set that covers what your integration actually calls, rather than reaching for a token that can do everything.

## When the server disagrees

The requirement table is a local copy and the server is the authority. If a plan changes, or a method is regraded, the table can be stale until you upgrade the SDK.

So treat `check_access` as a fast path that avoids a doomed request, and still handle `APIPlanRequired`, `APIAccessDenied` and `APIQuotaExceeded` at the call site. A check that passes is not a guarantee, and the SDK never treats it as one.

## Handling a rejection

```python
from phylax import APIAccessDenied, APIPlanRequired, APIQuotaExceeded

try:
    phylax.policies.create(policy)
except APIPlanRequired:
    ...  # the subscription does not include policy authoring
except APIAccessDenied:
    ...  # the plan covers it but this token lacks policies:write
except APIQuotaExceeded:
    ...  # the allowance is spent for this period
```

These three failures look alike from the outside and need different responses. A plan failure calls for an upgrade, a permission failure calls for a better scoped token, and a quota failure calls for waiting or for a larger allowance.
