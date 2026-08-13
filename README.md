# phylax-sdk

[![PyPI](https://img.shields.io/badge/PyPI-pending-informational)](https://github.com/praxi-labs/phylax-sdk-python/releases)

Python SDK for the [Phylax](https://phyi.dev) API. Package verification, policy evaluation, attestations, and plan aware quota handling.

This is the canonical Python client for the Phylax API. It exists so any Python application, whether that is a build script, an agent runtime, or your own security service, can verify what your software depends on without hand rolling auth, retries, redaction and error handling.

## Install

```sh
pip install phylax-sdk
```

The distribution is `phylax-sdk` and the import is `phylax`:

```python
from phylax import Phylax
```

An unrelated project already holds the name `phylax` on PyPI, so `pip install phylax` installs something else entirely. Check the distribution name before you install.

## Usage

<details open>
<summary><b>Quickstart</b>: verify a package and act on the verdict</summary>

```python
from phylax import Phylax, APIFailure

phylax = Phylax()  # reads PHYLAX_API_TOKEN from the environment

try:
    result = phylax.artifacts.verify("pkg:npm/express@4.18.2")
except APIFailure as error:
    print(error.code, error.message)
else:
    if result["verdict"] == "BLOCK":
        raise SystemExit(1)
```

Verify a whole dependency list in one call:

```python
results = phylax.artifacts.verify_many(
    [
        "pkg:npm/express@4.18.2",
        "pkg:pypi/requests@2.32.3",
    ]
)
```

Evaluate against your organization policy:

```python
decision = phylax.policies.evaluate(
    "pkg:npm/express@4.18.2",
    policy="prod-runtime-policy",
    include=["vulnerabilities", "licenses"],
)
```

</details>

<details>
<summary><b>Handle plan and quota limits</b></summary>

```python
from phylax import APIPlanRequired, APIQuotaExceeded

try:
    phylax.policies.evaluate("pkg:npm/express@4.18.2")
except APIPlanRequired:
    ...  # capability is not part of this subscription
except APIQuotaExceeded:
    ...  # period quota is spent
```

Check before spending a call:

```python
entitlements = phylax.quota.entitlements()
check = phylax.quota.check_access("policies.evaluate", entitlements)

if not check.allowed:
    print("; ".join(check.reasons))
```

</details>

<details>
<summary><b>Verify an inbound webhook delivery</b></summary>

```python
from phylax import verify_signature

result = verify_signature(
    raw_body=request.data,
    signature=request.headers.get("X-Phylax-Signature"),
    timestamp=request.headers.get("X-Phylax-Timestamp"),
    secret=os.environ["PHYLAX_WEBHOOK_SECRET"],
)

if not result.valid:
    abort(401, result.reason)
```

Pass the raw request bytes, not parsed JSON. Any middleware that reparses the payload can reorder keys, which changes the bytes and invalidates a signature that was perfectly good.

</details>

## Documentation

| Guide | Covers |
| --- | --- |
| [API reference](docs/api.md) | Every resource and method, with arguments and plan requirements. |
| [Exceptions and retries](docs/exceptions-and-retries.md) | The exception hierarchy, what is retried and why writes are treated differently. |
| [Plans and quota](docs/plans-and-quota.md) | Checking entitlements before spending a call. |
| [Webhooks](docs/webhooks.md) | Verifying inbound deliveries without opening a replay hole. |

## Exceptions

Methods raise rather than return an error value, which is what Python callers expect. Every failure derives from `APIFailure`, so a single `except APIFailure` catches everything while specific handlers stay available.

| Exception | Status |
| --- | --- |
| `APITokenMissing` | none, raised at construction |
| `APIAuthenticationError` | 401 |
| `APIPlanRequired` | 402 |
| `APIAccessDenied` | 403 |
| `APIResourceNotFound` | 404 |
| `APIRateLimited` | 429, carries `retry_after` |
| `APIQuotaExceeded` | 429 or 402 |
| `APIInvalidRequest` | other 4xx |
| `APIServerError` | 5xx |
| `APIConnectionError` | transport |
| `APITimeout` | transport |

## Retries

Rate limits and transient server faults are retried automatically. `Retry-After` is honoured when present, otherwise the delay is exponential backoff with full jitter, capped at 30 seconds.

Writes are treated differently. A `POST`, `PATCH` or `DELETE` retries only on 429 and 408, where the request was rejected before reaching the handler. A 5xx on a write is ambiguous, because the server may have committed before failing to respond, so it is raised rather than replayed.

## Configuration

| Argument | Default | Notes |
| --- | --- | --- |
| `api_token` | `PHYLAX_API_TOKEN` env | `PHYLAX_API_KEY` also accepted. Raises if absent. |
| `base_url` | `https://api.phyi.dev` | |
| `timeout` | `30` | Seconds, per attempt. |
| `max_retries` | `3` | Total attempts. |
| `user_agent` | none | Prepended to the SDK user agent. |
| `session` | new session | Inject a `requests.Session` for pooling or tests. |

## Security

The API token never appears in an exception message. Response bodies are scanned and the token replaced before being raised, so a 401 body that echoes the credential cannot reach a log. There is a test that fails if this regresses.

Path segments are percent encoded, so an artifact reference cannot escape its position in the URL.

## Development

```sh
pip install -e ".[dev]"
python -m pytest
ruff check .
```

## License

MIT

## The rest of Phylax

| Tool | Where to get it |
| --- | --- |
| JavaScript SDK | [`@phyi/sdk`](https://www.npmjs.com/package/@phyi/sdk) on npm |
| Python SDK | [`phylax-sdk`](https://github.com/praxi-labs/phylax-sdk-python), PyPI release pending |
| MCP server | [`@phyi/mcp`](https://www.npmjs.com/package/@phyi/mcp) on npm |
| Agent runtime gate | [`@phyi/runtime-gate`](https://www.npmjs.com/package/@phyi/runtime-gate) on npm |
| VS Code extension | [`phylax.phylax`](https://marketplace.visualstudio.com/items?itemName=phylax.phylax) on the Marketplace |
| GitHub Action | [`praxi-labs/phylax-action`](https://github.com/praxi-labs/phylax-action) |
| Browser extension | [`praxi-labs/phylax-chrome`](https://github.com/praxi-labs/phylax-chrome/releases/latest), Web Store listing pending |

Docs live at [phyi.dev](https://phyi.dev).
