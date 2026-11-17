
import math
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
    return text.replace("\r\n", "\n").replace("\r", "\n")


def normalize_dashes(text):
    return re.sub(r"[‐‑‒–—−]", "-", str(text or ""))


def normalize_url(url):
    try:
        parsed = urlparse(str(url).strip())

        if parsed.scheme not in ("http", "https"):
            return None

        if not parsed.netloc or "." not in parsed.netloc:
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
    text = re.sub(r"\*\*|__", "", str(text or ""))

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
        r"(?im)^\s*(?:[-*]\s*)?(?:#{1,6}\s*)?"
        r"(?:\*\*)?(?:SCRIPT|NARRATION)"
        r"(?:\s*\([^)]*\))?\s*:"
        r"\s*(?:\*\*)?\s*"
        r"(.*?)"
        r"(?=^\s*(?:[-*]\s*)?(?:#{1,6}\s*)?"
        r"(?:\*\*)?VISUAL DIRECTIONS\s*:|"
        r"^\s*(?:[-*]\s*)?(?:#{1,6}\s*)?"
        r"(?:\*\*)?FACTS TO VERIFY\s*:|"
        r"\Z)"
    )

    match = re.search(
        pattern,
        script,
        re.IGNORECASE | re.MULTILINE | re.DOTALL
    )

    return match.group(1).strip() if match else ""


# ==================================================
# VISUAL EXTRACTION
# ==================================================

def extract_visual_text(media):
    script = extract_final_script(media)

    pattern = (
        r"(?im)^\s*(?:[-*]\s*)?(?:#{1,6}\s*)?"
        r"(?:\*\*)?VISUAL DIRECTIONS\s*:"
        r"\s*(?:\*\*)?\s*"
        r"(.*?)"
        r"(?=^\s*(?:[-*]\s*)?(?:#{1,6}\s*)?"
        r"(?:\*\*)?(?:FACTS TO VERIFY|FACT CHECK|"
        r"EDITOR REVIEW|PROBLEMS|CORRECTIONS|"
        r"FACTS STILL NEEDING|UNSUPPORTED CLAIMS)"
        r"\s*:|\Z)"
    )

    match = re.search(
        pattern,
        script,
        re.IGNORECASE | re.MULTILINE | re.DOTALL
    )

    return match.group(1).strip() if match else ""


