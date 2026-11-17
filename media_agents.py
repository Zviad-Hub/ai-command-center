
import re

from ai_brain import ask_ai
from error_diagnostics import safe_error_code
from research_agent import run_research


# ==================================================
# CONFIGURATION
# ==================================================

REQUIRED_TIMESTAMPS = [
    ("0:00", "0:10"),
    ("0:10", "0:20"),
    ("0:20", "0:30"),
    ("0:30", "0:40"),
    ("0:40", "0:50"),
    ("0:50", "1:00")
]

MIN_WORDS = 125
MAX_WORDS = 140


# ==================================================
# TEXT UTILITIES
# ==================================================

def requested_language_instruction(task):
    """Keep generated creative content in the CEO request's language."""
    task_text = str(task or "")
    if re.search(r"[\u10A0-\u10FF]", task_text):
        language = "Georgian"
    else:
        language = "the same language as the CEO's original request"

    return (
        "LANGUAGE REQUIREMENT (MANDATORY):\n"
        f"- Write all user-facing creative content in {language}.\n"
        "- The narration, hook, title, visual descriptions, concept, and editorial "
        "explanations must use that language.\n"
        "- Keep the required structural headings and machine-readable status labels "
        "in English exactly as specified, so automated validation remains reliable.\n"
        "- Do not translate the narration into English unless the CEO explicitly "
        "requests English."
    )


def narration_matches_requested_language(task, narration):
    """Return False when a Georgian request receives non-Georgian narration."""
    if re.search(r"[\u10A0-\u10FF]", str(task or "")):
        return bool(re.search(r"[\u10A0-\u10FF]", str(narration or "")))
    return True


def normalize_text(text):
    text = str(text or "")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def normalize_dashes(text):
    return re.sub(r"[‐‑‒–—−]", "-", str(text or ""))


def clean_markdown(text):
    text = str(text or "")
    text = re.sub(r"\*\*", "", text)
    text = re.sub(r"__", "", text)
    return text.strip()


def count_words(text):
    return len(
        re.findall(
            r"\b[\w’'-]+\b",
            clean_markdown(text),
            flags=re.UNICODE
        )
    )


def has_heading(text, heading):
    text = clean_markdown(text).upper()
    pattern = (
        r"(?m)^\s*(?:#{1,6}\s*)?"
        + re.escape(heading.upper())
        + r"\s*:?\s*$"
    )
    return bool(re.search(pattern, text))


# ==================================================
# NARRATION EXTRACTION
# ==================================================

def extract_narration(text):
    text = normalize_text(text)

    pattern = (
        r"(?im)^\s*(?:[-*]\s*)?(?:#{1,6}\s*)?"
        r"(?:\*\*)?(?:SCRIPT|NARRATION)"
        r"(?:\s*\([^)]*\))?\s*:?\s*(?:\*\*)?\s*"
        r"(.*?)"
        r"(?=^\s*(?:[-*]\s*)?(?:#{1,6}\s*)?"
        r"(?:\*\*)?VISUAL DIRECTIONS\s*:?(?:\*\*)?\s*|"
        r"^\s*(?:[-*]\s*)?(?:#{1,6}\s*)?"
        r"(?:\*\*)?FACTS TO VERIFY\s*:|"
        r"\Z)"
    )

    match = re.search(
        pattern,
        text,
        re.IGNORECASE | re.MULTILINE | re.DOTALL
    )

    return clean_markdown(match.group(1)) if match else ""


# ==================================================
# VISUAL EXTRACTION
# ==================================================

def extract_visual_section(text):
    text = normalize_text(text)

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

    return re.search(
        pattern,
        text,
        re.IGNORECASE | re.MULTILINE | re.DOTALL
    )


def extract_visual_ranges(text):
    text = normalize_dashes(text)

    return re.findall(
        r"(?m)^\s*(?:[-*]\s*)?"
        r"(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})(?!\d)",
        text
    )


def count_visual_scenes(text):
    section = extract_visual_section(text)

    if not section:
        return 0

    return len(extract_visual_ranges(section.group(1)))


def check_timestamps(text):
    section = extract_visual_section(text)

    if not section:
        return False

    return (
        extract_visual_ranges(section.group(1))
        == REQUIRED_TIMESTAMPS
    )


# ==================================================
# SCRIPT VALIDATION
# ==================================================

