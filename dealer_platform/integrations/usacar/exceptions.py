class USACarClientError(Exception):
    """Base exception for USA Car client failures."""


class USACarConfigurationError(USACarClientError):
    """Indicate that the USA Car integration configuration is unusable."""


class USACarAuthenticationError(USACarClientError):
    """Indicate that USA Car rejected the configured credentials."""


class USACarRequestError(USACarClientError):
    """Indicate that a USA Car request failed after retry handling."""


class USACarTransientError(USACarClientError):
    """Indicate an HTTP response that is safe to retry."""


class USACarResponseError(USACarClientError):
    """Indicate that USA Car returned an unexpected response."""
