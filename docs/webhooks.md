# Webhooks

Phylax delivers events to an HTTPS endpoint you control. Because that endpoint is public, the only thing separating a real delivery from a forged one is the signature, so verify every request before you act on it.

## The signature

Each delivery carries two headers.

| Header | Contents |
| --- | --- |
| `X-Phylax-Signature` | `sha256=` followed by a hex HMAC digest. |
| `X-Phylax-Timestamp` | Unix seconds at the moment of signing. |

The digest is computed over the timestamp and the body joined by a period:

```
signature = "sha256=" + hmac_sha256(secret, f"{timestamp}.{raw_body}")
```

The timestamp is inside the signed material rather than beside it. If it were only a header, an attacker could replay a captured request with a fresh timestamp and the signature would still verify. Signing them together means changing the timestamp invalidates the digest.

## Verifying

```python
from phylax import verify_signature

result = verify_signature(
    raw_body=request.get_data(),
    signature=request.headers.get("X-Phylax-Signature"),
    timestamp=request.headers.get("X-Phylax-Timestamp"),
    secret=os.environ["PHYLAX_WEBHOOK_SECRET"],
)

if not result.valid:
    abort(401, result.reason)
```

`SignatureResult` is a named tuple of `valid` and `reason`. The reason is for your logs. Do not return it to the caller, since it tells whoever is probing you exactly which part of the forgery to fix.

| Reason | Cause |
| --- | --- |
| `Missing signature header` | No `X-Phylax-Signature`. |
| `Missing timestamp header` | No `X-Phylax-Timestamp`. |
| `Malformed timestamp header` | Timestamp is not a number. |
| `Timestamp outside tolerance` | Older or further ahead than `tolerance_seconds`. |
| `Signature mismatch` | Digest does not match. |

## Pass the raw bytes

`raw_body` must be the bytes as received. This is the single most common way a correct integration still fails.

Any middleware that parses JSON and re-serialises it can reorder keys, change spacing or normalise unicode. The result is semantically identical and byte for byte different, and HMAC only sees bytes. The signature then fails on a delivery that was perfectly valid.

| Framework | Raw body |
| --- | --- |
| Flask | `request.get_data()` |
| Django | `request.body` |
| FastAPI | `await request.body()` |
| Starlette | `await request.body()` |

Read the raw body before anything else touches the request.

### FastAPI

```python
from fastapi import FastAPI, HTTPException, Request
from phylax import verify_signature

app = FastAPI()


@app.post("/webhooks/phylax")
async def receive(request: Request):
    raw = await request.body()

    result = verify_signature(
        raw_body=raw,
        signature=request.headers.get("X-Phylax-Signature"),
        timestamp=request.headers.get("X-Phylax-Timestamp"),
        secret=os.environ["PHYLAX_WEBHOOK_SECRET"],
    )

    if not result.valid:
        raise HTTPException(status_code=401)

    event = json.loads(raw)
    await queue.put(event)

    return {"ok": True}
```

Parse the body only after the signature checks out. Parsing first means unverified input has already reached your deserialiser.

## The replay window

`tolerance_seconds` defaults to 300. A delivery signed more than five minutes ago is rejected even when the signature is valid, which bounds how long a captured request stays useful to someone who intercepted it.

The comparison is absolute, so a timestamp far in the future is rejected too.

Widening the window past a few minutes gives back the protection it exists for. If deliveries fail on tolerance, the cause is almost always clock drift on the receiver, and NTP is the fix rather than a larger tolerance.

For testing, pass `now` to pin the current time:

```python
verify_signature(..., now=1_700_000_000.0)
```

## Constant time comparison

The comparison uses `hmac.compare_digest`, which takes the same time whether the mismatch is in the first byte or the last.

A plain `==` returns as soon as it finds a difference. That timing difference is measurable across enough requests, and it lets an attacker recover a valid digest one byte at a time without ever knowing the secret. Never compare a signature with `==`.

## Responding

Return 2xx as soon as the signature verifies and the event is safely queued. Do the real work afterwards.

Deliveries are retried on non 2xx responses, so slow handling turns into duplicate deliveries, and a handler that does its work inline turns a downstream slowdown into a retry storm.

Design handlers to be idempotent. At least once delivery means the same event can arrive twice, and network faults make that a certainty over a long enough period rather than an edge case. Key on the event identifier and ignore one you have already processed.

## Secrets

Create a webhook with your own secret, or let one be generated:

```python
hook = phylax.webhooks.create(
    url="https://example.com/webhooks/phylax",
    events=["artifact.verified", "policy.violated"],
)

store_secret(hook["secret"])
```

A generated secret is returned once, at creation, and cannot be retrieved afterwards. Store it then or rotate the webhook.

To rotate, create a second webhook, accept both secrets while deliveries drain, then delete the first. Updating a secret in place means every delivery already in flight fails verification.