def validate_script(text):
    narration = extract_narration(text)
    section = extract_visual_section(text)

    visual_ranges = (
        extract_visual_ranges(section.group(1))
        if section else []
    )

    words = count_words(narration)

    return {
        "narration_found": bool(narration.strip()),
        "narration_word_count": words,
        "word_count_passed": MIN_WORDS <= words <= MAX_WORDS,
        "visual_section_found": section is not None,
        "visual_scene_count": len(visual_ranges),
        "visual_scene_count_passed": len(visual_ranges) == 6,
        "timestamps_passed": visual_ranges == REQUIRED_TIMESTAMPS,
        "visual_ranges": visual_ranges
    }


# ==================================================
# REFUSAL DETECTION
# ==================================================

def is_refusal(text):
    text = str(text or "").lower()

    phrases = [
        "i'm sorry",
        "i am sorry",
        "i cannot fulfill",
        "i can't fulfill",
        "i cannot help",
        "i can't help",
        "i'm unable to",
        "i am unable to"
    ]

    return any(phrase in text for phrase in phrases)


# ==================================================
# RESEARCH SERIALIZATION
# ==================================================

def serialize_research(research, max_chars=14000):
    if not isinstance(research, dict):
        return "INVALID RESEARCH DATA"

    sources = research.get("sources", [])

    if not isinstance(sources, list):
        return "NO VALID SOURCE LIST"

    output = [
        "RESEARCH STATUS: " + str(research.get("status", "UNKNOWN")),
        "EXTRACTED TOPIC: " + str(research.get("extracted_topic", "UNKNOWN")),
        "SOURCE COUNT: " + str(len(sources)),
        "",
        "EVIDENCE RULES:",
        "- Supplied research is not automatically verified.",
        "- URL verification and claim verification are separate.",
        "- Never claim to have independently opened a URL.",
        "- Use only supplied source content.",
        "- Search snippets are weaker than full-page extracts.",
        "- Never invent facts, quotations or evidence.",
        ""
    ]

    used = sum(len(item) for item in output)
    included = 0

    for index, source in enumerate(sources, start=1):
        if not isinstance(source, dict):
            continue

        content = str(source.get("content", "")).strip()

        if not content:
            continue

        block = (
            f"SOURCE {index}\n"
            f"TITLE: {source.get('title', 'Unknown title')}\n"
            f"URL: {source.get('url', '')}\n"
            f"CONTENT TYPE: {source.get('content_type', 'UNKNOWN')}\n"
            f"CLAIM EVIDENCE STATUS: "
            f"{source.get('verification_status', 'NOT_VERIFIED')}\n"
            f"URL VERIFICATION STATUS: "
            f"{source.get('url_verification_status', 'NOT_INDEPENDENTLY_VERIFIED')}\n"
            f"SUPPLIED CONTENT:\n{content[:1200]}\n"
            + "-" * 40 + "\n"
        )

        remaining = max_chars - used

        if remaining <= 300:
            break

        output.append(block[:remaining])
        used += min(len(block), remaining)
        included += 1

        if len(block) > remaining:
            break

    if not included:
        output.append("No usable source excerpts were supplied.")

    return "\n".join(output)


def has_usable_research(research):
    if not isinstance(research, dict):
        return False

    sources = research.get("sources", [])

    if not isinstance(sources, list):
        return False

    return any(
        isinstance(source, dict)
        and str(source.get("content", "")).strip()
        for source in sources
    )


def count_unverified_sources(research):
    sources = research.get("sources", [])

    if not isinstance(sources, list):
        return 0

    return sum(
        1 for source in sources
        if isinstance(source, dict)
        and str(source.get("verification_status", "NOT_VERIFIED")).upper()
        not in ("VERIFIED", "CONFIRMED")
    )


# ==================================================
# ERROR RESULT
# ==================================================

