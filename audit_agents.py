
import re
from urllib.parse import urlparse


# ==================================================
# COMMON AUDIT UTILITIES
# ==================================================

def check_result(name, passed, details=""):
    return {
        "check": name,
        "passed": bool(passed),
        "details": str(details)
    }


def is_truncated(value):
    value = str(value).strip()

    if not value:
        return True

    if value.endswith(("...", "…", ":", "-", "–", "—")):
        return True

    return value[-1] not in ".!?\"')]}"



def normalize_url(url):
    url = str(url).strip().rstrip(".,;")

    try:
        parsed = urlparse(url)

        if parsed.scheme not in ("http", "https"):
            return ""

        if not parsed.hostname:
            return ""

        return (
            parsed.scheme.lower()
            + "://"
            + parsed.netloc.lower()
            + parsed.path.rstrip("/")
        )

    except Exception:
        return ""


def extract_urls(text):
    return set(
        re.findall(
            r"https?://[^\s)\]>\"']+",
            str(text),
            re.IGNORECASE
        )
    )


def extract_timestamps(text):
    pattern = r"(?<!\d)(\d{1,2}:\d{2})(?!\d)"
    matches = re.findall(pattern, str(text))

    seconds = set()

    for timestamp in matches:
        minutes, secs = map(int, timestamp.split(":"))

        if secs < 60:
            seconds.add(minutes * 60 + secs)

    return seconds


def extract_visual_ranges(text):
    pattern = (
        r"(?m)^\s*"
        r"(?:[-*]\s*)?"
        r"(\d{1,2}:\d{2})\s*[-–—]\s*"
        r"(\d{1,2}:\d{2})"
    )

    return re.findall(pattern, str(text))


