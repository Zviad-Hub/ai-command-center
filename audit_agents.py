
import re
from urllib.parse import urlparse


# ==================================================
# COMMON UTILITIES
# ==================================================

def check_result(name, passed, details=""):
    return {
        "check": name,
        "passed": bool(passed),
        "details": details
    }


def normalize_text(text):
    text = str(text or "")

    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    return text


def normalize_dashes(text):
    return re.sub(r"[‐-‒–—−]", "-", str(text or ""))


def normalize_url(url):

    try:
        parsed = urlparse(str(url).strip())

        if parsed.scheme not in ("http", "https"):
            return None

        if not parsed.netloc:
            return None

        if "." not in parsed.netloc:
            return None

        return str(url).strip()

    except Exception:
        return None


def collect_strings(value):

    result = []

    if isinstance(value, str):
        result.append(value)

    elif isinstance(value, dict):

        for item in value.values():
            result.extend(collect_strings(item))

    elif isinstance(value, (list, tuple)):

        for item in value:
            result.extend(collect_strings(item))

    return result


def find_nested_values(data, target_keys):

    found = []

    if isinstance(data, dict):

        for key, value in data.items():

            if str(key).lower() in target_keys:
                found.append(value)

            found.extend(
                find_nested_values(value, target_keys)
            )

    elif isinstance(data, (list, tuple)):

        for item in data:
            found.extend(
                find_nested_values(item, target_keys)
            )

    return found


def get_media_text(media):
    return "\n".join(collect_strings(media))


def count_words(text):

    text = str(text or "")

    text = re.sub(r"\*\*|__", "", text)

    return len(
        re.findall(
            r"\b[\w’'-]+\b",
            text,
            flags=re.UNICODE
        )
    )


# ==================================================
# FINAL SCRIPT EXTRACTION
# ==================================================

def extract_final_script(media):

    edited = media.get("edited_script", "")

    if isinstance(edited, str) and edited.strip():
        return normalize_text(edited)

    return normalize_text(
        str(media.get("script", ""))
    )


# ==================================================
# NARRATION EXTRACTION
# ==================================================

def extract_narration(media):

    script = extract_final_script(media)

    pattern = (
        r"^\s*(?:[-*]\s*)?"
        r"(?:\*\*)?"
        r"(?:SCRIPT|NARRATION)"
        r"(?:\s*\([^)]*\))?"
        r"\s*:\s*(?:\*\*)?\s*"
        r"(.*?)"
        r"(?=^\s*(?:[-*]\s*)?(?:\*\*)?"
        r"VISUAL DIRECTIONS"
        r"\s*:\s*(?:\*\*)?|"
        r"\Z)"
    )

    match = re.search(
        pattern,
        script,
        re.IGNORECASE | re.MULTILINE | re.DOTALL
    )

    if not match:
        return ""

    return match.group(1).strip()


# ==================================================
# VISUAL EXTRACTION
# ==================================================

def extract_visual_text(media):

    script = extract_final_script(media)

    pattern = (
        r"^\s*(?:[-*]\s*)?"
        r"(?:\*\*)?"
        r"VISUAL DIRECTIONS"
        r"\s*:\s*(?:\*\*)?\s*"
        r"(.*?)"
        r"(?=^\s*(?:[-*]\s*)?(?:\*\*)?"
        r"(?:FACTS TO VERIFY|FACT CHECK|"
        r"EDITOR REVIEW|PROBLEMS|CORRECTIONS|"
        r"FACTS STILL NEEDING|UNSUPPORTED CLAIMS)"
        r"\s*:|"
        r"\Z)"
    )

    match = re.search(
        pattern,
        script,
        re.IGNORECASE | re.MULTILINE | re.DOTALL
    )

    if match:
        return match.group(1).strip()

    return ""


def extract_visual_ranges(text):

    text = normalize_dashes(text)

    pattern = (
        r"(?m)^\s*(?:[-*]\s*)?"
        r"(\d{1,2}:\d{2})"
        r"\s*-\s*"
        r"(\d{1,2}:\d{2})"
        r"(?!\d)"
    )

    return re.findall(pattern, text)


# ==================================================
# FACT CHECK STATUS EXTRACTION
# ==================================================

def extract_fact_check_statuses(text):

    text = str(text or "").upper()

    pattern = (
        r"\bSTATUS\s*:\s*"
        r"(VERIFIED|NEEDS SOURCE|CONTRADICTED)\b"
    )

    return re.findall(pattern, text)


# ==================================================
# SOURCE COLLECTION
# ==================================================

def collect_sources(media):

    source_values = find_nested_values(
        media,
        {"sources", "source_results"}
    )

    sources = []
    seen = set()

    for value in source_values:

        items = []

        if isinstance(value, list):
            items = [
                item for item in value
                if isinstance(item, dict)
            ]

        elif isinstance(value, dict):
            items = [value]

        for item in items:

            identity = (
                str(item.get("url", "")).strip(),
                str(item.get("title", "")).strip()
            )

            if identity in seen:
                continue

            seen.add(identity)
            sources.append(item)

    return sources


