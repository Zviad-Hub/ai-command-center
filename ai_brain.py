
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


def ask_ai(system_prompt, user_prompt):

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError("GROQ_API_KEY is missing!")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

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
        "max_completion_tokens": 1200
    }

    for attempt in range(MAX_RETRIES + 1):

        try:
            response = requests.post(
                GROQ_API_URL,
                headers=headers,
                json=payload,
                timeout=(10, 90)
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

            content = ""

            if choices:
                content = (
                    choices[0]
                    .get("message", {})
                    .get("content", "")
                )

            if isinstance(content, str) and content.strip():
                return content.strip()

            if attempt == MAX_RETRIES:
                raise RuntimeError(
                    "Groq returned an empty response "
                    "after all retries."
                )

            wait_time = min(2 * (attempt + 1), 15)

            print(
                f"[AI BRAIN] Empty response. "
                f"Retrying in {wait_time}s..."
            )

            time.sleep(wait_time)

        except requests.exceptions.Timeout:

            if attempt == MAX_RETRIES:
                raise RuntimeError("Groq API request timed out.")

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

    raise RuntimeError("Groq API failed after all retries.")
