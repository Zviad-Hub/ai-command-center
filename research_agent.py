
import os
import requests


TAVILY_URL = "https://api.tavily.com/search"


def run_research(task, script):

    api_key = os.getenv("TAVILY_API_KEY")

    if not api_key:
        return {
            "status": "ERROR",
            "message": "TAVILY_API_KEY is missing.",
            "sources": []
        }

    query = f"""
    Historical fact checking:
    Topic: {task[:400]}
    Script claims: {script[:1200]}

    Find reliable historical sources, primary documents,
    museums, universities and government archives.
    """

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "query": query,
        "search_depth": "basic",
        "topic": "general",
        "max_results": 5,
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
            sources.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "content": item.get("content", ""),
                "score": item.get("score", 0)
            })

        return {
            "status": "COMPLETED" if sources else "NO_RESULTS",
            "query": query.strip(),
            "source_count": len(sources),
            "sources": sources
        }

    except requests.exceptions.RequestException as error:
        return {
            "status": "ERROR",
            "message": str(error),
            "sources": []
        }
