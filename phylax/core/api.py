import random
import time
from typing import Any

import requests

from phylax.exceptions import (
    APIConnectionError,
    APIQuotaExceeded,
    APIRateLimited,
    APITimeout,
    exception_for_status,
)
from phylax.version import __version__

DEFAULT_BASE_URL = "https://api.phyi.dev"
DEFAULT_TIMEOUT = 30
DEFAULT_MAX_RETRIES = 3
MAX_BACKOFF_SECONDS = 30

IDEMPOTENT_METHODS = frozenset({"GET", "HEAD", "PUT"})
RETRYABLE_IDEMPOTENT = frozenset({408, 429, 500, 502, 503, 504})
RETRYABLE_UNSAFE = frozenset({408, 429})


def is_retryable(method: str, status: int) -> bool:
    if method.upper() in IDEMPOTENT_METHODS:
        return status in RETRYABLE_IDEMPOTENT
    return status in RETRYABLE_UNSAFE


def retry_delay(attempt: int, retry_after: str | None, rand: Any = random.random) -> float:
    if retry_after:
        try:
            return min(float(retry_after), MAX_BACKOFF_SECONDS)
        except (TypeError, ValueError):
            pass
    ceiling = min(2**attempt, MAX_BACKOFF_SECONDS)
    return rand() * ceiling


def redact(value: str, token: str | None) -> str:
    if not token or len(token) < 8:
        return value
    return value.replace(token, "***")


class API:
    def __init__(
        self,
        api_token: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        user_agent: str | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self.api_token = api_token
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = session or requests.Session()

        agent = f"phylax-python/{__version__}"
        self.user_agent = f"{user_agent} {agent}" if user_agent else agent

    def _headers(self, has_body: bool) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_token}",
            "User-Agent": self.user_agent,
        }
        if has_body:
            headers["Content-Type"] = "application/json"
        return headers

    def request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
    ) -> Any:
        url = f"{self.base_url}{path}"
        clean_params = {k: v for k, v in (params or {}).items() if v is not None}
        method = method.upper()

        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                response = self.session.request(
                    method,
                    url,
                    params=clean_params or None,
                    json=json,
                    headers=self._headers(json is not None),
                    timeout=self.timeout,
                )
            except requests.Timeout as exc:
                last_error = APITimeout(f"Request timed out after {self.timeout}s")
                if method not in IDEMPOTENT_METHODS or attempt >= self.max_retries - 1:
                    raise last_error from exc
                time.sleep(retry_delay(attempt, None))
                continue
            except requests.RequestException as exc:
                last_error = APIConnectionError(redact(str(exc), self.api_token))
                if method not in IDEMPOTENT_METHODS or attempt >= self.max_retries - 1:
                    raise last_error from exc
                time.sleep(retry_delay(attempt, None))
                continue

            if response.ok:
                if not response.content:
                    return None
                try:
                    return response.json()
                except ValueError:
                    return response.text

            body = redact(response.text or "", self.api_token)[:500]

            if is_retryable(method, response.status_code) and attempt < self.max_retries - 1:
                time.sleep(retry_delay(attempt, response.headers.get("Retry-After")))
                continue

            raise self._error_for(response, body)

        if last_error:
            raise last_error
        raise APIConnectionError("Request failed")

    def _error_for(self, response: requests.Response, body: str) -> Exception:
        status = response.status_code
        payload: dict[str, Any] = {"body": body}

        if status == 429:
            retry_after = response.headers.get("Retry-After")
            if "quota" in body.lower():
                return APIQuotaExceeded(f"Quota exhausted. {body}", payload=payload)
            return APIRateLimited(
                f"Rate limited. {body}",
                retry_after=float(retry_after) if retry_after else None,
                payload=payload,
            )

        return exception_for_status(status, f"HTTP {status}. {body}".strip(), payload)

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return self.request("GET", path, params=params)

    def post(self, path: str, json: Any | None = None, params: dict[str, Any] | None = None) -> Any:
        return self.request("POST", path, params=params, json=json)

    def patch(self, path: str, json: Any | None = None) -> Any:
        return self.request("PATCH", path, json=json)

    def delete(self, path: str) -> Any:
        return self.request("DELETE", path)