def extract_fact_check_statuses(report):
    report = str(report)

    statuses = []

    # Format 1: STATUS: VERIFIED
    standalone_pattern = re.compile(
        r"^\s*(?:[-*]\s*)?"
        r"(?:\*\*)?STATUS(?:\*\*)?"
        r"\s*:?\s*(?:\*\*)?\s*:?\s*"
        r"(VERIFIED|NEEDS\s+SOURCE|CONTRADICTED)\b",
        re.IGNORECASE | re.MULTILINE
    )

    for status in standalone_pattern.findall(report):
        statuses.append(
            re.sub(r"\s+", " ", status).upper()
        )

    # Format 2: Markdown table rows
    for line in report.splitlines():

        if "|" not in line:
            continue

        cells = [
            cell.strip().strip("*").upper()
            for cell in line.split("|")
        ]

        for cell in cells:
            if cell in (
                "VERIFIED",
                "NEEDS SOURCE",
                "CONTRADICTED"
            ):
                statuses.append(cell)

    return statuses


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

    # TOPIC PRESERVATION

    topic_words = [
        word for word in re.findall(
            r"\b[a-z]{4,}\b",
            original_task
        )
        if word not in {
            "create", "video", "about", "engaging",
            "powerful", "opening", "hook", "write",
            "english", "shorts", "script", "generate",
            "historical", "facts", "require", "external",
            "verification", "verify", "minute", "seconds"
        }
    ]

    topic_terms = [
        word for word in topic_words
        if word in {"roanoke", "colony"}
    ]

    topic_ok = (
        all(term in concept.lower() for term in topic_terms)
        and all(term in script.lower() for term in topic_terms)
        and all(term in edited.lower() for term in topic_terms)
        if topic_terms
        else bool(concept.strip() and script.strip() and edited.strip())
    )

    checks.append(check_result(
        "CEO topic preservation",
        topic_ok,
        f"Required topic terms: {topic_terms}"
    ))

    # REQUIRED OUTPUTS

    checks.append(check_result(
        "Concept exists",
        bool(concept.strip())
    ))

    checks.append(check_result(
        "Original script exists",
        bool(script.strip())
    ))

    checks.append(check_result(
        "Edited script exists",
        bool(edited.strip())
    ))

    # COMPLETENESS

    checks.append(check_result(
        "Original script completeness",
        not is_truncated(script)
    ))

    checks.append(check_result(
        "Edited script completeness",
        not is_truncated(edited)
    ))

    # NARRATION WORD COUNT

    narration = ""

    match = re.search(
        r"^\s*\*{0,2}(?:SCRIPT|NARRATION)"
        r"(?:\s*\([^)]*\))?\s*:\*{0,2}\s*"
        r"(.*?)"
        r"(?=^\s*\*{0,2}VISUAL DIRECTIONS\s*:\*{0,2})",
        edited,
        re.IGNORECASE | re.MULTILINE | re.DOTALL
    )

    if match:
        narration = match.group(1).strip()

    narration = re.sub(r"\*\*|__", "", narration)

    word_count = len(
        re.findall(r"\b[\w’'-]+\b", narration)
    )

    word_count_ok = (
        125 <= word_count <= 140
        if narration
        else False
    )

    checks.append(check_result(
        "Narration word count",
        word_count_ok,
        f"Detected words: {word_count}; Required: 125-140"
    ))

    # EXACT VISUAL TIMELINE

    expected_ranges = [
        ("0:00", "0:10"),
        ("0:10", "0:20"),
        ("0:20", "0:30"),
        ("0:30", "0:40"),
        ("0:40", "0:50"),
        ("0:50", "1:00")
    ]

    visual_ranges = extract_visual_ranges(edited)

    visual_ok = (
        visual_ranges == expected_ranges
    )

    checks.append(check_result(
        "Exactly six visual scenes",
        visual_ok,
        f"Detected: {visual_ranges}"
    ))

    timestamps = extract_timestamps(edited)

    expected_timestamps = set(range(0, 61, 10))
    missing = sorted(expected_timestamps - timestamps)

    checks.append(check_result(
        "60-second timeline markers",
        len(missing) == 0,
        f"Missing markers: {missing}"
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
    source_urls = set()

    for source in sources:

        if not isinstance(source, dict):
            invalid_sources.append("Invalid source record")
            continue

        title = str(source.get("title", "")).strip()
        url = str(source.get("url", "")).strip()
        normalized = normalize_url(url)

        try:
            parsed = urlparse(url)

            valid_url = (
                parsed.scheme == "https"
                and bool(parsed.hostname)
                and "." in parsed.hostname
            )

        except Exception:
            valid_url = False

        if title and valid_url and normalized:
            valid_sources.append(source)
            source_urls.add(normalized)
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
        "Source URL structure",
        len(invalid_sources) == 0,
        f"Invalid records: {len(invalid_sources)}"
    ))

    # SOURCE VERIFICATION

    unverified = [
        source for source in valid_sources
        if str(
            source.get("verification_status", "")
        ).upper() != "VERIFIED"
    ]

    checks.append(check_result(
        "Independent source verification",
        len(valid_sources) > 0 and len(unverified) == 0,
        f"Unverified sources: {len(unverified)}"
    ))

    # FACT CHECK REPORT

    fact_check = str(media.get("fact_check", ""))

    statuses = extract_fact_check_statuses(fact_check)

    checks.append(check_result(
        "Fact-check report exists",
        bool(fact_check.strip())
    ))

    checks.append(check_result(
        "Claim statuses detected",
        len(statuses) > 0,
        f"Parsed claim statuses: {len(statuses)}"
    ))

    needs_source = statuses.count("NEEDS SOURCE")
    contradicted = statuses.count("CONTRADICTED")
    verified = statuses.count("VERIFIED")

    checks.append(check_result(
        "No unsupported claims",
        (
            len(statuses) > 0
            and needs_source == 0
        ),
        f"Claims needing sources: {needs_source}"
    ))

    checks.append(check_result(
        "No contradicted claims",
        (
            len(statuses) > 0
            and contradicted == 0
        ),
        f"Contradicted claims: {contradicted}"
    ))

    # CROSS-CHECK URLS IN ALL MEDIA OUTPUTS

    script_urls = (
        extract_urls(media.get("script", ""))
        | extract_urls(media.get("edited_script", ""))
        | extract_urls(fact_check)
    )

    unmatched_urls = []

    for url in script_urls:

        normalized = normalize_url(url)

        if normalized and normalized not in source_urls:
            unmatched_urls.append(url)

    checks.append(check_result(
        "Media URLs match research records",
        len(unmatched_urls) == 0,
        f"Unmatched URLs: {len(unmatched_urls)}"
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
        "verified_claim_count": verified,
        "needs_source_count": needs_source,
        "contradicted_count": contradicted,
        "unmatched_urls": unmatched_urls
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

    checks.append(check_result(
        "Media review status",
        media.get("status") == "REVIEW_REQUIRED",
        f"Current status: {media.get('status')}"
    ))

    checks.append(check_result(
        "Publication approval remains blocked",
        media.get("publication_approved") is False,
        "Only CEO can authorize publication."
    ))

    for field in ["concept", "script", "edited_script"]:

        checks.append(check_result(
            f"Output type: {field}",
            isinstance(media.get(field), str),
            "Expected a text string."
        ))

    checks.append(check_result(
        "Research result structure",
        isinstance(media.get("research"), dict),
        "Research must be a structured object."
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

    reports = [
        compliance_auditor(task, media_result),
        evidence_auditor(media_result),
        integrity_auditor(media_result)
    ]

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

    final_status = (
        "PASSED_WITH_LIMITATIONS"
        if audit_passed
        else "REVIEW_REQUIRED"
    )

    print("\n" + "=" * 55)
    print("FINAL AUDIT DECISION:", final_status)
    print("FAILED AUDITORS:", failed_auditors)
    print("TOTAL CHECKS:", len(all_checks))
    print("PASSED CHECKS:", len(all_checks) - len(failed_checks))
    print("FAILED CHECKS:", len(failed_checks))
    print("=" * 55)

    return {
        "department": "audit",
        "status": final_status,
        "audit_passed": audit_passed,
        "message": (
            "Automated audit checks passed. "
            "CEO approval is still mandatory."
            if audit_passed
            else "Audit checks failed. Human review is required."
        ),
        "auditor_reports": reports,
        "failed_auditors": failed_auditors,
        "failed_checks": failed_checks,
        "total_checks": len(all_checks),
        "passed_checks": len(all_checks) - len(failed_checks),
        "publication_approved": False
    }
