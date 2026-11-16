
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
        "max_completion_tokens": 900
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
                        "Groq rate limit exceeded after retries. "
                        "Please try again later."
                    )

                wait_time = None

                # Check Retry-After header
                retry_header = response.headers.get("Retry-After")

                if retry_header:
                    try:
                        wait_time = float(retry_header)
                    except ValueError:
                        pass

                # Check Groq error message
                if wait_time is None:
                    match = re.search(
                        r"try again in ([0-9.]+)s",
                        response.text,
                        re.IGNORECASE
                    )

                    if match:
                        wait_time = float(match.group(1))

                # Fallback exponential backoff
                if wait_time is None:
                    wait_time = min(5 * (2 ** attempt), 30)

                wait_time = min(max(wait_time, 1), 60)

                print(
                    f"[AI BRAIN] Rate limit reached. "
                    f"Waiting {wait_time:.1f} seconds..."
                )

                time.sleep(wait_time)
                continue

            response.raise_for_status()

            result = response.json()

            content = result["choices"][0]["message"]["content"]

            if not content:
                raise RuntimeError("Groq returned an empty response.")

            return content

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
            raise RuntimeError(
                f"Groq connection error: {error}"
            )

    raise RuntimeError("Groq API failed after all retries.")