# ==================================================
# AUDITOR 1: COMPLIANCE AUDITOR
# ==================================================

def compliance_auditor(task, media):

    checks = []

    task_text = str(task).lower()
    media_text = get_media_text(media).lower()

    # ----------------------------------------------
    # TOPIC PRESERVATION
    # ----------------------------------------------

    required_topic_terms = [
        "roanoke",
        "colony"
    ]

    topic_passed = all(
        term in task_text and term in media_text
        for term in required_topic_terms
    )

    checks.append(
        check_result(
            "Topic preservation",
            topic_passed,
            "The original Roanoke Lost Colony topic must be preserved."
        )
    )

    # ----------------------------------------------
    # NARRATION WORD COUNT
    # ----------------------------------------------

    narration = extract_narration(media)

    narration_words = count_words(narration)

    checks.append(
        check_result(
            "Narration word count",
            125 <= narration_words <= 140,
            (
                f"Detected {narration_words} words; "
                "required 125-140."
            )
        )
    )

    # ----------------------------------------------
    # SIX VISUAL SCENES
    # ----------------------------------------------

    visual_text = extract_visual_text(media)

    visual_ranges = extract_visual_ranges(
        visual_text
    )

    expected_ranges = [
        ("0:00", "0:10"),
        ("0:10", "0:20"),
        ("0:20", "0:30"),
        ("0:30", "0:40"),
        ("0:40", "0:50"),
        ("0:50", "1:00")
    ]

    checks.append(
        check_result(
            "Six visual scenes",
            visual_ranges == expected_ranges,
            (
                f"Detected {len(visual_ranges)} scenes. "
                "Expected exactly six consecutive 10-second scenes."
            )
        )
    )

    # ----------------------------------------------
    # REQUIRED CONTENT SECTIONS
    # ----------------------------------------------

    required_sections = [
        "video title",
        "script",
        "visual directions"
    ]

    final_script = extract_final_script(media).lower()

    missing_sections = [
        section
        for section in required_sections
        if section not in final_script
    ]

    checks.append(
        check_result(
            "Required content sections",
            not missing_sections,
            (
                "Missing: " + ", ".join(missing_sections)
                if missing_sections
                else "Required sections detected."
            )
        )
    )

    # ----------------------------------------------
    # NARRATION COMPLETENESS
    # ----------------------------------------------

    checks.append(
        check_result(
            "Narration completeness",
            bool(narration.strip()),
            "Final narration must be present."
        )
    )

    return {
        "auditor": "Compliance Auditor",
        "checks": checks,
        "passed": all(
            item["passed"] for item in checks
        )
    }


# ==================================================
# AUDITOR 2: EVIDENCE AUDITOR
# ==================================================

def evidence_auditor(media):

    checks = []

    # ----------------------------------------------
    # SOURCE VERIFICATION
    # ----------------------------------------------

    sources = collect_sources(media)

    source_urls = []
    source_statuses = []

    for source in sources:

        url = source.get("url")

        if url:
            source_urls.append(url)

        status = source.get(
            "verification_status",
            ""
        )

        if status:
            source_statuses.append(
                str(status).upper().strip()
            )

    valid_urls = [
        url for url in source_urls
        if normalize_url(url)
    ]

    sources_verified = (
        bool(sources)
        and len(valid_urls) == len(sources)
        and len(source_statuses) == len(sources)
        and all(
            status in ("VERIFIED", "CONFIRMED")
            for status in source_statuses
        )
    )

    checks.append(
        check_result(
            "Source verification",
            sources_verified,
            (
                f"Sources: {len(sources)}; "
                f"valid URLs: {len(valid_urls)}; "
                f"statuses: {source_statuses}; "
                "URL structure does not prove source verification."
            )
        )
    )

    # ----------------------------------------------
    # FACT CHECK REPORT
    # ----------------------------------------------

    fact_check_values = find_nested_values(
        media,
        {
            "fact_check",
            "fact_check_report",
            "fact_check_results"
        }
    )

    fact_check_text = "\n".join(
        collect_strings(fact_check_values)
    )

    statuses = extract_fact_check_statuses(
        fact_check_text
    )

    has_verified = "VERIFIED" in statuses
    has_needs_source = "NEEDS SOURCE" in statuses
    has_contradicted = "CONTRADICTED" in statuses

    checks.append(
        check_result(
            "Fact-check coverage",
            has_verified,
            (
                "At least one explicitly VERIFIED claim is required."
                if not has_verified
                else "At least one explicitly VERIFIED claim was reported."
            )
        )
    )

    checks.append(
        check_result(
            "Unsupported claims",
            not has_needs_source,
            (
                "Claims marked NEEDS SOURCE were found."
                if has_needs_source
                else "No claims marked NEEDS SOURCE were found."
            )
        )
    )

    checks.append(
        check_result(
            "Contradiction detection",
            not has_contradicted,
            (
                "Claims explicitly marked CONTRADICTED were found."
                if has_contradicted
                else "No claims marked CONTRADICTED were found."
            )
        )
    )

    # ----------------------------------------------
    # URL STRUCTURE
    # ----------------------------------------------

    all_text = get_media_text(media)

    discovered_urls = re.findall(
        r"https?://[^\s<>\"')\]]+",
        all_text,
        flags=re.IGNORECASE
    )

    invalid_urls = [
        url for url in discovered_urls
        if not normalize_url(url)
    ]

    checks.append(
        check_result(
            "URL structure",
            not invalid_urls,
            (
                f"Invalid URLs detected: {len(invalid_urls)}"
                if invalid_urls
                else "No malformed URLs detected."
            )
        )
    )

    return {
        "auditor": "Evidence Auditor",
        "checks": checks,
        "passed": all(
            item["passed"] for item in checks
        )
    }