def build_error_result(task, stage, error, partial=None):
    partial = partial or {}

    return {
        "department": "media",
        "status": "ERROR",
        "failed_stage": stage,
        "error_type": type(error).__name__,
        "error_code": (
            "SCRIPTWRITER_OUTPUT_UNPARSEABLE"
            if stage == "Scriptwriter" and "narration" in str(error).lower()
            else "SCRIPTWRITER_EMPTY_OUTPUT"
            if stage == "Scriptwriter" and "empty" in str(error).lower()
            else (
                f"{stage.upper().replace(' ', '_')}_{safe_error_code(error)}"
                if safe_error_code(error) != "AGENT_PROCESSING_ERROR"
                else f"{stage.upper().replace(' ', '_')}_FAILED"
            )
        ),
        "message": f"{stage} failed: {str(error)}",
        "original_ceo_topic": task,
        "concept": partial.get("concept", ""),
        "script": partial.get("script", ""),
        "edited_script": partial.get("edited_script", ""),
        "initial_fact_check": partial.get("initial_fact_check", ""),
        "fact_check": partial.get("fact_check", ""),
        "research": partial.get(
            "research",
            {"status": "NOT_STARTED", "sources": []}
        ),
        "narration_word_count": partial.get("narration_word_count", 0),
        "validation": partial.get("validation", {}),
        "publication_approved": False,
        "specialists": partial.get("specialists", []),
        "warnings": [
            f"Pipeline stopped during: {stage}.",
            "Previously completed work has been preserved.",
            "CEO review is required.",
            "Publication is not approved."
        ]
    }


# ==================================================
# 1. CREATIVE STRATEGIST
# ==================================================

def creative_strategist(task, research):
    print("\n[CREATIVE STRATEGIST] Creating concept...")

    prompt = """
You are a professional YouTube Shorts Creative Strategist.

The CEO's original topic is the final authority.

Create exactly ONE concept about that exact topic.

Do not change or expand the topic.
Do not write the full narration.
Do not invent historical facts.
Do not treat snippets as verified evidence.
Do not invent numbers, dates, names or quotations.
Use uncertainty labels where evidence is insufficient.

Return a concise concept containing:
- Exact topic
- One video concept
- One hook
- Key questions to investigate
- Supported historical details
- Uncertain details

Do not create alternative concepts.
Maximum 220 words.
"""

    prompt += "\n\n" + requested_language_instruction(task)

    user_prompt = (
        "CEO ORIGINAL REQUEST:\n"
        + str(task)
        + "\n\nSUPPLIED RESEARCH:\n"
        + serialize_research(research)
    )

    result = ask_ai(prompt, user_prompt)

    if not isinstance(result, str) or not result.strip():
        raise RuntimeError("Creative Strategist returned empty output.")

    result = result.strip()

    if is_refusal(result):
        raise RuntimeError("Creative Strategist refused the task.")

    # IMPORTANT:
    # Missing headings must never stop the entire pipeline.
    # Preserve the model's useful response and normalize its format.

    required = [
        "EXACT TOPIC:",
        "VIDEO CONCEPT:",
        "HOOK:",
        "KEY QUESTIONS TO INVESTIGATE:"
    ]

    missing = [
        heading for heading in required
        if heading.lower() not in clean_markdown(result).lower()
    ]

    if missing:
        result = (
            "EXACT TOPIC:\n"
            + str(task)
            + "\n\nVIDEO CONCEPT:\n"
            + result
            + "\n\nHOOK:\n"
            + "Investigate the central historical mystery using "
              "evidence rather than assumptions."
            + "\n\nKEY QUESTIONS TO INVESTIGATE:\n"
            + "Which details are supported by the supplied historical "
              "evidence, and which remain uncertain?"
            + "\n\nSUPPORTED HISTORICAL DETAILS:\n"
            + "Use only details directly supported by supplied research."
            + "\n\nUNCERTAIN DETAILS:\n"
            + "Claims without sufficient supplied evidence require "
              "further verification."
        )

        print(
            "[CREATIVE STRATEGIST] Output headings normalized. "
            "Pipeline will continue."
        )

    print("[CREATIVE STRATEGIST] Concept completed.")

    return result


# ==================================================
# 2. SCRIPTWRITER
# ==================================================

