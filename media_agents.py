
import re

from ai_brain import ask_ai
from research_agent import run_research


# ==================================================
# COMMON MEDIA UTILITIES
# ==================================================

REQUIRED_TIMESTAMPS = [
    "0:00-0:10",
    "0:10-0:20",
    "0:20-0:30",
    "0:30-0:40",
    "0:40-0:50",
    "0:50-1:00"
]


def extract_narration(text):

    text = str(text or "")

    match = re.search(
        r"^\s*\*{0,2}(?:SCRIPT|NARRATION)"
        r"(?:\s*\([^)]*\))?\s*:\*{0,2}\s*"
        r"(.*?)"
        r"(?=^\s*\*{0,2}VISUAL DIRECTIONS\s*:\*{0,2})",
        text,
        re.IGNORECASE | re.MULTILINE | re.DOTALL
    )

    if not match:
        return ""

    narration = match.group(1).strip()

    narration = re.sub(r"\*\*|__", "", narration)

    return narration


def count_words(text):

    return len(
        re.findall(r"\b[\w’'-]+\b", str(text or ""))
    )


def count_visual_scenes(text):

    text = str(text or "")

    section = re.search(
        r"^\s*\*{0,2}VISUAL DIRECTIONS\s*:\*{0,2}\s*"
        r"(.*?)(?=^\s*\*{0,2}(?:FACTS TO VERIFY|FACT CHECK|"
        r"EDITOR REVIEW|PROBLEMS|CORRECTIONS|FACTS STILL NEEDING)"
        r"\b)",
        text,
        re.IGNORECASE | re.MULTILINE | re.DOTALL
    )

    if not section:

        section = re.search(
            r"^\s*\*{0,2}VISUAL DIRECTIONS\s*:\*{0,2}\s*(.*)$",
            text,
            re.IGNORECASE | re.MULTILINE | re.DOTALL
        )

    if not section:
        return 0

    content = section.group(1)

    return len(
        re.findall(
            r"(?m)^\s*(?:[-*]\s*)?"
            r"(?:0:00-0:10|0:10-0:20|0:20-0:30|"
            r"0:30-0:40|0:40-0:50|0:50-1:00)\b",
            content
        )
    )


def check_timestamps(text):

    text = str(text or "")

    section = re.search(
        r"^\s*\*{0,2}VISUAL DIRECTIONS\s*:\*{0,2}\s*"
        r"(.*?)(?=^\s*\*{0,2}(?:FACTS TO VERIFY|FACT CHECK|"
        r"EDITOR REVIEW|PROBLEMS|CORRECTIONS|FACTS STILL NEEDING)"
        r"\b)",
        text,
        re.IGNORECASE | re.MULTILINE | re.DOTALL
    )

    if not section:

        section = re.search(
            r"^\s*\*{0,2}VISUAL DIRECTIONS\s*:\*{0,2}\s*(.*)$",
            text,
            re.IGNORECASE | re.MULTILINE | re.DOTALL
        )

    if not section:
        return False

    content = section.group(1)

    found = re.findall(
        r"(?m)^\s*(?:[-*]\s*)?"
        r"(\d:\d{2}-\d:\d{2})\b",
        content
    )

    return found == REQUIRED_TIMESTAMPS


def is_refusal(text):

    text = str(text or "").lower()

    refusal_phrases = [
        "i'm sorry",
        "i am sorry",
        "i cannot fulfill",
        "i can't fulfill",
        "i cannot help",
        "i can't help",
        "i'm unable to",
        "i am unable to"
    ]

    return any(
        phrase in text
        for phrase in refusal_phrases
    )


