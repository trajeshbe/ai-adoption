"""JWT authentication utilities.

Stub implementation for development. Replace with OIDC/OAuth2 provider
integration (e.g., Auth0, Keycloak) for production.
"""

from datetime import datetime, timedelta, timezone

import jwt
from pydantic import BaseModel


class TokenPayload(BaseModel):
    """Decoded JWT token payload."""

    sub: str
    exp: datetime
    iat: datetime
    roles: list[str] = []


def create_token(
    subject: str,
    secret: str,
    algorithm: str = "HS256",
    expires_delta: timedelta = timedelta(hours=24),
    roles: list[str] | None = None,
) -> str:
    """Create a JWT token for development/testing."""
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + expires_delta,
        "roles": roles or ["user"],
    }
    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_token(
    token: str,
    secret: str,
    algorithm: str = "HS256",
) -> TokenPayload:
    """Decode and validate a JWT token.

    Raises:
        jwt.ExpiredSignatureError: Token has expired.
        jwt.InvalidTokenError: Token is invalid.
    """
    payload = jwt.decode(token, secret, algorithms=[algorithm])
    return TokenPayload(**payload)