def scriptwriter(task, concept, research):
    print("\n[SCRIPTWRITER] Writing script...")

    prompt = """
You are a professional historical YouTube Shorts Scriptwriter.

Create exactly ONE YouTube Shorts video script.

TOPIC:
The exact topic in the CEO request is mandatory.
Never replace or expand it.

NARRATION:
- 125-140 spoken words.
- Aim for approximately 132 words.
- Natural, engaging spoken language matching the CEO request.
- Do not count headings or visual directions.

HISTORICAL ACCURACY:
- Use supplied research only.
- Never invent facts, dates, names, numbers, quotations or events.
- Do not present theories as established facts.
- Mark uncertain claims [NEEDS SOURCE].
- Do not invent source references.
- Search snippets are not verified evidence.

VISUALS:
Create exactly six scenes.
Use each timestamp exactly once, in this order:

0:00-0:10
0:10-0:20
0:20-0:30
0:30-0:40
0:40-0:50
0:50-1:00

Each scene must describe one clear visual.
Visuals must match the narration.
Do not depict invented evidence as historical fact.

Return these sections:

VIDEO TITLE:
EXACT TOPIC:
HOOK:
SCRIPT:
VISUAL DIRECTIONS:
FACTS TO VERIFY:

Count the narration words before returning.
"""

    prompt += "\n\n" + requested_language_instruction(task)

    user_prompt = (
        "CEO ORIGINAL REQUEST:\n"
        + str(task)
        + "\n\nAPPROVED CONCEPT:\n"
        + str(concept)
        + "\n\nSUPPLIED RESEARCH:\n"
        + serialize_research(research)
    )

    result = ask_ai(prompt, user_prompt)

    if not isinstance(result, str) or not result.strip():
        raise RuntimeError("Scriptwriter returned empty output.")

    result = result.strip()
    validation = validate_script(result)

    # Models sometimes omit the colon or use a Markdown heading. The parser
    # accepts both forms; if narration is still absent, make one bounded
    # format-only repair attempt before failing the stage.
    if (
        not validation["narration_found"]
        or not narration_matches_requested_language(
            task, extract_narration(result)
        )
    ):
        repair_prompt = """
Reformat the supplied response as a complete historical YouTube Shorts script.
Do not add, remove, or alter historical claims. Do not invent facts.
Preserve the exact CEO topic and original narration wording wherever possible.
Return these exact sections, with a colon after each heading:
VIDEO TITLE:
EXACT TOPIC:
HOOK:
SCRIPT:
VISUAL DIRECTIONS:
FACTS TO VERIFY:
The SCRIPT section must contain the spoken narration. Include all six timestamped
visual scenes if they exist in the supplied response. If the original response
contains no narration, say NO NARRATION PROVIDED rather than inventing one.
"""
        repair_prompt += "\n\n" + requested_language_instruction(task)
        repaired = ask_ai(
            repair_prompt,
            "CEO ORIGINAL REQUEST:\n" + str(task)
            + "\n\nORIGINAL SCRIPTWRITER RESPONSE:\n" + result
        )
        if isinstance(repaired, str) and repaired.strip():
            repaired = repaired.strip()
            repaired_validation = validate_script(repaired)
            if (
                repaired_validation["narration_found"]
                and narration_matches_requested_language(
                    task, extract_narration(repaired)
                )
            ):
                result = repaired
                validation = repaired_validation

    if not validation["narration_found"]:
        raise RuntimeError(
            "Scriptwriter response contained no extractable narration after one format-repair attempt."
        )

    if not narration_matches_requested_language(task, extract_narration(result)):
        raise RuntimeError(
            "Scriptwriter narration language does not match the CEO request."
        )

    print("[SCRIPTWRITER] Narration words:", validation["narration_word_count"])
    print("[SCRIPTWRITER] Visual scenes:", validation["visual_scene_count"])

    return result


# ==================================================
# 3. QUALITY EDITOR
# ==================================================

