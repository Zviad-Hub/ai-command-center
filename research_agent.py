
import os
import requests


TAVILY_URL = "https://api.tavily.com/search"

# წყაროების პრიორიტეტი
TRUSTED_DOMAINS = [
    "archives.gov",
    "loc.gov",
    "nps.gov",
    "si.edu",
    "britannica.com",
    "history.com",
    "edu",
    "gov"
]


def run_research(task, script):

    api_key = os.getenv("TAVILY_API_KEY")

    if not api_key:
        return {
            "status": "ERROR",
            "message": "TAVILY_API_KEY is missing.",
            "sources": []
        }

    # CEO-ს დავალება არის მთავარი თემა.
    # სცენარი გამოიყენება მხოლოდ საკვლევი ფაქტების გამოსავლენად.
    topic = str(task).strip()[:500]
    script_text = str(script).strip()[:1000]

    query = (
        f"Research ONLY this exact historical topic: {topic}. "
        "Find reliable primary sources, government archives, "
        "museums, universities, and established history institutions. "
        "Do not research unrelated topics. "
        "Find evidence that directly supports or contradicts "
        "the historical claims in this topic."
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "query": query,
        "search_depth": "advanced",
        "topic": "general",
        "max_results": 7,
        "include_answer": False,
        "include_raw_content": False
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
            domain = url.lower()

            # წყაროს სანდოობა ავტომატურად დადასტურებული არ არის.
            trusted_candidate = any(
                marker in domain
                for marker in TRUSTED_DOMAINS
            )

            sources.append({
                "title": item.get("title", ""),
                "url": url,
                "content": item.get("content", "")[:1200],
                "score": item.get("score", 0),
                "trusted_candidate": trusted_candidate,
                "verification_status": "NOT_VERIFIED"
            })

        return {
            "status": "COMPLETED" if sources else "NO_RESULTS",
            "original_ceo_topic": topic,
            "script_used_for_context": bool(script_text),
            "source_count": len(sources),
            "sources": sources,
            "warning": (
                "Search results are leads, not verified evidence. "
                "A trusted-domain match does not prove a claim."
            )
        }

    except requests.exceptions.RequestException as error:
        return {
            "status": "ERROR",
            "original_ceo_topic": topic,
            "message": str(error),
            "sources": []
        }
