
import os
import re
import time
import requests


GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-120b"
)

MAX_RETRIES = 5
MAX_WAIT_SECONDS = 300

TOKEN_LIMITS = {
    "director": 700,
    "creative": 900,
    "script": 1800,
    "editor": 1800,
    "fact_check": 1600,
    "audit": 1200,
    "default": 1200
}


def detect_token_limit(system_prompt):

    prompt = str(system_prompt).lower()

    if "chief ai director" in prompt:
        return TOKEN_LIMITS["director"]

    if "creative strategist" in prompt:
        return TOKEN_LIMITS["creative"]

    if "youtube shorts scriptwriter" in prompt:
        return TOKEN_LIMITS["script"]

    if "quality editor" in prompt:
        return TOKEN_LIMITS["editor"]

    if "historical fact-checker" in prompt:
        return TOKEN_LIMITS["fact_check"]

    if "auditor" in prompt:
        return TOKEN_LIMITS["audit"]

    return TOKEN_LIMITS["default"]


def is_daily_limit(message):

    text = str(message).lower()

    daily_patterns = [
        "per day",
        "per-day",
        "daily limit",
        "daily quota",
        "tokens per day",
        "requests per day",
        "tpd",
        "rpd"
    ]

    return any(
        pattern in text
        for pattern in daily_patterns
    )


def parse_wait_time(value):

    if not value:
        return None

    value = str(value).strip().lower()

    try:
        return float(value)
    except ValueError:
        pass

    minutes = re.search(
        r"([0-9.]+)\s*m",
        value
    )

    seconds = re.search(
        r"([0-9.]+)\s*s",
        value
    )

    total = 0

    if minutes:
        total += float(minutes.group(1)) * 60

    if seconds:
        total += float(seconds.group(1))

    if total > 0:
        return total

    return None


def get_retry_delay(response, attempt):

    headers = response.headers

    # 1. Retry-After header

    retry_after = headers.get("Retry-After")

    delay = parse_wait_time(retry_after)

    if delay is not None:
        return delay

    # 2. Groq rate limit reset headers

    reset_headers = [
        "x-ratelimit-reset-requests",
        "x-ratelimit-reset-tokens"
    ]

    for header in reset_headers:

        value = headers.get(header)

        delay = parse_wait_time(value)

        if delay is not None:
            return delay

    # 3. Parse Groq error message

    match = re.search(
        r"try again in\s*([0-9.]+\s*(?:m|s)"
        r"(?:\s*[0-9.]+\s*s)?)",
        response.text,
        re.IGNORECASE
    )

    if match:

        delay = parse_wait_time(match.group(1))

        if delay is not None:
            return delay

    # 4. Exponential fallback

    return min(3 * (2 ** attempt), 60)


def ask_ai(system_prompt, user_prompt):

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is missing!"
        )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    token_limit = detect_token_limit(system_prompt)

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
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
                json=payload,
                timeout=(10, 120)
            )

            # RATE LIMIT HANDLING

            if response.status_code == 429:

                error_text = response.text[:2000]

                if is_daily_limit(error_text):

                    raise RuntimeError(
                        "GROQ DAILY QUOTA EXCEEDED. "
                        "Daily API limit reached. "
                        "Check Groq usage and quota."
                    )

                if attempt == MAX_RETRIES:

                    raise RuntimeError(
                        "Groq rate limit exceeded "
                        "after all retry attempts. "
                        f"Details: {error_text}"
                    )

                wait_time = get_retry_delay(
                    response,
                    attempt
                )

                if wait_time > MAX_WAIT_SECONDS:

                    raise RuntimeError(
                        "Groq requested a long waiting period: "
                        f"{wait_time:.1f} seconds. "
                        "Automatic retry stopped to avoid "
                        "blocking the workflow."
                    )

                print(
                    f"[AI BRAIN] RATE LIMIT DETECTED. "
                    f"Attempt {attempt + 1}/{MAX_RETRIES + 1}. "
                    f"Waiting {wait_time:.1f} seconds."
                )

                time.sleep(wait_time)
                continue

            response.raise_for_status()

            result = response.json()

            choices = result.get("choices", [])

            if not choices:

                raise RuntimeError(
                    "Groq returned no choices."
                )

            message = choices[0].get("message", {})

            content = message.get("content", "")

            finish_reason = choices[0].get(
                "finish_reason",
                "unknown"
            )

            if not isinstance(content, str) or not content.strip():

                if attempt == MAX_RETRIES:

                    raise RuntimeError(
                        "Groq returned an empty response."
                    )

                print(
                    "[AI BRAIN] Empty response. Retrying..."
                )

                time.sleep(min(2 * (attempt + 1), 15))
                continue

            if finish_reason == "length":

                raise RuntimeError(
                    "Groq response was truncated. "
                    f"Token limit: {token_limit}"
                )

            print(
                f"[AI BRAIN] SUCCESS. "
                f"Model: {GROQ_MODEL}. "
                f"Token limit: {token_limit}. "
                f"Finish reason: {finish_reason}"
            )

            return content.strip()

        except requests.exceptions.Timeout:

            if attempt == MAX_RETRIES:

                raise RuntimeError(
                    "Groq API request timed out "
                    "after all retries."
                )

            wait_time = min(2 ** attempt, 30)

            print(
                f"[AI BRAIN] TIMEOUT. "
                f"Retrying in {wait_time}s..."
            )

            time.sleep(wait_time)

        except requests.exceptions.HTTPError as error:

            status = (
                error.response.status_code
                if error.response is not None
                else "UNKNOWN"
            )

            details = (
                error.response.text[:1000]
                if error.response is not None
                else str(error)
            )

            raise RuntimeError(
                f"Groq API HTTP error {status}: {details}"
            )

        except requests.exceptions.RequestException as error:

            if attempt == MAX_RETRIES:

                raise RuntimeError(
                    f"Groq connection failed: {error}"
                )

            wait_time = min(2 ** attempt, 30)

            print(
                f"[AI BRAIN] CONNECTION ERROR. "
                f"Retrying in {wait_time}s..."
            )

            time.sleep(wait_time)

    raise RuntimeError(
        "Groq API failed after all retries."
    )
