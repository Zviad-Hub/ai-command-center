
import os
import requests
from urllib.parse import urlparse


TAVILY_URL = "https://api.tavily.com/search"

TRUSTED_DOMAINS = [
    "nps.gov",
    "archives.gov",
    "loc.gov",
    "si.edu",
    "britannica.com",
    "history.ncdcr.gov",
    "virginia.edu",
    "unc.edu",
    "jstor.org",
    "archive.org"
]


def is_trusted_domain(url):
    try:
        host = urlparse(url).hostname or ""
        host = host.lower().removeprefix("www.")

        return any(
            host == domain or host.endswith("." + domain)
            for domain in TRUSTED_DOMAINS
        )

    except Exception:
        return False


def run_research(task, script):

    api_key = os.getenv("TAVILY_API_KEY")

    if not api_key:
        return {
            "status": "ERROR",
            "message": "TAVILY_API_KEY is missing.",
            "sources": []
        }

    topic = str(task).strip()[:500]

    # CEO-ს თავდაპირველი თემა უცვლელია.
    query = (
        '"Roanoke Lost Colony" '
        '"John White" 1587 1590 '
        'historical records archaeology '
        'National Park Service archives university'
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "query": query,
        "search_depth": "advanced",
        "topic": "general",
        "max_results": 15,
        "include_answer": False,
        "include_raw_content": False,
        "include_domains": TRUSTED_DOMAINS
    }

    try:
        response = requests.post(
            TAVILY_URL,
            headers=headers,
            json=payload,
            timeout=45
        )

        response.raise_for_status()
        data = response.json()

        sources = []

        for item in data.get("results", []):

            url = item.get("url", "")

            if not is_trusted_domain(url):
                continue

            sources.append({
                "title": item.get("title", ""),
                "url": url,
                "content": item.get("content", "")[:1500],
                "score": item.get("score", 0),
                "trusted_candidate": True,
                "verification_status": "NOT_VERIFIED"
            })

        return {
            "status": "COMPLETED" if sources else "NO_RESULTS",
            "original_ceo_topic": topic,
            "query": query,
            "source_count": len(sources),
            "sources": sources,
            "warning": (
                "Sources are candidates only. "
                "Every historical claim requires direct evidence."
            )
        }

    except requests.exceptions.RequestException as error:
        return {
            "status": "ERROR",
            "original_ceo_topic": topic,
            "message": str(error),
            "sources": []
        }
