
import os
import re
import time
import requests


GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-120b"
)

MAX_RETRIES = 4
MAX_LENGTH_RETRIES = 2
MAX_COMPLETION_TOKEN_CAP = int(os.getenv("AI_MAX_COMPLETION_TOKEN_CAP", "65536"))
REQUEST_TIMEOUT = (10, 120)


# ==================================================
# TOKEN LIMITS
# ==================================================

TOKEN_LIMITS = {
    "director": 1200,
    "creative": 1800,
    "script": 3000,
    "editor": 3500,
    "fact_check": 3500,
    "evidence_editor": 3500,
    "audit": 2500,
    "research": 3000,
    "default": 2000
}


def detect_token_limit(system_prompt):

    prompt = str(system_prompt or "").lower()

    if "chief ai director" in prompt:
        return TOKEN_LIMITS["director"]

    if "creative strategist" in prompt:
        return TOKEN_LIMITS["creative"]

    if "historical youtube shorts scriptwriter" in prompt:
        return TOKEN_LIMITS["script"]

    if "quality editor" in prompt:
        return TOKEN_LIMITS["editor"]

    if "fact-checker" in prompt or "fact checker" in prompt:
        return TOKEN_LIMITS["fact_check"]

    if "evidence-based script editor" in prompt:
        return TOKEN_LIMITS["evidence_editor"]

    if "auditor" in prompt:
        return TOKEN_LIMITS["audit"]

    if "research" in prompt:
        return TOKEN_LIMITS["research"]

    return TOKEN_LIMITS["default"]


# ==================================================
# RATE LIMIT UTILITIES
# ==================================================

def is_daily_limit_error(response_text):

    text = str(response_text or "").lower()

    indicators = [
        "daily quota",
        "per day",
        "requests per day",
        "tokens per day",
        "rpd",
        "tpd",
        "daily_limit"
    ]

    return any(item in text for item in indicators)


def _fallback_provider_config():
    """Return a fully configured OpenAI-compatible fallback, or None."""
    url = os.getenv("AI_FALLBACK_API_URL", "").strip()
    key = os.getenv("AI_FALLBACK_API_KEY", "").strip()
    model = os.getenv("AI_FALLBACK_MODEL", "").strip()
    if not (url and key and model):
        return None
    token_field = os.getenv("AI_FALLBACK_TOKEN_FIELD", "max_tokens").strip()
    if token_field not in {"max_tokens", "max_completion_tokens"}:
        raise RuntimeError("AI fallback token field configuration is invalid.")
    return url, key, model, token_field


def _ask_fallback_provider(system_prompt, user_prompt, token_limit, config):
    """Make one bounded request to an explicitly configured compatible provider."""
    url, key, model, token_field = config
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": str(system_prompt)},
            {"role": "user", "content": str(user_prompt)},
        ],
        token_field: token_limit,
    }
    try:
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
    except requests.exceptions.Timeout as error:
        raise RuntimeError("Fallback AI provider timed out; provider details were withheld.") from error
    except requests.exceptions.RequestException as error:
        raise RuntimeError("Fallback AI provider connection failed; provider details were withheld.") from error

    if response.status_code == 429:
        if is_daily_limit_error(response.text[:2000]):
            raise RuntimeError("Fallback AI provider daily quota is exhausted.")
        raise RuntimeError("Fallback AI provider rate limit exceeded; provider details were withheld.")
    if not response.ok:
        raise RuntimeError(
            f"Fallback AI provider HTTP error: {response.status_code}; provider details were withheld."
        )

    try:
        result = response.json()
        choices = result.get("choices", [])
        content = choices[0].get("message", {}).get("content", "") if choices else ""
    except (ValueError, TypeError, IndexError, AttributeError) as error:
        raise RuntimeError("Fallback AI provider returned an invalid response.") from error

    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("Fallback AI provider returned an empty response.")
    if choices[0].get("finish_reason") == "length":
        raise RuntimeError("Fallback AI provider response was truncated; provider details were withheld.")

    usage = result.get("usage", {})
    completion_tokens = usage.get("completion_tokens", "unknown") if isinstance(usage, dict) else "unknown"
    print(
        "[AI BRAIN] Fallback provider response received successfully. "
        f"Token limit: {token_limit}. Completion tokens: {completion_tokens}."
    )
    return content.strip()


def get_retry_wait(response, attempt):

    wait_time = None

    # First: Retry-After header
    retry_after = response.headers.get("Retry-After")

    if retry_after:
        try:
            wait_time = float(retry_after)
        except (ValueError, TypeError):
            wait_time = None

    # Second: Groq error message
    if wait_time is None:

        match = re.search(
            r"try again in ([0-9.]+)s",
            response.text,
            re.IGNORECASE
        )

        if match:
            wait_time = float(match.group(1))

    # Third: exponential backoff
    if wait_time is None:
        wait_time = 3 * (2 ** attempt)

    return min(max(wait_time, 2), 60)


# ==================================================
# MAIN AI REQUEST
# ==================================================

