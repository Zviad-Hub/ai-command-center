
import os
import re
import requests

from urllib.parse import urlparse


TAVILY_URL = "https://api.tavily.com/search"

MAX_RESULTS = 15
REQUEST_TIMEOUT = 90
MAX_CONTENT_LENGTH = 1500


# ==================================================
# PREFERRED SOURCE DOMAINS
# These are preferences, NOT proof of truth.
# ==================================================

PREFERRED_DOMAINS = [
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


# ==================================================
# DOMAIN UTILITIES
# ==================================================

def get_domain(url):

    try:
        host = urlparse(url).hostname or ""
        return host.lower().removeprefix("www.")

    except Exception:
        return ""


def is_trusted_domain(url):

    host = get_domain(url)

    return any(
        host == domain or host.endswith("." + domain)
        for domain in PREFERRED_DOMAINS
    )


# ==================================================
# TOPIC EXTRACTION
# ==================================================

def extract_topic(task, script=None):

    task_text = str(task or "").strip()

    if not task_text:
        raise ValueError("CEO task is empty.")

    patterns = [
        r"(?im)^\s*EXACT TOPIC\s*:\s*(.+?)\s*$",
        r"(?im)^\s*TOPIC\s*:\s*(.+?)\s*$",
        r"(?i)\b(?:only topic is|exact topic is)\s+(.+?)(?:[.!?\n]|$)",
        r"(?i)\babout\s+(.+?)(?:[.!?\n]|$)",
        r"(?i)შესახებ\s+(.+?)(?:[.!?\n]|$)",
        r"(?i)თემა\s*[:：]\s*(.+?)(?:[.!?\n]|$)"
    ]

    for pattern in patterns:

        match = re.search(pattern, task_text)

        if match:

            topic = match.group(1).strip()

            topic = topic.strip(
                " \t\r\n\"'“”‘’"
            )

            if topic:
                return topic[:300]

    # Try extracting the topic from an existing script.

    script_text = str(script or "").strip()

    if script_text:

        for pattern in patterns:

            match = re.search(pattern, script_text)

            if match:

                topic = match.group(1).strip()

                if topic:
                    return topic[:300]

    # Safe fallback: use the original task.
    # Never silently replace it with another topic.

    return task_text[:350]


# ==================================================
# RESEARCH QUERY BUILDER
# ==================================================

def build_research_query(task, script=None):

    topic = extract_topic(task, script)

    query = (
        f"{topic} "
        "reliable sources authoritative records "
        "official documentation primary evidence"
    )

    return topic, query[:500]


# ==================================================
# SOURCE CONTENT UTILITIES
# ==================================================

def extract_source_content(item):

    raw_content = item.get("raw_content")

    if isinstance(raw_content, str) and raw_content.strip():

        return (
            raw_content.strip()[:MAX_CONTENT_LENGTH],
            "FULL_PAGE_EXTRACT"
        )

    snippet = item.get("content", "")

    if isinstance(snippet, str) and snippet.strip():

        return (
            snippet.strip()[:MAX_CONTENT_LENGTH],
            "SEARCH_RESULT_SNIPPET"
        )

    return "", "NO_CONTENT"


# ==================================================
# MAIN RESEARCH AGENT
# ==================================================

def run_research(task, script=None):

    print("\n" + "=" * 55)
    print("RESEARCH AGENT STARTED")
    print("=" * 55)

    api_key = os.getenv("TAVILY_API_KEY")

    if not api_key:

        return {
            "status": "ERROR",
            "original_ceo_topic": str(task or ""),
            "message": "TAVILY_API_KEY is missing.",
            "source_count": 0,
            "sources": []
        }

    try:

        topic, query = build_research_query(task, script)

    except Exception as error:

        return {
            "status": "ERROR",
            "original_ceo_topic": str(task or ""),
            "message": f"Topic extraction failed: {error}",
            "source_count": 0,
            "sources": []
        }

    print("[RESEARCH] Topic:", topic)
    print("[RESEARCH] Query:", query)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "query": query,
        "search_depth": "advanced",
        "topic": "general",
        "max_results": MAX_RESULTS,
        "include_answer": False,

        # Request extracted page content, not only snippets.
        "include_raw_content": "markdown",

        # Do not restrict results to a fixed domain list.
        "include_domains": []
    }

    try:

        response = requests.post(
            TAVILY_URL,
            headers=headers,
            json=payload,
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

        data = response.json()

        results = data.get("results", [])

        if not isinstance(results, list):

            raise RuntimeError(
                "Tavily returned an invalid results structure."
            )

        sources = []
        seen_urls = set()

        for item in results:

            if not isinstance(item, dict):
                continue

            url = str(item.get("url", "")).strip()

            if not url:
                continue

            parsed = urlparse(url)

            if parsed.scheme not in ("http", "https"):
                continue

            if not parsed.hostname:
                continue

            normalized_url = url.rstrip("/").lower()

            if normalized_url in seen_urls:
                continue

            seen_urls.add(normalized_url)

            content, content_type = extract_source_content(item)

            if not content:
                continue

            domain = get_domain(url)

            source = {
                "title": str(
                    item.get("title", "")
                )[:300],

                "url": url,

                "domain": domain,

                "content": content,

                "content_type": content_type,

                "score": item.get("score", 0),

                "preferred_domain_candidate": (
                    is_trusted_domain(url)
                ),

                # A preferred domain is NOT proof
                # that a historical claim is true.

                "verification_status": "NOT_VERIFIED",

                "url_verification_status": (
                    "NOT_INDEPENDENTLY_VERIFIED"
                )
            }

            sources.append(source)

        print(
            "[RESEARCH] Sources collected:",
            len(sources)
        )

        full_pages = sum(
            1 for source in sources
            if source["content_type"] == "FULL_PAGE_EXTRACT"
        )

        snippets = sum(
            1 for source in sources
            if source["content_type"] == "SEARCH_RESULT_SNIPPET"
        )

        print("[RESEARCH] Full page extracts:", full_pages)
        print("[RESEARCH] Search snippets:", snippets)

        if not sources:

            status = "NO_RESULTS"

        elif full_pages == 0:

            status = "PARTIAL"

        else:

            status = "COMPLETED"

        return {
            "status": status,

            "original_ceo_topic": str(task),

            "extracted_topic": topic,

            "query": query,

            "source_count": len(sources),

            "full_page_count": full_pages,

            "snippet_count": snippets,

            "sources": sources,

            "warning": (
                "Research results are evidence candidates. "
                "A preferred domain does not prove a claim. "
                "URLs have not been independently verified. "
                "Fact-check every claim against supplied content."
            )
        }

    except requests.exceptions.Timeout:

        return {
            "status": "ERROR",
            "original_ceo_topic": str(task),
            "extracted_topic": topic,
            "query": query,
            "message": "Tavily research request timed out.",
            "source_count": 0,
            "sources": []
        }

    except requests.exceptions.HTTPError as error:

        response = error.response

        status_code = (
            response.status_code
            if response is not None
            else "UNKNOWN"
        )

        error_text = (
            response.text[:1500]
            if response is not None
            else str(error)
        )

        return {
            "status": "ERROR",
            "original_ceo_topic": str(task),
            "extracted_topic": topic,
            "query": query,
            "message": (
                f"Tavily HTTP error {status_code}: "
                f"{error_text}"
            ),
            "source_count": 0,
            "sources": []
        }

    except requests.exceptions.RequestException as error:

        return {
            "status": "ERROR",
            "original_ceo_topic": str(task),
            "extracted_topic": topic,
            "query": query,
            "message": f"Tavily connection error: {error}",
            "source_count": 0,
            "sources": []
        }

    except (ValueError, TypeError) as error:

        return {
            "status": "ERROR",
            "original_ceo_topic": str(task),
            "extracted_topic": topic,
            "query": query,
            "message": f"Invalid Tavily response: {error}",
            "source_count": 0,
            "sources": []
        }

    except Exception as error:

        return {
            "status": "ERROR",
            "original_ceo_topic": str(task),
            "extracted_topic": topic,
            "query": query,
            "message": f"Unexpected research error: {error}",
            "source_count": 0,
            "sources": []
        }
