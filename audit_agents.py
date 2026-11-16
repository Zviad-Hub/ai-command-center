
import re


def run_audit(task, media_result):

    print("\n[AUDIT] Independent audit started...")

    problems = []
    checks = []

    # 1. CEO topic preservation
    original_topic = str(task).lower()
    concept = str(media_result.get("concept", ""))
    script = str(media_result.get("script", ""))
    edited_script = str(media_result.get("edited_script", ""))

    combined = (concept + script + edited_script).lower()

    topic_ok = (
        "roanoke" in original_topic
        and "roanoke" in combined
    )

    checks.append({
        "check": "CEO topic preservation",
        "passed": topic_ok
    })

    if not topic_ok:
        problems.append("CEO topic was not preserved.")

    # 2. One concept and one script
    concept_ok = bool(concept.strip())
    script_ok = bool(script.strip())

    checks.append({
        "check": "Concept exists",
        "passed": concept_ok
    })

    checks.append({
        "check": "Script exists",
        "passed": script_ok
    })

    if not concept_ok:
        problems.append("Video concept is missing.")

    if not script_ok:
        problems.append("Video script is missing.")

    # 3. Timestamp coverage
    timestamps = re.findall(
        r"\b(?:0?[0-5]?\d):[0-5]\d\b",
        script + edited_script
    )

    has_timestamps = len(timestamps) >= 4

    checks.append({
        "check": "Timestamped directions",
        "passed": has_timestamps
    })

    if not has_timestamps:
        problems.append("Timestamp coverage may be incomplete.")

    # 4. Research sources
    research = media_result.get("research", {})
    sources = research.get("sources", [])

    valid_sources = [
        source for source in sources
        if source.get("title") and source.get("url")
    ]

    sources_ok = len(valid_sources) > 0

    checks.append({
        "check": "Research source titles and URLs",
        "passed": sources_ok
    })

    if not sources_ok:
        problems.append("No usable research sources were supplied.")

    # 5. Fact-check review
    fact_check = str(media_result.get("fact_check", ""))

    fact_check_exists = bool(fact_check.strip())

    checks.append({
        "check": "Fact-check report exists",
        "passed": fact_check_exists
    })

    if not fact_check_exists:
        problems.append("Fact-check report is missing.")

    # 6. Publication safety
    publication_approved = media_result.get(
        "publication_approved",
        False
    )

    if publication_approved is not False:
        problems.append("Publication approval must remain false.")

    checks.append({
        "check": "Publication remains blocked",
        "passed": publication_approved is False
    })

    # 7. Final audit decision
    audit_status = (
        "REVIEW_REQUIRED"
        if problems
        else "PASSED_WITH_LIMITATIONS"
    )

    return {
        "department": "audit",
        "status": audit_status,
        "message": (
            "Independent audit completed. "
            "CEO approval is still required."
        ),
        "checks": checks,
        "problems": problems,
        "source_count": len(valid_sources),
        "publication_approved": False
    }
