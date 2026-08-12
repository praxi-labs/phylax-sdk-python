# API reference

Every method is reached through a `Phylax` instance. Resources are grouped on the client so the call reads like the thing you are asking about.

```python
from phylax import Phylax

phylax = Phylax(api_token="phx_live_...")
```

Methods return the decoded JSON body. They raise on failure rather than returning an error value, so there is no result object to unwrap. See [exceptions and retries](exceptions-and-retries.md).

## Client

### `Phylax(...)`

| Argument | Type | Default | Notes |
| --- | --- | --- | --- |
| `api_token` | `str` | `PHYLAX_API_TOKEN` env | `PHYLAX_API_KEY` is also read. Raises `APITokenMissing` if neither is set. |
| `base_url` | `str` | `https://api.phyi.dev` | Trailing slashes are stripped. |
| `timeout` | `int` | `30` | Seconds, applied per attempt rather than per call. |
| `max_retries` | `int` | `3` | Total attempts, not additional ones. |
| `user_agent` | `str` | none | Prepended to the SDK user agent so your traffic is identifiable. |
| `session` | `requests.Session` | new session | Inject a session to share a connection pool or to stub transport in tests. |

### `phylax.health()`

Liveness of the API. Useful as a startup check before a long running process begins issuing verifications.

### `phylax.server_identity()`

The identity the API presents for itself, for callers that pin or audit it.

### `phylax.me()`

The account the token belongs to. Read this once at startup to confirm a token is bound to the tenant you expect.

## Artifacts

An artifact is anything you depend on that Phylax can reason about: a package, an MCP server, a source repository or a skill. References use [package URL](https://github.com/package-url/purl-spec) syntax.

### `artifacts.verify(artifact, policy=None, include=None)`

Verify a single artifact and return a verdict.

| Argument | Type | Notes |
| --- | --- | --- |
| `artifact` | `str` | Package URL, for example `pkg:npm/express@4.18.2`. |
| `policy` | `str` | Named policy. Omit to use the organization default. |
| `include` | `list[str]` | Extra sections to compute, such as `vulnerabilities` or `licenses`. |

```python
result = phylax.artifacts.verify("pkg:npm/express@4.18.2")

if result["verdict"] == "BLOCK":
    raise SystemExit(1)
```

The verdict is one of `ALLOW`, `WARN` or `BLOCK`. Treat anything you do not recognize as `BLOCK`, so a verdict added in a later API version fails closed rather than passing silently.

### `artifacts.verify_many(artifacts, policy=None, include=None)`

Verify a list in a single round trip. Prefer this over a loop: one call costs one unit of quota where a loop costs one per artifact, and it avoids serialising network latency across a dependency tree.

```python
results = phylax.artifacts.verify_many(
    [
        "pkg:npm/express@4.18.2",
        "pkg:pypi/requests@2.32.3",
    ]
)
```

### `artifacts.get(artifact)`

The stored record for one artifact, including its most recent verification.

### `artifacts.list(ecosystem=None, limit=None, page=None)`

Artifacts known to your account.

### `artifacts.search(query, ecosystem=None, limit=None)`

Free text search across artifacts. Use this when you have a name rather than a fully qualified package URL.

## Attestations

An attestation is signed evidence about an artifact produced by the network. It is what lets a consumer check a claim without trusting the party that made it.

### `attestations.list(artifact, limit=None, page=None)`

Attestations recorded for an artifact, newest first.

### `attestations.get(attestation_id)`

One attestation by identifier.

### `attestations.verify(bundle)`

Check a bundle you already hold. Pass the bundle exactly as received.

```python
verified = phylax.attestations.verify(bundle)
```

Verifying locally held evidence is the point of this method. If you fetch and trust in one step you have gained nothing over a plain lookup, so the flow that matters is to receive a bundle out of band and confirm it here.

## Policies

A policy turns findings into a verdict. Keeping that decision on the server means every integration in your organization, whether CI, the runtime gate or a developer's editor, applies the same rule.

### `policies.list()`

### `policies.get(policy_id)`

### `policies.create(policy)`

### `policies.update(policy_id, policy)`

Partial update. Only the keys you pass are changed.

### `policies.delete(policy_id)`

### `policies.evaluate(artifact, policy=None, include=None)`

Evaluate an artifact against a policy without changing anything.

```python
decision = phylax.policies.evaluate(
    "pkg:npm/express@4.18.2",
    policy="prod-runtime-policy",
    include=["vulnerabilities", "licenses"],
)
```

Evaluation is the read only counterpart to `artifacts.verify`. Use it to preview the effect of a policy change before you publish it.

Every policy method requires the marketplace plan or above. A policy is how a team enforces one decision across everyone, which is the marketplace boundary.

## Repositories

### `repositories.list()`

### `repositories.get(repository_id)`

### `repositories.add(url, provider=None, policy=None)`

Track a repository. Passing `policy` binds it at registration, which is more reliable than remembering to pass one at each verification.

### `repositories.remove(repository_id)`

### `repositories.verify(url)`

Verify a repository without registering it first. This is the method to reach for when you are evaluating a dependency you do not own.

## Webhooks

Configuration only. Verifying an inbound delivery is covered in [webhooks](webhooks.md).

### `webhooks.list()`

### `webhooks.get(webhook_id)`

### `webhooks.create(url, events, secret=None)`

| Argument | Type | Notes |
| --- | --- | --- |
| `url` | `str` | HTTPS endpoint that receives deliveries. |
| `events` | `list[str]` | Event names to subscribe to. |
| `secret` | `str` | Signing secret. Omit and one is generated and returned once. |

The generated secret is returned on creation and never again. Store it at that moment, because there is no endpoint that reveals it later.

### `webhooks.update(webhook_id, **fields)`

### `webhooks.delete(webhook_id)`

A `builder` subscription may hold one webhook. Creating a second is refused by the server even though the method is available at that plan.

## Quota

Plan and permission introspection. Covered in [plans and quota](plans-and-quota.md).

| Method | Returns |
| --- | --- |
| `quota.entitlements()` | Live plan, permissions and remaining quota. |
| `quota.check_access(method, entitlements)` | `AccessCheck` with `allowed`, `reasons` and `requirement`. |
| `quota.get_requirement(method)` | What one method costs and requires. |
| `quota.total_quota_cost(methods)` | Combined cost of a planned sequence. |
| `quota.methods_for_plan(plan)` | Methods a plan can reach. |
| `quota.methods_requiring_permission(permission)` | Methods gated on a permission. |

## Encoding

Every path segment is percent encoded before it reaches the URL. A package URL contains `/` and `@`, so an unencoded reference would otherwise change which endpoint is called rather than which artifact is looked up.

Query parameters set to `None` are dropped rather than sent empty, so an omitted filter and an explicitly empty one are not confused.