def serialize_research(research, max_chars=14000):

    """
    Pass actual supplied research content to downstream agents.

    Never convert candidate sources into verified sources.
    Never claim that a URL was independently opened.
    """

    if not isinstance(research, dict):
        return "INVALID RESEARCH DATA"

    sources = research.get("sources", [])

    if not isinstance(sources, list):
        return "NO VALID SOURCE LIST"

    output = [
        "RESEARCH STATUS: "
        + str(research.get("status", "UNKNOWN")),

        "EXTRACTED TOPIC: "
        + str(research.get("extracted_topic", "UNKNOWN")),

        "SOURCE COUNT: "
        + str(len(sources)),

        "",
        "IMPORTANT EVIDENCE RULES:",
        "- These are supplied research results.",
        "- A preferred domain is not proof of accuracy.",
        "- URL verification and claim verification are separate.",
        "- Do not claim to have independently opened a URL.",
        "- Use only the actual supplied content.",
        "- A search snippet is weaker than a full-page extract.",
        ""
    ]

    used = sum(len(item) for item in output)

    for index, source in enumerate(sources, start=1):

        if not isinstance(source, dict):
            continue

        title = str(source.get("title", "Unknown title"))
        url = str(source.get("url", ""))
        content = str(source.get("content", ""))
        content_type = str(
            source.get("content_type", "UNKNOWN")
        )
        verification = str(
            source.get("verification_status", "NOT_VERIFIED")
        )
        url_status = str(
            source.get(
                "url_verification_status",
                "NOT_INDEPENDENTLY_VERIFIED"
            )
        )

        if not content.strip():
            continue

        block = (
            f"SOURCE {index}\n"
            f"TITLE: {title}\n"
            f"URL: {url}\n"
            f"CONTENT TYPE: {content_type}\n"
            f"CLAIM EVIDENCE STATUS: {verification}\n"
            f"URL VERIFICATION STATUS: {url_status}\n"
            f"SUPPLIED CONTENT:\n"
            f"{content.strip()[:1200]}\n"
            f"{'-' * 40}\n"
        )

        if used + len(block) > max_chars:

            remaining = max_chars - used

            if remaining > 300:
                output.append(block[:remaining])

            break

        output.append(block)
        used += len(block)

    if len(output) <= 10:
        output.append("No usable source excerpts were supplied.")

    return "\n".join(output)


def validate_script(text):

    narration = extract_narration(text)
    words = count_words(narration)
    scenes = count_visual_scenes(text)
    timestamps_ok = check_timestamps(text)

    return {
        "narration_found": bool(narration),
        "narration_word_count": words,
        "word_count_passed": 125 <= words <= 140,
        "visual_scene_count": scenes,
        "visual_scene_count_passed": scenes == 6,
        "timestamps_passed": timestamps_ok
    }


def build_error_result(task, stage, error, partial=None):

    partial = partial or {}

    return {
        "department": "media",
        "status": "ERROR",
        "failed_stage": stage,
        "message": f"{stage} failed: {str(error)}",
        "original_ceo_topic": task,
        "concept": partial.get("concept", ""),
        "script": partial.get("script", ""),
        "edited_script": partial.get("edited_script", ""),
        "initial_fact_check": partial.get("initial_fact_check", ""),
        "fact_check": partial.get("fact_check", ""),
        "research": partial.get(
            "research",
            {
                "status": "NOT_STARTED",
                "sources": []
            }
        ),
        "narration_word_count": partial.get(
            "narration_word_count",
            0
        ),
        "publication_approved": False,
        "specialists": partial.get("specialists", []),
        "warnings": [
            "The Media Department did not complete all stages.",
            "CEO review is required.",
            "Publication is not approved."
        ]
    }


# ==================================================
# 1. RESEARCH-AWARE CREATIVE STRATEGIST
# ==================================================

def creative_strategist(task, research):

    print("\n[CREATIVE STRATEGIST] Creating research-based concept...")

    supplied_sources = serialize_research(research)

    prompt = """
You are a professional YouTube Shorts Creative Strategist.

THE CEO ORIGINAL REQUEST IS THE FINAL AUTHORITY.

STRICT RULES:

1. Preserve the exact topic requested by the CEO.
2. Never replace or expand the topic.
3. Create exactly ONE video concept.
4. Use supplied research to understand the subject.
5. Do not invent historical facts.
6. Do not treat search snippets as verified facts.
7. Uncertain details must be marked NEEDS SOURCE.
8. Do not invent sources or claim independent verification.
9. Do not write the full narration.
10. Do not create alternative concepts.

Return exactly:

EXACT TOPIC:
VIDEO CONCEPT:
HOOK:
KEY QUESTIONS TO INVESTIGATE:
SUPPORTED HISTORICAL DETAILS:
UNCERTAIN DETAILS:

Maximum 220 words.
Be specific and useful.
"""

    user_prompt = (
        "CEO ORIGINAL REQUEST:\n"
        + str(task)
        + "\n\nSUPPLIED RESEARCH:\n"
        + supplied_sources
    )

    result = ask_ai(prompt, user_prompt)

    if not isinstance(result, str) or not result.strip():
        raise RuntimeError("Creative Strategist returned empty output.")

    result = result.strip()

    required_sections = [
        "EXACT TOPIC:",
        "VIDEO CONCEPT:",
        "HOOK:",
        "KEY QUESTIONS TO INVESTIGATE:"
    ]

    if is_refusal(result):
        raise RuntimeError("Creative Strategist refused the task.")

    missing = [
        section for section in required_sections
        if section.lower() not in result.lower()
    ]

    if missing:
        raise RuntimeError(
            "Creative Strategist omitted required sections: "
            + ", ".join(missing)
        )

    print("[CREATIVE STRATEGIST] Concept completed.")

    return result