def quality_editor(task, script):
    print("\n[QUALITY EDITOR] Reviewing script...")

    prompt = """
You are an independent professional Quality Editor.

Improve the supplied script without changing its topic.

Check:
1. Exact topic preservation.
2. Grammar and clarity in the requested language.
3. Narration word count.
4. Unsupported historical claims.
5. Invented or misleading details.
6. Exactly six visual scenes.
7. Correct timestamps.
8. Consistency between narration and visuals.

Rules:
- Do not add historical facts.
- Do not invent dates, names, numbers or quotations.
- Preserve uncertainty labels.
- Do not turn theories into facts.
- Keep exactly six visual scenes.
- Keep all six required timestamps in order.
- Narration must contain 125-140 words.
- Do not create another concept.

Return a complete edited script with these exact headings:

SCRIPT:
VISUAL DIRECTIONS:
FACTS TO VERIFY:

You may include a short editor review before the script.
"""

    prompt += "\n\n" + requested_language_instruction(task)
    result = ask_ai(
        prompt,
        "CEO ORIGINAL REQUEST:\n"
        + str(task)
        + "\n\nORIGINAL SCRIPT:\n"
        + str(script)
    )

    if not isinstance(result, str) or not result.strip():
        raise RuntimeError("Quality Editor returned empty output.")

    edited = result.strip()
    validation = validate_script(edited)

    if not validation["narration_found"]:
        raise RuntimeError(
            "Quality Editor did not return readable narration."
        )

    if not narration_matches_requested_language(task, extract_narration(edited)):
        raise RuntimeError(
            "Quality Editor changed the narration language requested by the CEO."
        )

    if not validation["word_count_passed"]:
        repair_prompt = """
Correct the narration length in the supplied complete script.

Narration must contain 125-140 words.

Preserve:
- Exact CEO topic.
- Historical accuracy.
- Uncertainty labels.
- All six visual scenes.
- All six exact timestamps.

Do not invent facts.
Do not add unsupported claims.
Do not create another script.

Return the COMPLETE script using:

SCRIPT:
VISUAL DIRECTIONS:
FACTS TO VERIFY:
"""

        repair_prompt += "\n\n" + requested_language_instruction(task)
        repaired = ask_ai(
            repair_prompt,
            "CEO TOPIC:\n"
            + str(task)
            + "\n\nCURRENT SCRIPT:\n"
            + edited
            + "\n\nCURRENT WORD COUNT: "
            + str(validation["narration_word_count"])
        )

        if isinstance(repaired, str) and repaired.strip():
            repaired = repaired.strip()

            if (
                validate_script(repaired)["narration_found"]
                and narration_matches_requested_language(
                    task, extract_narration(repaired)
                )
            ):
                edited = repaired

    if not narration_matches_requested_language(task, extract_narration(edited)):
        raise RuntimeError(
            "Quality Editor narration language does not match the CEO request."
        )

    final_validation = validate_script(edited)

    print(
        "[QUALITY EDITOR] Final narration words:",
        final_validation["narration_word_count"]
    )

    print(
        "[QUALITY EDITOR] Final visual scenes:",
        final_validation["visual_scene_count"]
    )

    return edited


# ==================================================
# 4. INDEPENDENT FACT-CHECKER
# ==================================================

def fact_checker(task, script, research):
    print("\n[FACT CHECKER] Checking historical claims...")

    prompt = """
You are a STRICT independent historical fact-checker.

Use ONLY the supplied source excerpts.

Check every important historical claim in the narration.

Rules:
1. A URL alone is not evidence.
2. A source title or domain alone is not evidence.
3. Evidence must directly support the specific claim.
4. Never invent source titles, URLs, quotations or evidence.
5. Never claim to have independently opened a URL.
6. Do not mark a claim VERIFIED without direct supporting content.
7. If evidence is insufficient, mark NEEDS SOURCE.
8. Use CONTRADICTED only when supplied content directly contradicts it.
9. Distinguish full-page extracts from search snippets.
10. URL verification and claim verification are separate.
11. Never approve publication.

For every important claim return:

CLAIM:
STATUS: VERIFIED / NEEDS SOURCE / CONTRADICTED
EVIDENCE EXCERPT:
REASON:
SOURCE TITLE:
SOURCE URL:

If no supplied content directly supports a claim:
STATUS: NEEDS SOURCE
EVIDENCE EXCERPT: NONE
SOURCE TITLE: NONE
SOURCE URL: NONE

Return:

FACT CHECK RESULTS:
UNSUPPORTED CLAIMS:
CONTRADICTED CLAIMS:
OVERALL RESULT:

If any important claim needs a source or is contradicted,
OVERALL RESULT must be REVIEW REQUIRED.

If no claims can be checked, explicitly say so.
"""

    prompt += "\n\n" + requested_language_instruction(task)
    result = ask_ai(
        prompt,
        "CEO ORIGINAL REQUEST:\n"
        + str(task)
        + "\n\nSCRIPT TO CHECK:\n"
        + str(script)
        + "\n\nSUPPLIED RESEARCH:\n"
        + serialize_research(research)
    )

    if not isinstance(result, str) or not result.strip():
        raise RuntimeError("Fact-Checker returned empty output.")

    return result.strip()


# ==================================================
# 5. EVIDENCE-BASED SCRIPT EDITOR
# ==================================================

