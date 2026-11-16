
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

# ინდივიდუალური ლიმიტები თითოეული ტიპის სამუშაოსთვის
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


def ask_ai(system_prompt, user_prompt):

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError("GROQ_API_KEY is missing!")

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
        "max_completion_tokens": token_limit
    }

    for attempt in range(MAX_RETRIES + 1):

        try:

            response = requests.post(
                GROQ_API_URL,
                headers=headers,
                json=payload,
                timeout=(10, 120)
            )

            if response.status_code == 429:

                if attempt == MAX_RETRIES:
                    raise RuntimeError(
                        "Groq rate limit exceeded after retries."
                    )

                wait_time = None

                retry_header = response.headers.get("Retry-After")

                if retry_header:
                    try:
                        wait_time = float(retry_header)
                    except ValueError:
                        pass

                if wait_time is None:

                    match = re.search(
                        r"try again in ([0-9.]+)s",
                        response.text,
                        re.IGNORECASE
                    )

                    if match:
                        wait_time = float(match.group(1))

                if wait_time is None:
                    wait_time = 3 * (2 ** attempt)

                wait_time = min(max(wait_time, 2), 60)

                print(
                    f"[AI BRAIN] Rate limit. "
                    f"Retrying in {wait_time:.1f}s..."
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

                time.sleep(min(2 * (attempt + 1), 15))
                continue

            if finish_reason == "length":

                print(
                    "[AI BRAIN] WARNING: Response reached "
                    "the token limit and may be incomplete."
                )

                # Do not silently treat truncated output as complete.
                raise RuntimeError(
                    "Groq response was truncated by token limit. "
                    f"Limit: {token_limit}"
                )

            print(
                f"[AI BRAIN] Response received. "
                f"Tokens limit: {token_limit}, "
                f"Finish reason: {finish_reason}"
            )

            return content.strip()

        except requests.exceptions.Timeout:

            if attempt == MAX_RETRIES:
                raise RuntimeError(
                    "Groq API request timed out."
                )

            time.sleep(min(2 ** attempt, 15))

        except requests.exceptions.HTTPError as error:

            raise RuntimeError(
                f"Groq API HTTP error: "
                f"{error.response.status_code} "
                f"{error.response.text[:1000]}"
            )

        except requests.exceptions.RequestException as error:

            if attempt == MAX_RETRIES:
                raise RuntimeError(
                    f"Groq connection error: {error}"
                )

            time.sleep(min(2 ** attempt, 15))

    raise RuntimeError(
        "Groq API failed after all retries."
    )
