from typing import Any, Dict, Optional


class PhylaxError(Exception):
    def __init__(
        self,
        message: str,
        status: int = 0,
        code: str = "error",
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code
        self.payload = payload or {}

    def __str__(self) -> str:
        return f"{self.message} (status={self.status}, code={self.code})"


class APIFailure(PhylaxError):
    pass


class APITokenMissing(APIFailure):
    def __init__(self, message: str = "") -> None:
        super().__init__(
            message
            or (
                "A Phylax API token is required. Create one at "
                "https://app.phyi.dev/marketplace/keys, or set PHYLAX_API_TOKEN."
            ),
            status=0,
            code="unauthenticated",
        )


class APIAuthenticationError(APIFailure):
    def __init__(self, message: str = "Token missing, malformed or revoked.", **kwargs: Any) -> None:
        super().__init__(message, status=kwargs.pop("status", 401), code="unauthenticated", **kwargs)


class APIAccessDenied(APIFailure):
    def __init__(self, message: str = "Token lacks a required permission.", **kwargs: Any) -> None:
        super().__init__(message, status=kwargs.pop("status", 403), code="forbidden", **kwargs)


class APIPlanRequired(APIFailure):
    def __init__(
        self,
        message: str = "This capability is not part of the current subscription plan.",
        **kwargs: Any,
    ) -> None:
        super().__init__(message, status=kwargs.pop("status", 402), code="plan_required", **kwargs)


class APIQuotaExceeded(APIFailure):
    def __init__(
        self, message: str = "Plan quota is spent for the current period.", **kwargs: Any
    ) -> None:
        super().__init__(message, status=kwargs.pop("status", 429), code="quota_exceeded", **kwargs)


class APIRateLimited(APIFailure):
    def __init__(self, message: str = "Rate limited.", retry_after: Optional[float] = None, **kwargs: Any) -> None:
        super().__init__(message, status=kwargs.pop("status", 429), code="rate_limited", **kwargs)
        self.retry_after = retry_after


class APIResourceNotFound(APIFailure):
    def __init__(self, message: str = "Resource not found.", **kwargs: Any) -> None:
        super().__init__(message, status=kwargs.pop("status", 404), code="not_found", **kwargs)


class APIInvalidRequest(APIFailure):
    def __init__(self, message: str = "Invalid request.", **kwargs: Any) -> None:
        super().__init__(message, status=kwargs.pop("status", 400), code="invalid_request", **kwargs)


class APIServerError(APIFailure):
    def __init__(self, message: str = "Phylax server error.", **kwargs: Any) -> None:
        super().__init__(message, status=kwargs.pop("status", 500), code="server_error", **kwargs)


class APIConnectionError(APIFailure):
    def __init__(self, message: str = "Could not reach the Phylax API.", **kwargs: Any) -> None:
        super().__init__(message, status=0, code="network_error", **kwargs)


class APITimeout(APIFailure):
    def __init__(self, message: str = "Request timed out.", **kwargs: Any) -> None:
        super().__init__(message, status=0, code="timeout", **kwargs)


STATUS_TO_EXCEPTION = {
    400: APIInvalidRequest,
    401: APIAuthenticationError,
    402: APIPlanRequired,
    403: APIAccessDenied,
    404: APIResourceNotFound,
    429: APIRateLimited,
}


def exception_for_status(status: int, message: str, payload: Optional[Dict[str, Any]] = None) -> APIFailure:
    if status in STATUS_TO_EXCEPTION:
        return STATUS_TO_EXCEPTION[status](message, status=status, payload=payload)
    if status >= 500:
        return APIServerError(message, status=status, payload=payload)
    return APIInvalidRequest(message, status=status, payload=payload)
