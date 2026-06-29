from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any, TypeAlias, cast

import httpx
from tenacity import (
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from dealer_platform.integrations.models import USACarIntegrationConfig
from dealer_platform.integrations.usacar.exceptions import (
    USACarAuthenticationError,
    USACarConfigurationError,
    USACarRequestError,
    USACarResponseError,
    USACarTransientError,
)

USACarRecord: TypeAlias = dict[str, Any]

RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}
RETRYABLE_EXCEPTIONS = (
    httpx.TimeoutException,
    httpx.NetworkError,
    httpx.RemoteProtocolError,
)
RETRYABLE_CLIENT_EXCEPTIONS = (
    *RETRYABLE_EXCEPTIONS,
    USACarTransientError,
)


class USACarClient:
    """Authenticate with USA Car and retrieve its inventory records."""

    auth_path = "v1/auth/token/"
    inventory_path = "v1/inventory/"

    def __init__(
        self,
        config: USACarIntegrationConfig,
        *,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        max_attempts: int = 3,
        backoff_factor: float = 0.25,
        backoff_max: float = 2.0,
        backoff_jitter: float = 0.25,
        timeout: float = 10.0,
    ) -> None:
        """Initialize a client from a USA Car integration configuration."""
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if backoff_factor < 0:
            raise ValueError("backoff_factor cannot be negative")
        if backoff_max < 0:
            raise ValueError("backoff_max cannot be negative")
        if backoff_jitter < 0:
            raise ValueError("backoff_jitter cannot be negative")

        self.config = config
        self.max_attempts = max_attempts
        self._retrying = Retrying(
            sleep=sleep,
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential_jitter(
                initial=backoff_factor,
                max=backoff_max,
                jitter=backoff_jitter,
            ),
            retry=retry_if_exception_type(RETRYABLE_CLIENT_EXCEPTIONS),
            reraise=True,
        )
        self._http = httpx.Client(
            base_url=f"{config.base_url.rstrip('/')}/",
            timeout=timeout,
            transport=transport,
        )

    def __enter__(self) -> USACarClient:
        """Return this client for context-manager usage."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object | None,
    ) -> None:
        """Close the HTTP connection pool when leaving a context."""
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._http.close()

    def fetch_inventory(self) -> list[USACarRecord]:
        """Authenticate and return every page of USA Car inventory."""
        if not self.config.is_active:
            raise USACarConfigurationError("USA Car integration is inactive.")

        access_token = self._authenticate()
        records: list[USACarRecord] = []
        cursor: str | None = None
        seen_cursors: set[str] = set()

        while True:
            params = {"cursor": cursor} if cursor is not None else None
            response = self._request(
                "GET",
                self.inventory_path,
                headers={"Authorization": f"Bearer {access_token}"},
                params=params,
            )
            self._raise_for_status(response)
            payload = self._json_object(response)
            records.extend(self._inventory_records(payload))

            next_cursor = payload.get("next_cursor")
            if next_cursor is None:
                return records
            if not isinstance(next_cursor, str) or not next_cursor:
                raise USACarResponseError(
                    "USA Car returned an invalid pagination cursor."
                )
            if next_cursor in seen_cursors:
                raise USACarResponseError(
                    "USA Car returned a repeated pagination cursor."
                )

            seen_cursors.add(next_cursor)
            cursor = next_cursor

    def _authenticate(self) -> str:
        """Exchange configured credentials for a USA Car access token."""
        response = self._request(
            "POST",
            self.auth_path,
            json={
                "login": self.config.login,
                "password": self.config.password,
            },
        )
        if response.status_code in {401, 403}:
            raise USACarAuthenticationError(
                "USA Car rejected the configured credentials."
            )

        self._raise_for_status(response)
        payload = self._json_object(response)
        access_token = payload.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise USACarResponseError(
                "USA Car authentication response has no access token."
            )
        return access_token

    def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Send one request using the configured Tenacity retry policy."""
        try:
            response = self._retrying(
                self._send_once,
                method,
                path,
                kwargs,
            )
        except RETRYABLE_CLIENT_EXCEPTIONS as error:
            raise USACarRequestError(
                "USA Car request failed after "
                f"{self.max_attempts} attempts."
            ) from error
        return cast(httpx.Response, response)

    def _send_once(
        self,
        method: str,
        path: str,
        kwargs: dict[str, Any],
    ) -> httpx.Response:
        """Send one HTTP attempt and classify transient status responses."""
        response = self._http.request(method, path, **kwargs)
        if response.status_code in RETRYABLE_STATUS_CODES:
            raise USACarTransientError(
                f"USA Car returned transient status {response.status_code}."
            )
        return response

    def _raise_for_status(self, response: httpx.Response) -> None:
        """Raise a safe client error for a non-successful response."""
        if not response.is_success:
            raise USACarRequestError(
                f"USA Car returned status {response.status_code}."
            )

    def _json_object(self, response: httpx.Response) -> dict[str, Any]:
        """Decode a response and require a JSON object at its root."""
        try:
            payload = response.json()
        except ValueError as error:
            raise USACarResponseError(
                "USA Car returned invalid JSON."
            ) from error

        if not isinstance(payload, dict):
            raise USACarResponseError(
                "USA Car response must contain a JSON object."
            )
        return cast(dict[str, Any], payload)

    def _inventory_records(
        self,
        payload: dict[str, Any],
    ) -> list[USACarRecord]:
        """Extract and validate provider records from an inventory page."""
        inventory = payload.get("inventory")
        if not isinstance(inventory, list):
            raise USACarResponseError(
                "USA Car response has no inventory list."
            )
        if not all(isinstance(record, dict) for record in inventory):
            raise USACarResponseError(
                "USA Car inventory contains an invalid record."
            )
        return cast(list[USACarRecord], inventory)
