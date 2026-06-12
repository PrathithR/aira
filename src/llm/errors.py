class LLMError(Exception):
    """Base for every failure escaping the LLM layer. The Agent catches THIS."""


class LLMTimeoutError(LLMError):
    """Model call exceeded the timeout."""


class LLMAuthError(LLMError):
    """Missing or rejected API key."""


class LLMRateLimitError(LLMError):
    """Provider rate limit hit after retries."""