def ask_ai(system_prompt, user_prompt):

    api_key = os.getenv("GROQ_API_KEY")
    fallback_config = _fallback_provider_config()

    if not api_key:
        if fallback_config:
            return _ask_fallback_provider(
                system_prompt, user_prompt,
                min(detect_token_limit(system_prompt), MAX_COMPLETION_TOKEN_CAP),
                fallback_config,
            )
        raise RuntimeError("GROQ_API_KEY is missing and no fallback AI provider is configured.")

    if not str(system_prompt or "").strip():
        raise ValueError("System prompt is empty.")

    if not str(user_prompt or "").strip():
        raise ValueError("User prompt is empty.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    token_limit = min(detect_token_limit(system_prompt), MAX_COMPLETION_TOKEN_CAP)
    length_retries = 0

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {
                "role": "system",
                "content": str(system_prompt)
            },
            {
                "role": "user",
                "content": str(user_prompt)
            }
        ],
        "max_completion_tokens": token_limit,
        "reasoning_effort": "low",
        "include_reasoning": False
    }

    for attempt in range(MAX_RETRIES + 1):

        try:

            response = requests.post(
                GROQ_API_URL,
                headers=headers,
                json=payload.copy(),
                timeout=REQUEST_TIMEOUT
            )

            # ------------------------------------------
            # RATE LIMIT
            # ------------------------------------------

            if response.status_code == 429:

                error_text = response.text[:2000]

                if is_daily_limit_error(error_text):
                    if fallback_config:
                        print("[AI BRAIN] Groq daily quota exhausted; switching to configured fallback provider.")
                        return _ask_fallback_provider(
                            system_prompt, user_prompt, token_limit, fallback_config
                        )
                    raise RuntimeError(
                        "Groq daily quota has been exhausted and no fallback AI provider is configured. "
                        "Wait for the quota reset or configure AI_FALLBACK_API_URL, "
                        "AI_FALLBACK_API_KEY and AI_FALLBACK_MODEL."
                    )

                if attempt >= MAX_RETRIES:
                    raise RuntimeError(
                        "Groq rate limit exceeded after all retries; "
                        "provider details were withheld."
                    )

                wait_time = get_retry_wait(response, attempt)

                print(
                    f"[AI BRAIN] Rate limit reached. "
                    f"Retry {attempt + 1}/{MAX_RETRIES} "
                    f"in {wait_time:.1f} seconds."
                )

                time.sleep(wait_time)
                continue

            # ------------------------------------------
            # TEMPORARY SERVER ERRORS
            # ------------------------------------------

            if response.status_code in (500, 502, 503, 504):

                if attempt >= MAX_RETRIES:
                    raise RuntimeError(
                        f"Groq server error: HTTP {response.status_code}; "
                        "provider details were withheld."
                    )

                wait_time = min(2 ** (attempt + 1), 20)

                print(
                    f"[AI BRAIN] Temporary server error "
                    f"{response.status_code}. "
                    f"Retrying in {wait_time}s..."
                )

                time.sleep(wait_time)
                continue

            # ------------------------------------------
            # OTHER HTTP ERRORS
            # ------------------------------------------

            if not response.ok:
                raise RuntimeError(
                    f"Groq API HTTP error: {response.status_code}; "
                    "provider details were withheld."
                )

            # ------------------------------------------
            # READ RESPONSE
            # ------------------------------------------

            result = response.json()

            choices = result.get("choices", [])

            if not choices:
                raise RuntimeError(
                    "Groq returned no choices."
                )

            choice = choices[0]

            message = choice.get("message", {})
            content = message.get("content", "")

            finish_reason = choice.get(
                "finish_reason",
                "unknown"
            )

            if not isinstance(content, str) or not content.strip():

                if attempt >= MAX_RETRIES:
                    raise RuntimeError(
                        "Groq returned an empty response."
                    )

                wait_time = min(2 ** (attempt + 1), 15)

                print(
                    "[AI BRAIN] Empty response. "
                    f"Retrying in {wait_time}s..."
                )

                time.sleep(wait_time)
                continue

            # ------------------------------------------
            # TRUNCATION CHECK
            # ------------------------------------------

            if finish_reason == "length":

                if (
                    length_retries < MAX_LENGTH_RETRIES
                    and token_limit < MAX_COMPLETION_TOKEN_CAP
                ):
                    previous_limit = token_limit
                    token_limit = min(token_limit * 2, MAX_COMPLETION_TOKEN_CAP)
                    payload["max_completion_tokens"] = token_limit
                    length_retries += 1
                    print(
                        "[AI BRAIN] Response reached its token limit. "
                        f"Retrying with {token_limit} tokens "
                        f"(attempt {length_retries}/{MAX_LENGTH_RETRIES}; "
                        f"previous limit {previous_limit})."
                    )
                    continue

                raise RuntimeError(
                    "Groq response remained truncated after adaptive token-limit retries. "
                    f"Final limit: {token_limit}; cap: {MAX_COMPLETION_TOKEN_CAP}. "
                    "The task may need a shorter output or a larger configured cap."
                )

            # ------------------------------------------
            # SUCCESS
            # ------------------------------------------

            usage = result.get("usage", {})

            completion_tokens = usage.get(
                "completion_tokens",
                "unknown"
            )

            print(
                "[AI BRAIN] Response received successfully. "
                f"Token limit: {token_limit}. "
                f"Completion tokens: {completion_tokens}. "
                f"Finish reason: {finish_reason}."
            )

            return content.strip()

        except requests.exceptions.Timeout:

            if attempt >= MAX_RETRIES:
                raise RuntimeError(
                    "Groq API request timed out after all retries."
                )

            wait_time = min(2 ** (attempt + 1), 20)

            print(
                "[AI BRAIN] Request timed out. "
                f"Retrying in {wait_time}s..."
            )

            time.sleep(wait_time)

        except requests.exceptions.RequestException as error:

            if attempt >= MAX_RETRIES:
                raise RuntimeError(
                    "Groq connection failed after all retries; "
                    "connection details were withheld."
                )

            wait_time = min(2 ** (attempt + 1), 20)

            print(
                "[AI BRAIN] Connection error. "
                f"Retrying in {wait_time}s..."
            )

            time.sleep(wait_time)

    raise RuntimeError(
        "Groq API failed after all retry attempts."
    )
