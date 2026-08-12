import hashlib
import hmac
import time
from typing import NamedTuple, Optional, Union


class SignatureResult(NamedTuple):
    valid: bool
    reason: str = ""


def verify_signature(
    raw_body: Union[str, bytes],
    signature: Optional[str],
    timestamp: Optional[Union[str, int, float]],
    secret: str,
    tolerance_seconds: int = 300,
    now: Optional[float] = None,
) -> SignatureResult:
    if not signature:
        return SignatureResult(False, "Missing signature header")
    if timestamp is None or timestamp == "":
        return SignatureResult(False, "Missing timestamp header")

    try:
        ts = float(timestamp)
    except (TypeError, ValueError):
        return SignatureResult(False, "Malformed timestamp header")

    current = time.time() if now is None else now
    skew = abs(current - ts)
    if skew > tolerance_seconds:
        return SignatureResult(
            False,
            f"Timestamp outside tolerance ({int(skew)}s > {tolerance_seconds}s)",
        )

    body = raw_body.encode("utf-8") if isinstance(raw_body, str) else raw_body
    prefix = f"{int(ts)}.".encode("utf-8")

    expected = "sha256=" + hmac.new(
        secret.encode("utf-8"), prefix + body, hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        return SignatureResult(False, "Signature mismatch")

    return SignatureResult(True)