def evidence_based_editor(task, script, research, fact_check):
    print("\n[EVIDENCE EDITOR] Correcting unsupported claims...")

    prompt = """
You are an independent historical evidence-based script editor.

The CEO's exact topic is locked.

Use ONLY supplied source excerpts and fact-check results.

Rules:
1. Remove or rewrite claims marked NEEDS SOURCE.
2. Remove claims that supplied evidence cannot support.
3. Remove claims marked CONTRADICTED.
4. Never turn an unconfirmed theory into a fact.
5. Never invent dates, numbers, names, quotations or events.
6. Never invent evidence or citations.
7. Preserve directly supported facts.
8. Do not add claims merely to reach the word count.
9. Preserve the exact CEO topic.
10. Preserve exactly six visual scenes.
11. Preserve the six exact timestamps in order.
12. Make visuals consistent with corrected narration.
13. Never claim publication is approved.

Aim for 125-140 narration words ONLY if the evidence allows it.
Accuracy is more important than word count.

Return a complete script with:

EVIDENCE EDITOR REVIEW:
REMOVED UNSUPPORTED CLAIMS:
RETAINED SUPPORTED CLAIMS:
SCRIPT:
VISUAL DIRECTIONS:
FACTS TO VERIFY:
"""

    prompt += "\n\n" + requested_language_instruction(task)
    result = ask_ai(
        prompt,
        "CEO ORIGINAL REQUEST:\n"
        + str(task)
        + "\n\nCURRENT SCRIPT:\n"
        + str(script)
        + "\n\nFACT CHECK RESULTS:\n"
        + str(fact_check)
        + "\n\nSUPPLIED RESEARCH:\n"
        + serialize_research(research)
    )

    if not isinstance(result, str) or not result.strip():
        raise RuntimeError("Evidence-Based Editor returned empty output.")

    edited = result.strip()

    if not validate_script(edited)["narration_found"]:
        raise RuntimeError(
            "Evidence Editor did not return readable narration."
        )

    if not narration_matches_requested_language(task, extract_narration(edited)):
        raise RuntimeError(
            "Evidence Editor changed the narration language requested by the CEO."
        )

    validation = validate_script(edited)

    print("[EVIDENCE EDITOR] Narration words:", validation["narration_word_count"])
    print("[EVIDENCE EDITOR] Visual scenes:", validation["visual_scene_count"])

    return edited


# ==================================================
# 6. MEDIA DEPARTMENT MANAGER
# ==================================================