# ==================================================
# AUDITOR 3: INTEGRITY AUDITOR
# ==================================================

def integrity_auditor(media):

    checks = []

    # ----------------------------------------------
    # DEPARTMENT IDENTITY
    # ----------------------------------------------

    department = str(
        media.get("department", "")
    ).lower()

    checks.append(
        check_result(
            "Department identity",
            department == "media",
            f"Received department: {department or 'missing'}"
        )
    )

    # ----------------------------------------------
    # MEDIA STATUS
    # ----------------------------------------------

    status = str(
        media.get("status", "")
    ).upper()

    checks.append(
        check_result(
            "Media review status",
            status == "REVIEW_REQUIRED",
            f"Received status: {status or 'missing'}"
        )
    )

    # ----------------------------------------------
    # PUBLICATION SAFETY
    # ----------------------------------------------

    publication_approved = media.get(
        "publication_approved"
    )

    checks.append(
        check_result(
            "Publication safety",
            publication_approved is False,
            "Media must never approve its own publication."
        )
    )

    # ----------------------------------------------
    # RESULT STRUCTURE
    # ----------------------------------------------

    checks.append(
        check_result(
            "Result structure",
            isinstance(media, dict),
            "Media result must be a dictionary."
        )
    )

    # ----------------------------------------------
    # RESEARCH DATA
    # ----------------------------------------------

    research_values = find_nested_values(
        media,
        {"research"}
    )

    research_present = any(
        isinstance(value, dict)
        and bool(value)
        for value in research_values
    )

    checks.append(
        check_result(
            "Research data structure",
            research_present,
            "Research results must be present."
        )
    )

    # ----------------------------------------------
    # SPECIALIST OUTPUT
    # ----------------------------------------------

    specialists = media.get("specialists")

    specialists_valid = (
        isinstance(specialists, (list, dict))
        and bool(specialists)
    )

    checks.append(
        check_result(
            "Specialist output",
            specialists_valid,
            (
                f"Received {len(specialists)} specialists."
                if specialists_valid
                else "Specialist output is missing or invalid."
            )
        )
    )

    return {
        "auditor": "Integrity Auditor",
        "checks": checks,
        "passed": all(
            item["passed"] for item in checks
        )
    }


# ==================================================
# FINAL AUDIT COORDINATOR
# ==================================================

def run_audit(task, media_result):

    if not isinstance(media_result, dict):

        return {
            "department": "audit",
            "status": "ERROR",
            "message": "Invalid media result. Expected dictionary.",
            "publication_approved": False
        }

    auditors = [
        compliance_auditor(task, media_result),
        evidence_auditor(media_result),
        integrity_auditor(media_result)
    ]

    all_checks = []

    for auditor in auditors:

        for check in auditor["checks"]:

            all_checks.append({
                "auditor": auditor["auditor"],
                **check
            })

    total_checks = len(all_checks)

    passed_checks = sum(
        1 for check in all_checks
        if check["passed"]
    )

    failed_checks = [
        check for check in all_checks
        if not check["passed"]
    ]

    all_passed = (
        total_checks > 0
        and len(failed_checks) == 0
    )

    return {
        "department": "audit",

        "status": (
            "PASSED_WITH_LIMITATIONS"
            if all_passed
            else "REVIEW_REQUIRED"
        ),

        "auditors": auditors,

        "summary": {
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "failed_checks": len(failed_checks)
        },

        "failed_checks": failed_checks,

        # Audit can never grant publication approval.
        "publication_approved": False,

        "final_decision": "CEO_APPROVAL_REQUIRED",

        "message": (
            "ყველა აუდიტის შემოწმება წარმატებით დასრულდა. "
            "გამოქვეყნებისთვის მაინც საჭიროა CEO-ს ნებართვა."
            if all_passed
            else
            "აუდიტმა აღმოაჩინა პრობლემები. "
            "მასალა საჭიროებს შესწორებას ან დამატებით მტკიცებულებებს."
        )
    }