# ==================================================
# 2. SCRIPTWRITER
# ==================================================

def scriptwriter(task, concept, research):

    print("\n[SCRIPTWRITER] Writing research-based script...")

    supplied_sources = serialize_research(research)

    prompt = """
You are a professional historical YouTube Shorts Scriptwriter.

THE CEO ORIGINAL REQUEST IS THE FINAL AUTHORITY.

Create exactly ONE English YouTube Shorts script.

TOPIC LOCK:
- The exact CEO topic must never change.
- Do not introduce another subject.
- Do not create alternative scripts.

NARRATION:
- MUST contain 125-140 words.
- Target approximately 132 words.
- Write natural, engaging spoken English.
- Do not count headings or visual directions as narration.

HISTORICAL ACCURACY:
- Use supplied research as the available evidence.
- Never invent dates, names, numbers, quotations or events.
- Do not present theories as established facts.
- Mark uncertain claims [NEEDS SOURCE].
- Do not invent source references.
- A search snippet is not equivalent to a verified primary source.

VISUAL TIMELINE:
Create exactly six scenes.
Use these exact timestamps, once each, in this order:

0:00-0:10
0:10-0:20
0:20-0:30
0:30-0:40
0:40-0:50
0:50-1:00

Each scene must describe one clear visual.
Visuals must match the narration.
Do not invent visual evidence.

Return exactly:

VIDEO TITLE:
EXACT TOPIC:
HOOK:
SCRIPT:
VISUAL DIRECTIONS:
FACTS TO VERIFY:

Count narration words before returning.
Do not omit any section.
"""

    user_prompt = (
        "CEO ORIGINAL REQUEST:\n"
        + str(task)
        + "\n\nAPPROVED CONCEPT:\n"
        + str(concept)
        + "\n\nSUPPLIED RESEARCH:\n"
        + supplied_sources
    )

    result = ask_ai(prompt, user_prompt)

    if not isinstance(result, str) or not result.strip():
        raise RuntimeError("Scriptwriter returned empty output.")

    result = result.strip()

    validation = validate_script(result)

    if not validation["narration_found"]:
        raise RuntimeError(
            "Scriptwriter did not return a readable SCRIPT section."
        )

    print(
        "[SCRIPTWRITER] Narration words:",
        validation["narration_word_count"]
    )

    print(
        "[SCRIPTWRITER] Visual scenes:",
        validation["visual_scene_count"]
    )

    return result


# ==================================================
# 3. QUALITY EDITOR
# ==================================================