def extract_visual_ranges(text):
    text = normalize_dashes(text)

    return re.findall(
        r"(?m)^\s*(?:[-*]\s*)?"
        r"(\d{1,2}:\d{2})\s*-\s*"
        r"(\d{1,2}:\d{2})(?!\d)",
        text
    )


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
        if isinstance(value, list):
            items = [
                item for item in value
                if isinstance(item, dict)
            ]

        elif isinstance(value, dict):
            items = [value]

        else:
            items = []

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

    task_text = str(task or "").casefold()
    concept_text = str(media.get("concept", "") or "")
    final_script = extract_final_script(media).casefold()

    # TOPIC PRESERVATION — derive the subject from this task's own concept.
    topic_line = None
    concept_lines = concept_text.splitlines()
    for index, line in enumerate(concept_lines):
        heading = re.match(
            r"^\s*(?:[-*]\s*)?(?:#{1,6}\s*)?(?:\*\*)?EXACT TOPIC\s*:?[ \t]*(?:\*\*)?\s*(.*)$",
            line,
            re.IGNORECASE,
        )
        if not heading:
            continue
        topic_line = heading.group(1).strip(" *")
        if not topic_line:
            for candidate in concept_lines[index + 1:]:
                candidate = candidate.strip()
                if candidate and not re.match(r"^[A-Z][A-Z ]+:$", candidate):
                    topic_line = candidate
                    break
        break

    stopwords = {
        "a", "an", "the", "and", "or", "of", "to", "in", "on", "at", "by",
        "from", "for", "with", "without", "about", "into", "as", "is", "are",
        "was", "were", "be", "do", "does", "did", "not", "no", "any", "all",
        "create", "make", "write", "produce", "prepare", "generate", "develop",
        "video", "short", "script", "narration", "visual", "directions", "scene",
        "scenes", "exact", "topic", "concept", "hook", "key", "questions",
        "investigate", "research", "fact", "check", "checks", "claim", "claims",
        "source", "sources", "supplied", "provided", "evidence", "verified",
        "verification", "supported", "historical", "details", "uncertain",
        "include", "must", "should", "would", "could", "please", "using", "use",
        "based", "only", "one", "two", "three", "four", "five", "six", "125",
        "140", "words", "minute", "minutes", "exactly", "original", "ceo",
        "request", "task",
    }
    topic_terms = []
    for term in re.findall(r"[^\W_]+", str(topic_line or "").casefold(), flags=re.UNICODE):
        if term not in stopwords and len(term) > 1 and term not in topic_terms:
            topic_terms.append(term)

    matched_terms = [
        term for term in topic_terms
        if re.search(rf"\b{re.escape(term)}\b", task_text)
        and re.search(rf"\b{re.escape(term)}\b", final_script)
    ]
    required_matches = max(1, math.ceil(len(topic_terms) * 0.6))
    topic_passed = (
        bool(topic_terms)
        and len(matched_terms) >= required_matches
    )

    checks.append(
        check_result(
            "Topic preservation",
            topic_passed,
            (
                f"Matched {len(matched_terms)} of {len(topic_terms)} key topic terms "
                "from the concept's EXACT TOPIC in both the original task and final script; "
                f"{required_matches} required."
                if topic_terms
                else "The media concept did not provide an extractable EXACT TOPIC."
            )
        )
    )

    # NARRATION WORD COUNT

    narration = extract_narration(media)
    narration_words = count_words(narration)

    checks.append(
        check_result(
            "Narration word count",
            125 <= narration_words <= 140,
            f"Detected {narration_words} words; required 125-140."
        )
    )

    # REQUESTED LANGUAGE — Georgian requests must not silently receive English narration.
    if re.search(r"[\u10A0-\u10FF]", task_text) or re.search(r"\bgeorgian\b|ქართულ", task_text):
        language_passed = bool(re.search(r"[\u10A0-\u10FF]", narration))
        checks.append(
            check_result(
                "Narration language",
                language_passed,
                "Georgian narration is required by the CEO task."
                if language_passed
                else "The CEO requested Georgian, but the narration contains no Georgian script."
            )
        )

    # SIX VISUAL SCENES

    visual_text = extract_visual_text(media)
    visual_ranges = extract_visual_ranges(visual_text)

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

    # REQUIRED CONTENT SECTIONS

    final_script = extract_final_script(media)

    required_sections = [
        "video title",
        "exact topic",
        "hook",
        "script",
        "visual directions",
        "facts to verify"
    ]

    missing_sections = [
        section
        for section in required_sections
        if not re.search(
            r"(?im)^\s*(?:#{1,6}\s*)?(?:\*\*)?"
            + re.escape(section)
            + r"\s*:",
            final_script
        )
    ]

    checks.append(
        check_result(
            "Required content sections",
            not missing_sections,
            (
                "Missing: " + ", ".join(missing_sections)
                if missing_sections
                else "All required sections detected."
            )
        )
    )

    # NARRATION COMPLETENESS

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
        "passed": all(item["passed"] for item in checks)
    }


# ==================================================
# AUDITOR 2: EVIDENCE AUDITOR
# ==================================================

def evidence_auditor(media):
    checks = []

    # SOURCE VERIFICATION

    sources = collect_sources(media)

    source_urls = []
    source_statuses = []

    for source in sources:
        url = source.get("url")

        if url:
            source_urls.append(url)

        status = source.get("verification_status", "")

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
                f"statuses: {source_statuses}. "
                "URL structure does not prove source verification."
            )
        )
    )

    # FACT CHECK REPORT EXISTENCE

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
    ).strip()

    report_present = bool(fact_check_text)

    statuses = extract_fact_check_statuses(
        fact_check_text
    )

    statuses_present = bool(statuses)

    checks.append(
        check_result(
            "Fact-check report present",
            report_present,
            (
                "A fact-check report was supplied."
                if report_present
                else "Fact-check report is missing or empty."
            )
        )
    )

    checks.append(
        check_result(
            "Fact-check statuses present",
            statuses_present,
            (
                f"Detected {len(statuses)} explicit claim statuses."
                if statuses_present
                else "No explicit VERIFIED, NEEDS SOURCE or CONTRADICTED statuses found."
            )
        )
    )

    # FACT CHECK COVERAGE

    has_verified = "VERIFIED" in statuses

    checks.append(
        check_result(
            "Fact-check coverage",
            statuses_present and has_verified,
            (
                "At least one explicitly VERIFIED claim is required."
                if not has_verified
                else "At least one explicitly VERIFIED claim was reported."
            )
        )
    )

    # UNSUPPORTED CLAIMS
    # Missing report or missing statuses MUST FAIL.

    has_needs_source = "NEEDS SOURCE" in statuses

    unsupported_passed = (
        statuses_present
        and not has_needs_source
    )

    checks.append(
        check_result(
            "Unsupported claims",
            unsupported_passed,
            (
                "Claims marked NEEDS SOURCE were found."
                if has_needs_source
                else (
                    "No NEEDS SOURCE claims found in a present report."
                    if unsupported_passed
                    else "Cannot pass: fact-check report or explicit statuses are missing."
                )
            )
        )
    )

    # CONTRADICTION DETECTION
    # Missing report or missing statuses MUST FAIL.

    has_contradicted = "CONTRADICTED" in statuses

    contradiction_passed = (
        statuses_present
        and not has_contradicted
    )

    checks.append(
        check_result(
            "Contradiction detection",
            contradiction_passed,
            (
                "Claims explicitly marked CONTRADICTED were found."
                if has_contradicted
                else (
                    "No CONTRADICTED claims found in a present report."
                    if contradiction_passed
                    else "Cannot pass: fact-check report or explicit statuses are missing."
                )
            )
        )
    )

    # URL STRUCTURE

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
        "passed": all(item["passed"] for item in checks)
    }


