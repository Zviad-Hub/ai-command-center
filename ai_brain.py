
import os
import requests

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-120b"
)


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

    try:
        response = requests.post(
            GROQ_API_URL,
            headers=headers,
            json=payload,
            timeout=(10, 60)
        )

        response.raise_for_status()

        result = response.json()

        return result["choices"][0]["message"]["content"]

    except requests.exceptions.Timeout:
        raise RuntimeError("Groq API request timed out.")

    except requests.exceptions.HTTPError as error:
        raise RuntimeError(
            f"Groq API HTTP error: {error.response.status_code} "
            f"{error.response.text[:1000]}"
        )

    except requests.exceptions.RequestException as error:
        raise RuntimeError(f"Groq connection error: {error}")