def quality_editor(task, script):

    print("\n[QUALITY EDITOR] Reviewing script...")

    prompt = """
You are an independent professional Quality Editor.

THE CEO ORIGINAL REQUEST IS THE FINAL AUTHORITY.

Improve the supplied script without changing its topic.

CHECK:
1. Exact topic preservation.
2. Natural English and grammar.
3. Narration word count.
4. Unsupported historical claims.
5. Misleading or invented details.
6. Exactly six visual scenes.
7. Correct visual timestamps.
8. Consistency between narration and visuals.

STRICT RULES:
- Do not add historical facts.
- Do not invent dates, names, numbers or quotations.
- Keep uncertainty labels.
- Do not turn theories into facts.
- Preserve the meaning of supported claims.
- Keep exactly six visual scenes.
- Use all six required timestamps in order.
- Narration MUST contain 125-140 words.
- Do not create another concept or script.
- Do not claim that facts are verified.

Return exactly:

TOPIC CHECK:
EDITOR REVIEW:
PROBLEMS:
CORRECTIONS:
EDITED SCRIPT:
FACTS STILL NEEDING VERIFICATION:

The EDITED SCRIPT must contain the complete narration
and all six timestamped visual directions.
"""

    user_prompt = (
        "CEO ORIGINAL REQUEST:\n"
        + str(task)
        + "\n\nORIGINAL SCRIPT:\n"
        + str(script)
    )

    edited = ask_ai(prompt, user_prompt)

    if not isinstance(edited, str) or not edited.strip():
        raise RuntimeError("Quality Editor returned empty output.")

    edited = edited.strip()

    validation = validate_script(edited)

    if not validation["narration_found"]:
        raise RuntimeError(
            "Quality Editor did not return a readable narration."
        )

    if not validation["word_count_passed"]:

        print(
            "[QUALITY EDITOR] Word count outside target:",
            validation["narration_word_count"]
        )

        repair_prompt = """
You are a professional YouTube Shorts Script Editor.

Correct ONLY the narration length in the supplied edited script.

MANDATORY:
- Narration must contain 125-140 words.
- Preserve the exact CEO topic.
- Preserve historical accuracy.
- Do not invent facts.
- Keep uncertainty labels.
- Preserve all six visual scenes and timestamps.
- Do not add another concept or script.

Return the COMPLETE corrected edited script.
Do not omit any section.
"""

        repair_input = (
            "CEO ORIGINAL REQUEST:\n"
            + str(task)
            + "\n\nCURRENT EDITED SCRIPT:\n"
            + edited
            + "\n\nCURRENT WORD COUNT: "
            + str(validation["narration_word_count"])
            + "\nREQUIRED: 125-140 words."
        )

        repaired = ask_ai(repair_prompt, repair_input)

        if isinstance(repaired, str) and repaired.strip():

            repaired = repaired.strip()
            repaired_validation = validate_script(repaired)

            if repaired_validation["narration_found"]:
                edited = repaired

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

    supplied_sources = serialize_research(research)

    prompt = """
You are a STRICT independent historical fact-checker.

THE CEO ORIGINAL TOPIC IS MANDATORY.

EVIDENCE RULES:

1. Use ONLY the supplied source excerpts.
2. Check every important historical claim in the narration.
3. Search-result URLs alone are NOT evidence.
4. A source title or domain alone is NOT evidence.
5. Evidence must directly support the specific claim.
6. Do not invent source titles, URLs, quotations or evidence.
7. Do not claim to have independently opened a URL.
8. Do not mark a claim VERIFIED unless supplied content
   directly supports that specific claim.
9. If evidence is insufficient, mark NEEDS SOURCE.
10. Use CONTRADICTED only when supplied content
    directly contradicts the claim.
11. Cite the exact supplied source title and URL when available.
12. Distinguish full-page extracts from search snippets.
13. URL verification and claim verification are separate.
14. Never approve publication.

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

Return exactly:

FACT CHECK RESULTS:
UNSUPPORTED CLAIMS:
CONTRADICTED CLAIMS:
OVERALL RESULT:

If any important claim is NEEDS SOURCE or CONTRADICTED,
OVERALL RESULT must be REVIEW REQUIRED.

Be concise but do not omit important claims.
"""

    user_prompt = (
        "CEO ORIGINAL REQUEST:\n"
        + str(task)
        + "\n\nFINAL SCRIPT TO CHECK:\n"
        + str(script)
        + "\n\nSUPPLIED RESEARCH EXCERPTS:\n"
        + supplied_sources
    )

    result = ask_ai(prompt, user_prompt)

    if not isinstance(result, str) or not result.strip():
        raise RuntimeError("Fact-Checker returned empty output.")

    return result.strip()


# ==================================================
# 5. EVIDENCE-BASED SCRIPT EDITOR
# ==================================================

