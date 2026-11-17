"""Safe, non-sensitive failure classification for agent diagnostics."""

import re


def safe_error_code(error):
    """Classify failures without exposing provider messages, prompts, or secrets."""
    message = str(error or "").casefold()

    if "daily quota" in message or "daily limit" in message or "tokens per day" in message:
        return "PROVIDER_DAILY_QUOTA_EXHAUSTED"
    if "rate limit" in message or "429" in message:
        return "PROVIDER_RATE_LIMIT_EXHAUSTED"
    provider_http = re.search(
        r"(fallback ai provider|groq(?: api)?)(?: http error| server error):?\s*(?:http\s*)?(\d{3})",
        message,
    )
    if provider_http:
        provider = "FALLBACK" if provider_http.group(1).startswith("fallback") else "PRIMARY"
        return f"{provider}_PROVIDER_HTTP_{provider_http.group(2)}"
    if "http error" in message or "http status" in message or "server error" in message:
        return "PROVIDER_HTTP_ERROR"
    if "timed out" in message or "timeout" in message:
        return "PROVIDER_TIMEOUT"
    if "connection failed" in message or "connection error" in message:
        return "PROVIDER_CONNECTION_ERROR"
    if (
        "empty response" in message
        or "empty output" in message
        or "returned empty" in message
        or "no choices" in message
    ):
        return "PROVIDER_EMPTY_RESPONSE"
    if "refused the task" in message or "refusal" in message:
        return "PROVIDER_REFUSAL"
    if "api_key is missing" in message or "api key is missing" in message:
        return "PROVIDER_CONFIGURATION_ERROR"
    if "truncated" in message or "token limit" in message:
        return "PROVIDER_RESPONSE_TRUNCATED"
    if isinstance(error, (ValueError, TypeError)):
        return "INVALID_AGENT_RESPONSE"
    if isinstance(error, RuntimeError):
        return "PROVIDER_REQUEST_FAILED"
    return "AGENT_PROCESSING_ERROR"