def run_media_department(task):
    print("\n" + "=" * 55)
    print("MEDIA DEPARTMENT STARTED")
    print("=" * 55)

    partial = {
        "concept": "",
        "script": "",
        "edited_script": "",
        "initial_fact_check": "",
        "fact_check": "",
        "research": {
            "status": "NOT_STARTED",
            "sources": []
        },
        "narration_word_count": 0,
        "validation": {},
        "specialists": []
    }

    stage = "Initialization"

    try:
        # STEP 1: RESEARCH

        stage = "Research Agent"
        print("\n[MEDIA] Step 1: Research Agent...")

        research = run_research(task)

        if not isinstance(research, dict):
            raise RuntimeError("Research Agent returned invalid data.")

        partial["research"] = research

        research_status = str(
            research.get("status", "UNKNOWN")
        ).upper()

        sources = research.get("sources", [])
        source_count = len(sources) if isinstance(sources, list) else 0

        print("[MEDIA] Research status:", research_status)
        print("[MEDIA] Sources collected:", source_count)

        partial["specialists"].append("Research Agent")

        if research_status in ("ERROR", "NO_RESULTS"):
            raise RuntimeError(
                "Research Agent did not produce usable research. "
                + str(research.get("message", ""))
            )

        if not has_usable_research(research):
            raise RuntimeError(
                "Research Agent supplied no usable source content."
            )

        # STEP 2: CREATIVE STRATEGIST

        stage = "Creative Strategist"
        print("\n[MEDIA] Step 2: Creative Strategist...")

        concept = creative_strategist(task, research)

        partial["concept"] = concept
        partial["specialists"].append("Creative Strategist")

        # STEP 3: SCRIPTWRITER

        stage = "Scriptwriter"
        print("\n[MEDIA] Step 3: Scriptwriter...")

        script = scriptwriter(task, concept, research)

        partial["script"] = script
        partial["specialists"].append("Scriptwriter")

        # STEP 4: QUALITY EDITOR

        stage = "Quality Editor"
        print("\n[MEDIA] Step 4: Quality Editor...")

        edited_script = quality_editor(task, script)

        partial["edited_script"] = edited_script
        partial["specialists"].append("Quality Editor")

        # STEP 5: INITIAL FACT CHECK

        stage = "Initial Fact-Checker"
        print("\n[MEDIA] Step 5: Initial Fact-Checker...")

        initial_fact_check = fact_checker(
            task,
            edited_script,
            research
        )

        partial["initial_fact_check"] = initial_fact_check
        partial["specialists"].append("Independent Fact-Checker")

        # STEP 6: EVIDENCE EDITOR

        stage = "Evidence-Based Editor"
        print("\n[MEDIA] Step 6: Evidence-Based Editor...")

        evidence_edited_script = evidence_based_editor(
            task,
            edited_script,
            research,
            initial_fact_check
        )

        partial["edited_script"] = evidence_edited_script
        partial["specialists"].append("Evidence-Based Script Editor")

        # STEP 7: FINAL FACT CHECK

        stage = "Final Fact-Checker"
        print("\n[MEDIA] Step 7: Final Fact-Checker...")

        final_fact_check = fact_checker(
            task,
            evidence_edited_script,
            research
        )

        partial["fact_check"] = final_fact_check
        partial["specialists"].append("Final Fact-Checker")

        # STEP 8: FINAL VALIDATION

        stage = "Final Validation"

        validation = validate_script(evidence_edited_script)
        partial["validation"] = validation

        narration_words = validation["narration_word_count"]
        partial["narration_word_count"] = narration_words

        warnings = []

        if research_status != "COMPLETED":
            warnings.append(
                "Research did not report COMPLETED status."
            )

        unverified_count = count_unverified_sources(research)

        if unverified_count:
            warnings.append(
                f"{unverified_count} research sources are not marked "
                "VERIFIED or CONFIRMED. Their content must not be "
                "treated as independently verified."
            )

        if not validation["word_count_passed"]:
            warnings.append(
                "Narration does not meet the 125-140 word requirement."
            )

        if not validation["visual_scene_count_passed"]:
            warnings.append(
                "Final script does not contain exactly six visual scenes."
            )

        if not validation["timestamps_passed"]:
            warnings.append(
                "Final visual timestamps are missing or out of order."
            )

        if not validation["narration_found"]:
            warnings.append(
                "Final narration could not be extracted."
            )

        if not final_fact_check.strip():
            warnings.append("Final fact-check report is missing.")
        else:
            fact_upper = final_fact_check.upper()

            if "NEEDS SOURCE" in fact_upper:
                warnings.append(
                    "Final fact-check identified claims needing sources."
                )

            if "CONTRADICTED" in fact_upper:
                warnings.append(
                    "Final fact-check identified contradicted claims."
                )

            if "VERIFIED" not in fact_upper:
                warnings.append(
                    "Final fact-check contains no VERIFIED claim status."
                )

        # Publication is NEVER approved automatically.
        final_status = "REVIEW_REQUIRED"

        print("\n" + "=" * 55)
        print("MEDIA DEPARTMENT COMPLETED")
        print("NARRATION WORDS:", narration_words)
        print("VISUAL SCENES:", validation["visual_scene_count"])
        print("TIMESTAMPS PASSED:", validation["timestamps_passed"])
        print("PUBLICATION APPROVED: False")
        print("=" * 55)

        return {
            "department": "media",
            "status": final_status,
            "message": (
                "Media production, research, editing and final "
                "fact-check completed. CEO review is required."
            ),
            "original_ceo_topic": task,
            "concept": concept,
            "script": script,
            "edited_script": evidence_edited_script,
            "initial_fact_check": initial_fact_check,
            "narration_word_count": narration_words,
            "research": research,
            "fact_check": final_fact_check,
            "validation": validation,
            "warnings": warnings,
            "publication_approved": False,
            "specialists": partial["specialists"]
        }

    except Exception as error:
        print("\n[MEDIA] ERROR during stage:", stage)
        print("[MEDIA] ERROR details:", str(error))

        return build_error_result(
            task,
            stage,
            error,
            partial
        )