def evidence_based_editor(task, script, research, fact_check):

    print("\n[EVIDENCE EDITOR] Correcting unsupported claims...")

    supplied_sources = serialize_research(research)

    prompt = """
You are an independent historical evidence-based script editor.

THE CEO ORIGINAL TOPIC IS LOCKED.

Your job is to correct the narration using ONLY:
1. Supplied source excerpts.
2. The independent fact-check results.

STRICT RULES:

1. Remove or rewrite claims marked NEEDS SOURCE.
2. Remove claims that supplied content cannot support.
3. Remove claims marked CONTRADICTED.
4. Never turn an unconfirmed theory into a historical fact.
5. Never invent dates, numbers, names, quotations or events.
6. Never invent evidence or citations.
7. Preserve facts directly supported by supplied content.
8. Do not add claims simply to reach the word count.
9. Preserve the exact CEO topic.
10. Preserve exactly six visual scenes.
11. Preserve the six required timestamps in their original order.
12. Make visuals consistent with the corrected narration.
13. Do not create another concept or video.
14. Do not claim that publication is approved.

If the evidence cannot support 125-140 words,
return the most accurate narration possible and explain why.

NARRATION TARGET:
125-140 words, if the evidence allows it.

Return exactly:

EVIDENCE EDITOR REVIEW:
REMOVED UNSUPPORTED CLAIMS:
RETAINED SUPPORTED CLAIMS:
EDITED SCRIPT:

The EDITED SCRIPT must contain:
- One complete narration.
- Exactly six timestamped visual scenes.
"""

    user_prompt = (
        "CEO ORIGINAL REQUEST:\n"
        + str(task)
        + "\n\nCURRENT SCRIPT:\n"
        + str(script)
        + "\n\nFACT CHECK RESULTS:\n"
        + str(fact_check)
        + "\n\nSUPPLIED RESEARCH:\n"
        + supplied_sources
    )

    result = ask_ai(prompt, user_prompt)

    if not isinstance(result, str) or not result.strip():
        raise RuntimeError(
            "Evidence-Based Editor returned empty output."
        )

    edited = result.strip()

    validation = validate_script(edited)

    if not validation["narration_found"]:
        raise RuntimeError(
            "Evidence Editor did not return a readable narration."
        )

    print(
        "[EVIDENCE EDITOR] Narration words:",
        validation["narration_word_count"]
    )

    print(
        "[EVIDENCE EDITOR] Visual scenes:",
        validation["visual_scene_count"]
    )

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
        "specialists": []
    }

    try:

        # STEP 1: RESEARCH FIRST

        print("\n[MEDIA] Step 1: Research Agent started...")

        research = run_research(task)

        if not isinstance(research, dict):

            research = {
                "status": "ERROR",
                "message": "Research Agent returned invalid data.",
                "sources": []
            }

        partial["research"] = research

        print(
            "[MEDIA] Research status:",
            research.get("status")
        )

        print(
            "[MEDIA] Sources collected:",
            research.get("source_count", 0)
        )

        partial["specialists"].append("Research Agent")

        # STEP 2: CREATIVE STRATEGIST

        print("\n[MEDIA] Step 2: Creative Strategist started...")

        concept = creative_strategist(task, research)

        partial["concept"] = concept
        partial["specialists"].append("Creative Strategist")

        # STEP 3: SCRIPTWRITER

        print("\n[MEDIA] Step 3: Scriptwriter started...")

        script = scriptwriter(task, concept, research)

        partial["script"] = script
        partial["specialists"].append("Scriptwriter")

        # STEP 4: QUALITY EDITOR

        print("\n[MEDIA] Step 4: Quality Editor started...")

        edited_script = quality_editor(task, script)

        partial["edited_script"] = edited_script
        partial["specialists"].append("Quality Editor")

        # STEP 5: INITIAL FACT CHECK

        print("\n[MEDIA] Step 5: Initial Fact-Checker started...")

        initial_fact_check = fact_checker(
            task,
            edited_script,
            research
        )

        partial["initial_fact_check"] = initial_fact_check
        partial["specialists"].append("Independent Fact-Checker")

        # STEP 6: EVIDENCE-BASED EDITOR

        print("\n[MEDIA] Step 6: Evidence-Based Editor started...")

        evidence_edited_script = evidence_based_editor(
            task,
            edited_script,
            research,
            initial_fact_check
        )

        partial["edited_script"] = evidence_edited_script
        partial["specialists"].append("Evidence-Based Script Editor")

        # STEP 7: FINAL FACT CHECK

        print("\n[MEDIA] Step 7: Final Fact-Checker started...")

        final_fact_check = fact_checker(
            task,
            evidence_edited_script,
            research
        )

        partial["fact_check"] = final_fact_check

        print("\n[MEDIA] Final fact-check completed.")

        # STEP 8: FINAL VALIDATION

        validation = validate_script(evidence_edited_script)

        narration_words = validation["narration_word_count"]

        partial["narration_word_count"] = narration_words

        warnings = []

        if research.get("status") != "COMPLETED":

            warnings.append(
                "Research did not complete with full-page extracts."
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

        print("\n" + "=" * 55)
        print("MEDIA DEPARTMENT COMPLETED")
        print("NARRATION WORDS:", narration_words)
        print("VISUAL SCENES:", validation["visual_scene_count"])
        print("PUBLICATION APPROVED: False")
        print("=" * 55)

        return {
            "department": "media",
            "status": "REVIEW_REQUIRED",
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

        print(
            "\n[MEDIA] ERROR during production:",
            str(error)
        )

        return build_error_result(
            task,
            "Media production pipeline",
            error,
            partial
        )
