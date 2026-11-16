
import os
import requests

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "llama-3.3-70b-versatile"
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
        "temperature": 0.2,
        "max_tokens": 1200
    }

    try:
        response = requests.post(
            GROQ_API_URL,
            headers=headers,
            json=payload,
            timeout=(10, 45)
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


if __name__ == "__main__":
    answer = ask_ai(
        "You are the AI Director of a professional AI organization.",
        "Introduce yourself in Georgian and explain your role."
    )

    print("\nAI DIRECTOR RESPONSE:\n")
    print(answer)
