
import re
from urllib.parse import urlparse


# ==================================================
# COMMON AUDIT UTILITIES
# ==================================================

def check_result(name, passed, details=""):
    return {
        "check": name,
        "passed": bool(passed),
        "details": details
    }


def is_truncated(value):
    value = str(value).strip()

    if not value:
        return True

    if value.endswith(("...", "…", ":", "-", "–", "—")):
        return True

    return value[-1] not in ".!?\"')]}"



def extract_timestamps(text):
    pattern = (
        r"^\s*(\d{1,2}:\d{2})"
        r"\s*(?:[-–—|:]|$)"
    )

    matches = re.findall(
        pattern,
        str(text),
        flags=re.MULTILINE
    )

    seconds = set()

    for timestamp in matches:
        minutes, secs = map(int, timestamp.split(":"))

        if secs < 60:
            seconds.add(minutes * 60 + secs)

    return seconds


# ==================================================
# AUDITOR 1: COMPLIANCE
# ==================================================

def compliance_auditor(task, media):

    print("\n[COMPLIANCE AUDITOR] Checking CEO requirements...")

    checks = []

    concept = str(media.get("concept", ""))
    script = str(media.get("script", ""))
    edited = str(media.get("edited_script", ""))

    original_task = str(task).lower()

    combined = (
        concept + "\n" + script + "\n" + edited
    ).lower()

    # TOPIC LOCK

    if "roanoke" in original_task:
        topic_ok = (
            "roanoke" in concept.lower()
            and "roanoke" in script.lower()
            and "roanoke" in edited.lower()
        )
    else:
        topic_ok = bool(concept.strip() and script.strip())

    checks.append(check_result(
        "CEO topic preservation",
        topic_ok,
        "The original topic must remain consistent."
    ))

    # ONE CONCEPT AND ONE SCRIPT

    concept_ok = bool(concept.strip())
    script_ok = bool(script.strip())
    edited_ok = bool(edited.strip())

    checks.append(check_result(
        "Exactly one concept field",
        concept_ok,
        "One non-empty concept is required."
    ))

    checks.append(check_result(
        "Exactly one original script field",
        script_ok,
        "One non-empty original script is required."
    ))

    checks.append(check_result(
        "Edited script exists",
        edited_ok
    ))

    # OUTPUT COMPLETENESS

    original_complete = not is_truncated(script)
    edited_complete = not is_truncated(edited)

    checks.append(check_result(
        "Original script completeness",
        original_complete,
        "The original script may be incomplete."
    ))

    checks.append(check_result(
        "Edited script completeness",
        edited_complete,
        "The edited script may be incomplete."
    ))

    # TIMELINE

    timestamps = extract_timestamps(
        script + "\n" + edited
    )

    timeline_ok = (
        0 in timestamps
        and 60 in timestamps
        and len(timestamps) >= 5
    )

    checks.append(check_result(
        "60-second timeline",
        timeline_ok,
        f"Detected timestamps: {len(timestamps)}"
    ))

    return {
        "auditor": "compliance",
        "status": (
            "PASSED"
            if all(item["passed"] for item in checks)
            else "FAILED"
        ),
        "checks": checks
    }


# ==================================================
# AUDITOR 2: EVIDENCE
# ==================================================

def evidence_auditor(media):

    print("\n[EVIDENCE AUDITOR] Checking research evidence...")

    checks = []

    research = media.get("research", {})

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
                and bool(parsed.hostname)
                and "." in parsed.hostname
            )

        except Exception:
            valid_url = False

        if title and valid_url:
            valid_sources.append(source)
        else:
            invalid_sources.append(
                title or "Missing title or valid HTTPS URL"
            )

    checks.append(check_result(
        "Research sources exist",
        len(valid_sources) > 0,
        f"Valid source records: {len(valid_sources)}"
    ))

    checks.append(check_result(
        "All source records have valid structure",
        len(invalid_sources) == 0,
        f"Invalid records: {len(invalid_sources)}"
    ))

    # DOMAIN MATCH DOES NOT EQUAL VERIFICATION.

    unverified = [
        source for source in valid_sources
        if source.get("verification_status") != "VERIFIED"
    ]

    independently_verified = (
        len(valid_sources) > 0
        and len(unverified) == 0
    )

    checks.append(check_result(
        "Independent source verification",
        independently_verified,
        f"Unverified sources: {len(unverified)}"
    ))

    # FACT CHECK REPORT

    fact_check = str(media.get("fact_check", ""))

    fact_check_exists = bool(fact_check.strip())

    checks.append(check_result(
        "Fact-check report exists",
        fact_check_exists
    ))

    needs_source = len(re.findall(
        r"NEEDS SOURCE",
        fact_check,
        re.IGNORECASE
    ))

    contradicted = len(re.findall(
        r"CONTRADICTED",
        fact_check,
        re.IGNORECASE
    ))

    checks.append(check_result(
        "No unsupported claims",
        fact_check_exists and needs_source == 0,
        f"Claims needing sources: {needs_source}"
    ))

    checks.append(check_result(
        "No contradicted claims",
        fact_check_exists and contradicted == 0,
        f"Contradicted claims: {contradicted}"
    ))

    return {
        "auditor": "evidence",
        "status": (
            "PASSED"
            if all(item["passed"] for item in checks)
            else "FAILED"
        ),
        "checks": checks,
        "source_count": len(valid_sources),
        "unverified_source_count": len(unverified),
        "invalid_source_count": len(invalid_sources),
        "needs_source_count": needs_source,
        "contradicted_count": contradicted
    }


