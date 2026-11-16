
import re
from urllib.parse import urlparse


def run_audit(task, media_result):

    print("\n[AUDIT] Advanced independent audit started...")

    problems = []
    checks = []

    def add_check(name, passed, details=""):
        checks.append({
            "check": name,
            "passed": bool(passed),
            "details": details
        })

        if not passed:
            problems.append(name + ": " + details)

    # 1. ORIGINAL TOPIC PRESERVATION

    original_topic = str(task).lower()

    concept = str(media_result.get("concept", ""))
    script = str(media_result.get("script", ""))
    edited_script = str(media_result.get("edited_script", ""))

    combined = (
        concept + "\n" + script + "\n" + edited_script
    ).lower()

    topic_ok = (
        "roanoke" in original_topic
        and "roanoke" in combined
    )

    add_check(
        "CEO topic preservation",
        topic_ok,
        "Roanoke must remain the only subject."
    )

    # 2. CONCEPT AND SCRIPT EXIST

    concept_ok = bool(concept.strip())
    script_ok = bool(script.strip())
    edited_ok = bool(edited_script.strip())

    add_check("Concept exists", concept_ok)
    add_check("Original script exists", script_ok)
    add_check("Edited script exists", edited_ok)

    # 3. DETECT TRUNCATED OUTPUT

    def looks_truncated(value):

        text = value.strip()

        if not text:
            return True

        endings = (
            ".", "!", "?", '"', "'", ")",
            "]", "}", "—"
        )

        return not text.endswith(endings)

    script_complete = not looks_truncated(script)
    edited_complete = not looks_truncated(edited_script)

    add_check(
        "Original script completion",
        script_complete,
        "Script may end in an incomplete sentence."
    )

    add_check(
        "Edited script completion",
        edited_complete,
        "Edited script may be truncated."
    )

    # 4. TIMESTAMP COVERAGE

    timestamps = re.findall(
        r"(?<!\d)(?:0?[0-9]|[1-5][0-9]):[0-5][0-9](?!\d)",
        script + "\n" + edited_script
    )

    timestamp_seconds = set()

    for timestamp in timestamps:
        minutes, seconds = map(int, timestamp.split(":"))
        timestamp_seconds.add(minutes * 60 + seconds)

    has_start = 0 in timestamp_seconds
    has_end = 60 in timestamp_seconds

    timestamp_count = len(timestamp_seconds)

    timeline_ok = (
        has_start
        and has_end
        and timestamp_count >= 5
    )

    add_check(
        "Full 0:00-1:00 timeline",
        timeline_ok,
        "Timeline must include 0:00, 1:00 and intermediate timestamps."
    )

    # 5. RESEARCH SOURCE VALIDATION

    research = media_result.get("research", {})

    if not isinstance(research, dict):
        research = {}

    sources = research.get("sources", [])

    if not isinstance(sources, list):
        sources = []

    valid_sources = []
    invalid_sources = []

    for source in sources:

        if not isinstance(source, dict):
            invalid_sources.append("Invalid source record")
            continue

        title = str(source.get("title", "")).strip()
        url = str(source.get("url", "")).strip()

        try:
            parsed = urlparse(url)

            valid_url = (
                parsed.scheme == "https"
                and bool(parsed.netloc)
                and "." in parsed.netloc
            )

        except Exception:
            valid_url = False

        if title and valid_url:
            valid_sources.append(source)
        else:
            invalid_sources.append(title or "Missing title or valid URL")

    sources_ok = len(valid_sources) > 0

    add_check(
        "Research source structure",
        sources_ok,
        f"Valid sources: {len(valid_sources)}"
    )

    # 6. SOURCE VERIFICATION STATUS

    unverified_sources = [
        source for source in valid_sources
        if source.get("verification_status") != "VERIFIED"
    ]

    all_sources_verified = (
        len(valid_sources) > 0
        and len(unverified_sources) == 0
    )

    add_check(
        "Independent source verification",
        all_sources_verified,
        f"{len(unverified_sources)} sources are not independently verified."
    )

    # 7. FACT CHECK REPORT

    fact_check = media_result.get("fact_check", "")

    if isinstance(fact_check, dict):
        fact_text = str(fact_check)
    else:
        fact_text = str(fact_check)

    fact_check_exists = bool(fact_text.strip())

    add_check(
        "Fact-check report exists",
        fact_check_exists
    )

    needs_source_count = len(
        re.findall(r"NEEDS SOURCE", fact_text, re.IGNORECASE)
    )

    contradicted_count = len(
        re.findall(r"CONTRADICTED", fact_text, re.IGNORECASE)
    )

    add_check(
        "Unsupported claims identified",
        fact_check_exists,
        f"NEEDS SOURCE: {needs_source_count}; "
        f"CONTRADICTED: {contradicted_count}"
    )

    # 8. MEDIA STATUS

    media_status = media_result.get("status")

    media_status_ok = media_status == "REVIEW_REQUIRED"

    add_check(
        "Media review status",
        media_status_ok,
        f"Current media status: {media_status}"
    )

    # 9. PUBLICATION SECURITY

    publication_approved = media_result.get(
        "publication_approved",
        False
    )

    publication_blocked = publication_approved is False

    add_check(
        "Publication remains blocked",
        publication_blocked,
        "CEO approval is mandatory."
    )

    # 10. FINAL AUDIT DECISION

    audit_passed = (
        len(problems) == 0
        and all_sources_verified
        and script_complete
        and edited_complete
        and timeline_ok
    )

    final_status = (
        "PASSED_WITH_LIMITATIONS"
        if audit_passed
        else "REVIEW_REQUIRED"
    )

    return {
        "department": "audit",
        "status": final_status,
        "audit_passed": audit_passed,
        "message": (
            "Advanced audit completed. "
            "CEO approval is still required."
        ),
        "checks": checks,
        "problems": problems,
        "source_count": len(valid_sources),
        "unverified_source_count": len(unverified_sources),
        "needs_source_count": needs_source_count,
        "contradicted_count": contradicted_count,
        "publication_approved": False
    }
