#!/usr/bin/env python3
"""Safely check configured AI providers with one tiny request per provider."""

import json
import os
import sys
from urllib.parse import urlsplit

import requests


GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
TIMEOUT_SECONDS = 12
HEALTH_CHECK_TOKEN_LIMIT = 64
DAILY_QUOTA_MARKERS = (
    "daily quota",
    "per day",
    "requests per day",
    "tokens per day",
    "daily_limit",
    "resource_exhausted",
)


def _classify_response(response):
    status = response.status_code
    if 200 <= status < 300:
        try:
            payload = response.json()
        except (ValueError, TypeError):
            return "INVALID_JSON"
        if not isinstance(payload, dict):
            return "INVALID_JSON_SHAPE"

        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            return "NO_CHOICES"

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            return "INVALID_CHOICE"
        message = first_choice.get("message")
        if not isinstance(message, dict):
            return "INVALID_MESSAGE"

        content = message.get("content")
        if not isinstance(content, str):
            return "NON_TEXT_CONTENT"
        if not content.strip():
            if first_choice.get("finish_reason") == "length":
                return "TRUNCATED_RESPONSE"
            return "EMPTY_CONTENT"
        return "PASS"

    if status in (401, 403):
        return "AUTH_ERROR"
    if status == 429:
        # Inspect only in memory; never print provider response bodies.
        try:
            body = response.text[:4000].lower()
        except Exception:
            body = ""
        if any(marker in body for marker in DAILY_QUOTA_MARKERS):
            return "DAILY_QUOTA"
        return "RATE_LIMIT"
    if status == 503:
        return "HTTP_503"
    if status in (500, 502, 504):
        return f"HTTP_{status}"
    return f"HTTP_ERROR_{status}"


def check_provider(name, url, api_key, model, token_field, post_fn=None):
    if not api_key:
        return {"provider": name, "status": "NOT_CONFIGURED"}

    parsed_url = urlsplit(str(url or ""))
    if parsed_url.scheme != "https" or not parsed_url.netloc:
        return {"provider": name, "status": "INVALID_CONFIGURATION"}

    post = post_fn or requests.post
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": "Reply with exactly: OK"}
        ],
        token_field: HEALTH_CHECK_TOKEN_LIMIT,
    }
    # Match the production Groq request's low-reasoning configuration. A tiny
    # 8-token budget can be consumed by reasoning before a visible answer exists.
    if name == "groq":
        payload["reasoning_effort"] = "low"
        payload["include_reasoning"] = False

    try:
        response = post(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=TIMEOUT_SECONDS,
        )
        status = _classify_response(response)
    except requests.exceptions.Timeout:
        status = "TIMEOUT"
    except requests.exceptions.RequestException:
        status = "CONNECTION_ERROR"
    except Exception:
        # Fail closed without exposing exception text, headers, or credentials.
        status = "UNAVAILABLE"

    return {"provider": name, "status": status}


def run_health_check():
    providers = [
        check_provider(
            "groq",
            GROQ_URL,
            os.getenv("GROQ_API_KEY", "").strip(),
            os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip(),
            "max_completion_tokens",
        ),
        check_provider(
            "gemini",
            GEMINI_URL,
            os.getenv("GEMINI_API_KEY", "").strip(),
            os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip(),
            "max_tokens",
        ),
    ]

    secondary_url = os.getenv("AI_FALLBACK_API_URL", "").strip()
    secondary_key = os.getenv("AI_FALLBACK_API_KEY", "").strip()
    secondary_model = os.getenv("AI_FALLBACK_MODEL", "").strip()
    if secondary_url and secondary_key and secondary_model:
        host = urlsplit(secondary_url).netloc.lower()
        secondary_name = "openrouter" if "openrouter.ai" in host else "secondary"
        providers.append(check_provider(
            secondary_name,
            secondary_url,
            secondary_key,
            secondary_model,
            os.getenv("AI_FALLBACK_TOKEN_FIELD", "max_tokens").strip(),
        ))

    configured = [item for item in providers if item["status"] != "NOT_CONFIGURED"]
    passing = sum(item["status"] == "PASS" for item in configured)
    if configured and passing == len(configured):
        overall = "PASS"
    elif passing:
        overall = "PARTIAL"
    elif not configured:
        overall = "NO_PROVIDERS_CONFIGURED"
    else:
        overall = "UNAVAILABLE"

    return {
        "overall_status": overall,
        "providers": providers,
        "requests_sent": len(configured),
    }

if __name__ == "__main__":
    # A completed diagnostic is a successful workflow run even if an API is down.
    # Provider health is reported explicitly in JSON rather than as a CI failure.
    print(json.dumps(run_health_check(), ensure_ascii=False, sort_keys=True))
    sys.exit(0)
