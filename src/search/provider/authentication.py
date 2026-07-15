"""Authentication implementation.

This module provides the ProviderAuthenticatorImpl class that
handles provider authentication abstraction.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .exceptions import AuthenticationError
from .interfaces import Provider, ProviderAuthenticator
from .models import (
    AuthMethod,
    ProviderAuthentication,
    ProviderCapabilities,
)


@dataclass
class AuthState:
    """Internal authentication state tracking."""

    is_authenticated: bool = False
    last_auth_time: datetime | None = None
    token_expires_at: datetime | None = None
    refresh_count: int = 0
    error_count: int = 0


class ProviderAuthenticatorImpl(ProviderAuthenticator):
    """Implementation of ProviderAuthenticator.

    This authenticator handles authentication abstraction for
    different authentication methods.
    """

    def __init__(self) -> None:
        """Initialize the authenticator."""
        self._auth_states: dict[str, AuthState] = {}

    async def authenticate(
        self,
        provider: Provider,
        credentials: ProviderAuthentication,
    ) -> ProviderAuthentication:
        """Authenticate with a provider.

        Args:
            provider: Provider to authenticate with.
            credentials: Credentials to use.

        Returns:
            Updated credentials with auth state.

        Raises:
            AuthenticationError: If authentication fails.
        """
        provider_name = provider.info.name
        state = self._get_or_create_state(provider_name)

        if not self._validate_credentials(credentials):
            state.error_count += 1
            raise AuthenticationError(
                "Invalid credentials",
                provider_name=provider_name,
            )

        if not self._check_auth_method(credentials.method, provider.capabilities):
            state.error_count += 1
            raise AuthenticationError(
                f"Auth method {credentials.method.name} not supported",
                provider_name=provider_name,
            )

        updated_credentials = await provider.authenticate(credentials)

        state.is_authenticated = True
        state.last_auth_time = datetime.now(timezone.utc)
        state.token_expires_at = updated_credentials.token_expires_at
        state.error_count = 0

        self._auth_states[provider_name] = state

        return ProviderAuthentication(
            method=updated_credentials.method,
            credentials=updated_credentials.credentials,
            token=updated_credentials.token,
            token_expires_at=updated_credentials.token_expires_at,
            refresh_token=updated_credentials.refresh_token,
            is_authenticated=True,
            last_auth_attempt=state.last_auth_time,
            auth_errors=state.error_count,
        )

    async def refresh(
        self,
        provider: Provider,
        credentials: ProviderAuthentication,
    ) -> ProviderAuthentication:
        """Refresh authentication.

        Args:
            provider: Provider to refresh auth for.
            credentials: Current credentials.

        Returns:
            Updated credentials with new token.

        Raises:
            AuthenticationError: If refresh fails.
        """
        provider_name = provider.info.name
        state = self._get_or_create_state(provider_name)

        if not credentials.refresh_token:
            state.error_count += 1
            raise AuthenticationError(
                "No refresh token available",
                provider_name=provider_name,
            )

        try:
            updated_credentials = await provider.refresh_auth(credentials)

            state.refresh_count += 1
            state.token_expires_at = updated_credentials.token_expires_at
            state.last_auth_time = datetime.now(timezone.utc)
            state.error_count = 0

            return ProviderAuthentication(
                method=updated_credentials.method,
                credentials=updated_credentials.credentials,
                token=updated_credentials.token,
                token_expires_at=updated_credentials.token_expires_at,
                refresh_token=updated_credentials.refresh_token,
                is_authenticated=True,
                last_auth_attempt=state.last_auth_time,
                auth_errors=state.error_count,
            )
        except Exception as e:
            state.error_count += 1
            raise AuthenticationError(
                f"Auth refresh failed: {e}",
                provider_name=provider_name,
            ) from e

    def is_authenticated(
        self,
        credentials: ProviderAuthentication,
    ) -> bool:
        """Check if credentials are authenticated.

        Args:
            credentials: Credentials to check.

        Returns:
            True if authenticated and not expired.
        """
        if credentials.method == AuthMethod.NONE:
            return True

        if not credentials.is_authenticated:
            return False

        if credentials.is_token_expired():
            return False

        return True

    def get_auth_headers(
        self,
        method: AuthMethod,
        credentials: ProviderAuthentication,
    ) -> dict[str, str]:
        """Get authentication headers.

        Args:
            method: Authentication method.
            credentials: Credentials to use.

        Returns:
            Headers for authentication.
        """
        headers: dict[str, str] = {}

        if method == AuthMethod.NONE:
            return headers

        header_value = credentials.get_header_value()
        if not header_value:
            return headers

        if method == AuthMethod.API_KEY:
            headers["X-API-Key"] = header_value
        elif method == AuthMethod.BEARER:
            headers["Authorization"] = f"Bearer {header_value}"
        elif method == AuthMethod.BASIC:
            headers["Authorization"] = f"Basic {header_value}"
        elif method == AuthMethod.CUSTOM:
            for key, value in credentials.credentials.items():
                if key.startswith("header_"):
                    header_name = key[7:]
                    headers[header_name] = value

        return headers

    def get_auth_state(self, provider_name: str) -> AuthState | None:
        """Get authentication state for a provider.

        Args:
            provider_name: Provider name.

        Returns:
            AuthState if available, None otherwise.
        """
        return self._auth_states.get(provider_name)

    def reset_auth_state(self, provider_name: str | None = None) -> None:
        """Reset authentication state.

        Args:
            provider_name: Specific provider to reset, or None for all.
        """
        if provider_name:
            self._auth_states.pop(provider_name, None)
        else:
            self._auth_states.clear()

    def _get_or_create_state(self, provider_name: str) -> AuthState:
        """Get or create auth state for a provider.

        Args:
            provider_name: Provider name.

        Returns:
            AuthState for the provider.
        """
        if provider_name not in self._auth_states:
            self._auth_states[provider_name] = AuthState()
        return self._auth_states[provider_name]

    def _validate_credentials(
        self,
        credentials: ProviderAuthentication,
    ) -> bool:
        """Validate credentials format.

        Args:
            credentials: Credentials to validate.

        Returns:
            True if credentials are valid format.
        """
        if credentials.method == AuthMethod.NONE:
            return True

        if credentials.method == AuthMethod.API_KEY:
            return bool(credentials.credentials.get("X-API-Key"))

        if credentials.method == AuthMethod.BEARER:
            return bool(credentials.token)

        if credentials.method == AuthMethod.BASIC:
            return bool(credentials.credentials.get("username"))

        if credentials.method == AuthMethod.OAUTH2:
            return bool(credentials.token or credentials.refresh_token)

        return True

    def _check_auth_method(
        self,
        method: AuthMethod,
        capabilities: ProviderCapabilities,
    ) -> bool:
        """Check if auth method is supported.

        Args:
            method: Auth method to check.
            capabilities: Provider capabilities.

        Returns:
            True if method is supported.
        """
        return method in capabilities.supported_auth_methods


class MockAuthenticator(ProviderAuthenticator):
    """Mock authenticator for testing.

    This provides a simple mock that always succeeds
    for testing purposes.
    """

    def __init__(self, always_authenticated: bool = True) -> None:
        """Initialize mock authenticator.

        Args:
            always_authenticated: Whether auth always succeeds.
        """
        self._always_authenticated = always_authenticated

    async def authenticate(
        self,
        provider: Provider,
        credentials: ProviderAuthentication,
    ) -> ProviderAuthentication:
        """Mock authentication.

        Args:
            provider: Provider (unused).
            credentials: Credentials (unused).

        Returns:
            Mock authenticated credentials.
        """
        if not self._always_authenticated:
            raise AuthenticationError("Mock auth failure")

        return ProviderAuthentication(
            method=credentials.method,
            credentials=credentials.credentials,
            token="mock-token-" + credentials.method.name,
            token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            is_authenticated=True,
            last_auth_attempt=datetime.now(timezone.utc),
        )

    async def refresh(
        self,
        provider: Provider,
        credentials: ProviderAuthentication,
    ) -> ProviderAuthentication:
        """Mock auth refresh.

        Args:
            provider: Provider (unused).
            credentials: Current credentials.

        Returns:
            New mock credentials.
        """
        return ProviderAuthentication(
            method=credentials.method,
            credentials=credentials.credentials,
            token="mock-token-refreshed",
            token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            is_authenticated=True,
            last_auth_attempt=datetime.now(timezone.utc),
        )

    def is_authenticated(
        self,
        credentials: ProviderAuthentication,
    ) -> bool:
        """Check mock authentication state.

        Args:
            credentials: Credentials to check.

        Returns:
            Always returns configured value.
        """
        return self._always_authenticated

    def get_auth_headers(
        self,
        method: AuthMethod,
        credentials: ProviderAuthentication,
    ) -> dict[str, str]:
        """Get mock auth headers.

        Args:
            method: Auth method.
            credentials: Credentials.

        Returns:
            Mock headers.
        """
        if method == AuthMethod.API_KEY:
            return {"X-API-Key": "mock-api-key"}
        if method == AuthMethod.BEARER:
            return {"Authorization": "Bearer mock-token"}
        return {}
