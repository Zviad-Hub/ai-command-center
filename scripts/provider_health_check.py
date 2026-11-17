#!/usr/bin/env python3
"""Safely check configured AI providers with one tiny request per provider."""

import json
import os
import sys

import requests


GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
TIMEOUT_SECONDS = 12
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
            choices = payload.get("choices", [])
            content = choices[0].get("message", {}).get("content", "") if choices else ""
        except (ValueError, TypeError, IndexError, AttributeError):
            return "INVALID_RESPONSE"
        return "PASS" if isinstance(content, str) and content.strip() else "INVALID_RESPONSE"

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

    post = post_fn or requests.post
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": "Reply with exactly: OK"}
        ],
        token_field: 8,
    }
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
    groq = check_provider(
        "groq",
        GROQ_URL,
        os.getenv("GROQ_API_KEY", "").strip(),
        os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip(),
        "max_completion_tokens",
    )
    gemini = check_provider(
        "gemini",
        GEMINI_URL,
        os.getenv("GEMINI_API_KEY", "").strip(),
        os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip(),
        "max_tokens",
    )

    statuses = (groq["status"], gemini["status"])
    passing = statuses.count("PASS")
    configured = sum(status != "NOT_CONFIGURED" for status in statuses)
    if passing == 2:
        overall = "PASS"
    elif passing == 1:
        overall = "PARTIAL"
    elif configured == 0:
        overall = "NO_PROVIDERS_CONFIGURED"
    else:
        overall = "UNAVAILABLE"

    return {
        "overall_status": overall,
        "providers": [groq, gemini],
        "requests_sent": sum(status != "NOT_CONFIGURED" for status in statuses),
    }


if __name__ == "__main__":
    # A completed diagnostic is a successful workflow run even if an API is down.
    # Provider health is reported explicitly in JSON rather than as a CI failure.
    print(json.dumps(run_health_check(), ensure_ascii=False, sort_keys=True))
    sys.exit(0)