# ==================================================
# AUDITOR 3: INTEGRITY AUDITOR
# ==================================================

def integrity_auditor(media):
    checks = []

    # DEPARTMENT IDENTITY

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

    # MEDIA STATUS

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

    # PUBLICATION SAFETY

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

    # RESULT STRUCTURE

    checks.append(
        check_result(
            "Result structure",
            isinstance(media, dict),
            "Media result must be a dictionary."
        )
    )

    # RESEARCH DATA

    research_values = find_nested_values(
        media,
        {"research"}
    )

    research_present = any(
        isinstance(value, dict) and bool(value)
        for value in research_values
    )

    checks.append(
        check_result(
            "Research data structure",
            research_present,
            "Research results must be present."
        )
    )

    # SPECIALIST OUTPUT

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
        "passed": all(item["passed"] for item in checks)
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
            "publication_approved": False,
            "final_decision": "CEO_APPROVAL_REQUIRED"
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

        # Audit NEVER approves publication.
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



# ==================================================
# GENERAL ORGANIZATION HANDOFF AUDIT
# ==================================================

def run_general_audit(task, department_results):
    """Audit non-media department handoffs when no Media-specific package exists.

    Reuses the deterministic organization contract checks. This avoids treating
    the absence of a Media artifact as an Audit failure while retaining all
    department-specific safety and evidence gates.
    """
    from organization_quality import _check_department_result

    checks = []
    entries = department_results if isinstance(department_results, list) else []

    if not str(task or "").strip():
        checks.append(check_result(
            "Original CEO task",
            False,
            "The original CEO task is missing."
        ))

    if not entries:
        checks.append(check_result(
            "Department handoff availability",
            False,
            "No completed department results were supplied for independent audit."
        ))

    seen_departments = set()
    for index, result in enumerate(entries):
        if not isinstance(result, dict):
            checks.append(check_result(
                f"Department result {index + 1}",
                False,
                "Department result is not a valid object."
            ))
            continue

        department = str(result.get("department") or "").strip().lower()
        if not department or department == "audit":
            checks.append(check_result(
                f"Department result {index + 1}",
                False,
                "Department identity is missing or invalid for this audit input."
            ))
            continue

        if department in seen_departments:
            checks.append(check_result(
                f"{department} handoff uniqueness",
                False,
                "Duplicate department results were supplied."
            ))
            continue
        seen_departments.add(department)

        issues = _check_department_result(department, result)
        checks.append(check_result(
            f"{department} handoff integrity",
            not issues,
            "All deterministic department contract checks passed."
            if not issues
            else "; ".join(str(issue) for issue in issues[:12])
        ))

    failed_checks = [item for item in checks if not item["passed"]]
    auditor = {
        "auditor": "Organization Handoff Auditor",
        "checks": checks,
        "passed": bool(checks) and not failed_checks,
    }
    return {
        "department": "audit",
        "status": "PASSED_WITH_LIMITATIONS" if checks and not failed_checks else "REVIEW_REQUIRED",
        "auditors": [auditor],
        "summary": {
            "total_checks": len(checks),
            "passed_checks": len(checks) - len(failed_checks),
            "failed_checks": len(failed_checks),
        },
        "failed_checks": [
            {"auditor": auditor["auditor"], **item}
            for item in failed_checks
        ],
        "publication_approved": False,
        "final_decision": "CEO_APPROVAL_REQUIRED",
        "message": (
            "დეპარტამენტების გადაბარების შემოწმება დასრულდა; ადამიანური დამტკიცება კვლავ სავალდებულოა."
            if not failed_checks and checks
            else "აუდიტმა აღმოაჩინა გადაბარების ან ხარისხის შეუსაბამობები; საჭიროა გადახედვა."
        ),
        "requires_ceo_approval": True,
        "execution_authorized": False,
        "execution_performed": False,
    }
