"""Structured error hierarchy for the Agent Platform.

All services raise these errors. The gateway translates them into
appropriate GraphQL error responses with consistent error codes.
"""


class AgentPlatformError(Exception):
    """Base error for all platform errors."""

    def __init__(self, message: str, code: str = "INTERNAL_ERROR") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


class NotFoundError(AgentPlatformError):
    """Resource not found (agent, document, session)."""

    def __init__(self, resource: str, resource_id: str) -> None:
        super().__init__(
            message=f"{resource} with id '{resource_id}' not found",
            code="NOT_FOUND",
        )
        self.resource = resource
        self.resource_id = resource_id


class ValidationError(AgentPlatformError):
    """Input validation failed."""

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message=message, code="VALIDATION_ERROR")
        self.field = field


class ServiceUnavailableError(AgentPlatformError):
    """Downstream service is unavailable."""

    def __init__(self, service: str) -> None:
        super().__init__(
            message=f"Service '{service}' is currently unavailable",
            code="SERVICE_UNAVAILABLE",
        )
        self.service = service


class RateLimitError(AgentPlatformError):
    """Rate limit exceeded."""

    def __init__(self, limit: int, window_seconds: int) -> None:
        super().__init__(
            message=f"Rate limit exceeded: {limit} requests per {window_seconds}s",
            code="RATE_LIMIT_EXCEEDED",
        )
        self.limit = limit
        self.window_seconds = window_seconds


class LLMError(AgentPlatformError):
    """LLM inference failed (both primary and fallback)."""

    def __init__(self, message: str = "LLM inference failed") -> None:
        super().__init__(message=message, code="LLM_ERROR")


class AuthenticationError(AgentPlatformError):
    """Authentication failed (invalid or missing token)."""

    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(message=message, code="UNAUTHENTICATED")


class AuthorizationError(AgentPlatformError):
    """Authorization failed (valid token but insufficient permissions)."""

    def __init__(self, message: str = "Insufficient permissions") -> None:
        super().__init__(message=message, code="UNAUTHORIZED")