# ==================================================
# AUDITOR 3: INTEGRITY
# ==================================================

def integrity_auditor(media):

    print("\n[INTEGRITY AUDITOR] Checking output integrity...")

    checks = []

    required_fields = [
        "concept",
        "script",
        "edited_script",
        "research",
        "fact_check"
    ]

    for field in required_fields:

        value = media.get(field)

        exists = (
            value is not None
            and bool(str(value).strip())
        )

        checks.append(check_result(
            f"Required field: {field}",
            exists,
            "Missing or empty output."
        ))

    # MEDIA STATUS

    media_status = media.get("status")

    checks.append(check_result(
        "Media review status",
        media_status == "REVIEW_REQUIRED",
        f"Current status: {media_status}"
    ))

    # PUBLICATION SECURITY

    publication_blocked = (
        media.get("publication_approved") is False
    )

    checks.append(check_result(
        "Publication approval remains blocked",
        publication_blocked,
        "Only CEO can authorize publication."
    ))

    # CHECK OUTPUT TYPES

    for field in ["concept", "script", "edited_script"]:

        correct_type = isinstance(
            media.get(field),
            str
        )

        checks.append(check_result(
            f"Output type: {field}",
            correct_type,
            "Expected a text string."
        ))

    return {
        "auditor": "integrity",
        "status": (
            "PASSED"
            if all(item["passed"] for item in checks)
            else "FAILED"
        ),
        "checks": checks
    }


# ==================================================
# AUDIT MANAGER
# ==================================================

def run_audit(task, media_result):

    print("\n" + "=" * 55)
    print("INDEPENDENT AUDIT DEPARTMENT")
    print("=" * 55)

    if not isinstance(media_result, dict):

        return {
            "department": "audit",
            "status": "REVIEW_REQUIRED",
            "audit_passed": False,
            "message": "Invalid or missing Media result.",
            "publication_approved": False
        }

    # THREE INDEPENDENT AUDITORS

    reports = [
        compliance_auditor(task, media_result),
        evidence_auditor(media_result),
        integrity_auditor(media_result)
    ]

    # COLLECT FAILURES

    failed_auditors = [
        report["auditor"]
        for report in reports
        if report["status"] != "PASSED"
    ]

    all_checks = []

    for report in reports:
        all_checks.extend(report["checks"])

    failed_checks = [
        item for item in all_checks
        if not item["passed"]
    ]

    audit_passed = (
        len(failed_auditors) == 0
        and len(failed_checks) == 0
    )

    # FINAL DECISION

    final_status = (
        "PASSED_WITH_LIMITATIONS"
        if audit_passed
        else "REVIEW_REQUIRED"
    )

    print("\n" + "=" * 55)
    print("FINAL AUDIT DECISION:", final_status)
    print("FAILED AUDITORS:", failed_auditors)
    print("FAILED CHECKS:", len(failed_checks))
    print("=" * 55)

    return {
        "department": "audit",
        "status": final_status,
        "audit_passed": audit_passed,
        "message": (
            "All automated audit checks passed. "
            "CEO approval is still mandatory."
            if audit_passed
            else "Audit failed. Human review is required."
        ),
        "auditor_reports": reports,
        "failed_auditors": failed_auditors,
        "failed_checks": failed_checks,
        "total_checks": len(all_checks),
        "passed_checks": len(all_checks) - len(failed_checks),
        "publication_approved": False
    }
