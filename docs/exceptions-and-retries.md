# Exceptions and retries

## Why exceptions

The TypeScript SDK returns a result union, because unchecked exceptions are easy to forget in TypeScript and the compiler cannot force you to handle one. Python is different. `try` and `except` are how the language reports failure, callers already expect it, and returning an error object would force every call site to unwrap a value that is almost always present.

So this SDK raises.

## The hierarchy

Everything derives from `APIFailure`, which derives from `PhylaxError`. A single handler catches every API failure, and narrower handlers stay available for the cases you want to treat differently.

```python
from phylax import APIFailure

try:
    result = phylax.artifacts.verify("pkg:npm/express@4.18.2")
except APIFailure as error:
    log.warning("verification failed: %s (%s)", error.message, error.code)
```

| Exception | Status | `code` | Meaning |
| --- | --- | --- | --- |
| `APITokenMissing` | none | `unauthenticated` | Raised at construction, before any request. |
| `APIAuthenticationError` | 401 | `unauthenticated` | Token missing, malformed or revoked. |
| `APIPlanRequired` | 402 | `plan_required` | Capability is outside the current subscription. |
| `APIAccessDenied` | 403 | `forbidden` | Token lacks a permission. |
| `APIResourceNotFound` | 404 | `not_found` | No such artifact, policy or webhook. |
| `APIRateLimited` | 429 | `rate_limited` | Too many requests. Carries `retry_after`. |
| `APIQuotaExceeded` | 429 or 402 | `quota_exceeded` | Period quota is spent. |
| `APIInvalidRequest` | other 4xx | `invalid_request` | Malformed request. |
| `APIServerError` | 5xx | `server_error` | Fault on the Phylax side. |
| `APIConnectionError` | none | `network_error` | Never reached the API. |
| `APITimeout` | none | `timeout` | No response within `timeout`. |

Every instance carries `message`, `status`, `code` and `payload`. Branch on `code` rather than on the exception class when you want behaviour that survives a future rename, and branch on the class when you want the clarity of a named handler.

### Rate limited or out of quota

Both arrive as 429 and they call for opposite responses. Being rate limited means you are going too fast, so waiting fixes it. Being out of quota means the period allowance is spent, so waiting does not fix it and only a plan change or the next period will.

The SDK separates them by inspecting the response body, and raises `APIQuotaExceeded` where the body identifies quota exhaustion.

```python
from phylax import APIQuotaExceeded, APIRateLimited

try:
    phylax.artifacts.verify_many(dependencies)
except APIRateLimited as error:
    time.sleep(error.retry_after or 5)
except APIQuotaExceeded:
    notify_owner()
```

Retrying a quota failure in a loop will not succeed and will burn the rest of your rate budget getting there.

## Retries

Retries are automatic. `max_retries` is the total number of attempts, so the default of `3` means one attempt and two retries.

Delay comes from `Retry-After` when the response carries one. Otherwise it is exponential backoff with full jitter, capped at 30 seconds:

```
delay = random() * min(2 ** attempt, 30)
```

Full jitter, rather than a fixed backoff, matters when many workers hit the same limit at once. Without it they all wait the same interval and retry in the same instant, reproducing the burst that caused the limit. Spreading each client randomly across the window breaks that synchronisation.

### What gets retried

| Method | Retried on |
| --- | --- |
| `GET`, `HEAD`, `PUT` | 408, 429, 500, 502, 503, 504, plus transport failures |
| `POST`, `PATCH`, `DELETE` | 408 and 429 only |

The asymmetry is deliberate. A 5xx on a write is ambiguous: the server may have committed the change and then failed to tell you, so replaying it risks creating a second policy or a second webhook. A 408 or a 429 is different, because both mean the request was rejected before the handler ran, which makes a retry safe.

Timeouts and connection failures follow the same rule. They are retried for idempotent methods and raised immediately for writes, since a timeout gives no evidence about whether the server acted.

To retry a write yourself, do it where you can tell whether the first attempt landed.

## Token redaction

An API error body sometimes echoes the credential that was rejected. Left alone, that lands in your logs the moment you print the exception.

Before any exception is raised, the response body is scanned and the token replaced with `***`. Transport error strings are redacted the same way, since a `requests` exception can embed a full URL. Bodies are also truncated to 500 characters so a large HTML error page does not flood a log line.

There is a test that fails if this regresses.

Redaction covers what the SDK raises. If you log the token yourself, or place it in a URL, nothing here can help.

## Timeouts

`timeout` applies to a single attempt, not to the call as a whole. With the defaults, a call that exhausts its retries can take longer than 30 seconds in total. Size it against your own request deadline if you sit behind one.
