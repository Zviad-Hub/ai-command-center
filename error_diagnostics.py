"""Safe, non-sensitive failure classification for agent diagnostics."""

import re


def safe_error_code(error):
    """Classify failures without exposing provider messages, prompts, or secrets."""
    message = str(error or "").casefold()

    if "all configured fallback providers failed" in message:
        # Preserve provider names and safe failure classes only.
        details = []
        for provider, prefix in (("gemini", "GEMINI"), ("openrouter", "OPENROUTER")):
            if f"{provider} fallback provider daily quota" in message:
                details.append(f"{prefix}_DAILY_QUOTA")
            elif f"{provider} fallback provider rate limit" in message:
                details.append(f"{prefix}_RATE_LIMIT")
            else:
                match = re.search(rf"{provider} fallback provider http error: (\d{{3}})", message)
                if match:
                    details.append(f"{prefix}_HTTP_{match.group(1)}")
                elif f"{provider} fallback provider timed out" in message:
                    details.append(f"{prefix}_TIMEOUT")
                elif f"{provider} fallback provider connection failed" in message:
                    details.append(f"{prefix}_CONNECTION_ERROR")
                elif f"{provider} fallback provider returned an invalid response" in message:
                    details.append(f"{prefix}_INVALID_RESPONSE")
                elif f"{provider} fallback provider returned an empty response" in message:
                    details.append(f"{prefix}_EMPTY_RESPONSE")
        suffix = "_".join(details)
        return f"PROVIDER_FALLBACK_CHAIN_EXHAUSTED_{suffix}" if suffix else "PROVIDER_FALLBACK_CHAIN_EXHAUSTED"
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
