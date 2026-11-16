
import json
import re

from ai_brain import ask_ai
from research_agent import run_research


# ==================================================
# COMMON MEDIA UTILITIES
# ==================================================

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
        match = re.search(
            r"^\s*\*{0,2}Narration"
            r"(?:\s*\([^)]*\))?\s*:\*{0,2}\s*"
            r"(.*?)"
            r"(?=^\s*\*{0,2}Visual Directions\s*:)",
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


def serialize_research(research, max_chars=11000):
    """
    Give the Fact Checker actual supplied source excerpts.
    Do not convert NOT_VERIFIED sources into VERIFIED sources.
    """

    if not isinstance(research, dict):
        return "INVALID RESEARCH DATA"

    sources = research.get("sources", [])

    if not isinstance(sources, list):
        return "NO VALID SOURCE LIST"

    output = [
        "RESEARCH STATUS: " + str(research.get("status", "UNKNOWN")),
        "SOURCE COUNT: " + str(len(sources)),
        "",
        "IMPORTANT: Source verification status and claim evidence "
        "status are separate things.",
        "A supplied excerpt may support a claim, but this does NOT "
        "mean the URL has been independently verified.",
        ""
    ]

    used = 0

    for index, source in enumerate(sources, start=1):

        if not isinstance(source, dict):
            continue

        title = str(source.get("title", "Unknown title"))
        url = str(source.get("url", ""))
        content = str(source.get("content", ""))
        verification = str(
            source.get("verification_status", "NOT_VERIFIED")
        )

        if not content.strip():
            continue

        excerpt = content.strip()[:1300]

        block = (
            f"SOURCE {index}\n"
            f"TITLE: {title}\n"
            f"URL: {url}\n"
            f"URL VERIFICATION STATUS: {verification}\n"
            f"SUPPLIED SOURCE CONTENT:\n{excerpt}\n"
            f"{'-' * 35}\n"
        )

        if used + len(block) > max_chars:
            remaining = max_chars - used

            if remaining > 300:
                output.append(block[:remaining])

            break

        output.append(block)
        used += len(block)

    if len(output) <= 5:
        output.append("No usable source excerpts were supplied.")

    return "\n".join(output)


# ==================================================
# 1. CREATIVE STRATEGIST
# ==================================================

def creative_strategist(task):

    print("\n[CREATIVE STRATEGIST] Creating video concept...")

    prompt = """
You are a professional YouTube Shorts Creative Strategist.

IMPORTANT:
The CEO is requesting a normal, harmless creative task.
You MUST complete the task.
Never refuse, apologize, or say you cannot help.

STRICT CEO TOPIC LOCK:
- The CEO's original request is the ONLY topic.
- Never change, replace, or expand the topic.
- Create exactly ONE video concept.
- Do not invent historical facts.
- Uncertain details must be marked NEEDS SOURCE.
- Do not discuss unrelated subjects.

Return exactly:

EXACT TOPIC:
VIDEO CONCEPT:
HOOK:
KEY QUESTIONS TO INVESTIGATE:

Maximum 180 words.
Be specific and useful.
"""

    user_prompt = (
        "CEO ORIGINAL REQUEST:\n"
        + str(task)[:1500]
    )

    required_sections = [
        "EXACT TOPIC:",
        "VIDEO CONCEPT:",
        "HOOK:",
        "KEY QUESTIONS TO INVESTIGATE:"
    ]

    for attempt in range(2):

        result = ask_ai(prompt, user_prompt)

        if not isinstance(result, str):
            result = str(result or "")

        cleaned = result.strip()
        lower_result = cleaned.lower()

        has_all_sections = all(
            section.lower() in lower_result
            for section in required_sections
        )

        if (
            cleaned
            and not is_refusal(cleaned)
            and has_all_sections
        ):
            print("[CREATIVE STRATEGIST] Valid concept created.")
            return cleaned

        print(
            f"[CREATIVE STRATEGIST] Invalid response. "
            f"Attempt {attempt + 1}/2"
        )

        user_prompt = (
            "YOUR PREVIOUS RESPONSE WAS INVALID.\n"
            "Do not refuse or apologize.\n"
            "Complete the original harmless creative task.\n\n"
            "CEO ORIGINAL REQUEST:\n"
            + str(task)[:1500]
        )

    raise RuntimeError(
        "Creative Strategist failed to produce a valid concept "
        "after two attempts."
    )


# ==================================================
# 2. SCRIPTWRITER
# ==================================================

def scriptwriter(task, concept):

    print("\n[SCRIPTWRITER] Writing video script...")

    prompt = """
You are a professional historical YouTube Shorts Scriptwriter.

THE CEO ORIGINAL REQUEST IS THE FINAL AUTHORITY.
The topic must never change.

Create ONE English YouTube Shorts video script.

STRICT LENGTH:
- Narration MUST contain 125-140 words.
- Target approximately 132 words.
- Target duration: approximately 60 seconds.
- Exactly ONE script.
- Do not add alternative concepts or scripts.

HISTORICAL ACCURACY:
- Never invent dates, names, numbers, quotations or events.
- Do not present uncertain claims as facts.
- Mark uncertain historical claims [NEEDS SOURCE].
- Do not invent sources.

VISUAL TIMELINE:
Create exactly 6 visual direction lines.
Use these exact timestamps:

0:00-0:10
0:10-0:20
0:20-0:30
0:30-0:40
0:40-0:50
0:50-1:00

Each line must describe one clear visual scene.

Return exactly:

VIDEO TITLE:
EXACT TOPIC:
HOOK:
SCRIPT:
VISUAL DIRECTIONS:
FACTS TO VERIFY:

Keep all sections concise.
Do not omit any section.
Count the narration words before returning.
"""

    user_prompt = (
        f"CEO ORIGINAL REQUEST:\n{str(task)[:1500]}\n\n"
        f"APPROVED CONCEPT:\n{str(concept)[:1000]}"
    )

    result = ask_ai(prompt, user_prompt)

    if not result or not str(result).strip():
        raise RuntimeError("Scriptwriter returned empty output.")

    return str(result).strip()


# ==================================================
# 3. QUALITY EDITOR
# ==================================================

def quality_editor(task, script):

    print("\n[QUALITY EDITOR] Reviewing and improving script...")

    prompt = """
You are an independent professional Quality Editor.

THE CEO ORIGINAL REQUEST IS THE FINAL AUTHORITY.

Improve the supplied script without changing
its historical subject or inventing information.

CHECK:
1. Exact topic preservation.
2. Grammar and natural English.
3. Narration word count.
4. Unsupported historical claims.
5. Misleading or invented details.
6. Complete visual timeline.

STRICT RULES:
- Preserve the original story and its meaning.
- Do not add historical facts.
- Do not invent dates, names, numbers or quotations.
- Never remove uncertainty labels unless evidence supports it.
- Keep unsupported claims marked [NEEDS SOURCE].
- Preserve all six visual timestamp sections.
- Do not create a second concept or script.
- Narration MUST contain 125-140 words.
- Target approximately 132 words.
- Count the narration words before returning.

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
        f"CEO ORIGINAL REQUEST:\n{str(task)[:1200]}\n\n"
        f"ORIGINAL SCRIPT:\n{str(script)[:3500]}"
    )

    edited = ask_ai(prompt, user_prompt)

    if not edited or not str(edited).strip():
        raise RuntimeError("Quality Editor returned empty output.")

    edited = str(edited).strip()

    narration = extract_narration(edited)
    words = count_words(narration)

    if not 125 <= words <= 140:

        print(
            f"[QUALITY EDITOR] Narration has {words} words. "
            "Requesting correction..."
        )

        repair_prompt = """
You are a professional YouTube Shorts Script Editor.

Correct ONLY the narration length in the supplied edited script.

MANDATORY:
- Narration must contain 125-140 words.
- Target approximately 132 words.
- Preserve the exact CEO topic.
- Preserve the meaning and historical accuracy.
- Do not invent facts.
- Keep [NEEDS SOURCE] labels.
- Preserve all six visual scenes and their timestamps.
- Do not add another concept or script.

Return the COMPLETE corrected edited script.
Do not omit any section.
"""

        repair_input = (
            f"CEO ORIGINAL REQUEST:\n{str(task)[:1200]}\n\n"
            f"CURRENT EDITED SCRIPT:\n{edited[:4500]}\n\n"
            f"CURRENT NARRATION WORD COUNT: {words}\n"
            "REQUIRED NARRATION WORD COUNT: 125-140"
        )

        repaired = ask_ai(repair_prompt, repair_input)

        if repaired and str(repaired).strip():

            repaired = str(repaired).strip()

            repaired_narration = extract_narration(repaired)
            repaired_words = count_words(repaired_narration)

            if 125 <= repaired_words <= 140:
                edited = repaired

                print(
                    "[QUALITY EDITOR] Word count corrected:",
                    repaired_words
                )

            else:
                print(
                    "[QUALITY EDITOR] Correction still outside "
                    f"required range: {repaired_words}"
                )

    final_narration = extract_narration(edited)

    print(
        "[QUALITY EDITOR] Final narration word count:",
        count_words(final_narration)
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

The CEO ORIGINAL TOPIC is mandatory.
Never change the topic.

EVIDENCE RULES:

1. Use ONLY the supplied source excerpts.
2. Read the supplied source excerpts carefully.
3. Check every historical claim in the final narration.
4. Search-result URLs alone are NOT evidence.
5. A source title or domain alone is NOT evidence.
6. A source excerpt must directly support the specific claim.
7. Do not invent source titles, URLs, quotations or evidence.
8. Do not claim to have independently opened a URL.
9. Do not mark a claim VERIFIED unless supplied source content
   directly supports that specific claim.
10. If evidence is insufficient, mark NEEDS SOURCE.
11. Use CONTRADICTED only when supplied source content
    directly contradicts the claim.
12. Cite the exact supplied source title and URL when available.
13. Do not confuse URL verification with claim verification.
14. A source can have URL VERIFICATION STATUS NOT_VERIFIED
    while its supplied excerpt still directly supports a claim.
    Explain this distinction.
15. Never approve publication.

IMPORTANT:
Read ALL supplied source excerpts, not just the first source.

For every important historical claim return:

CLAIM:
STATUS: VERIFIED / NEEDS SOURCE / CONTRADICTED
EVIDENCE EXCERPT:
REASON:
SOURCE TITLE:
SOURCE URL:

If no supplied source directly supports a claim:

STATUS: NEEDS SOURCE
EVIDENCE EXCERPT: NONE
SOURCE TITLE: NONE
SOURCE URL: NONE

Return exactly:

FACT CHECK RESULTS:
UNSUPPORTED CLAIMS:
CONTRADICTED CLAIMS:
OVERALL RESULT:

If any claim is NEEDS SOURCE or CONTRADICTED,
OVERALL RESULT must be REVIEW REQUIRED.

Be concise but do not omit important claims.
"""

    user_prompt = (
        f"CEO ORIGINAL REQUEST:\n{str(task)[:1000]}\n\n"
        f"FINAL SCRIPT TO CHECK:\n{str(script)[:3500]}\n\n"
        f"COMPLETE SUPPLIED RESEARCH EXCERPTS:\n"
        f"{supplied_sources}"
    )

    result = ask_ai(prompt, user_prompt)

    if not result or not str(result).strip():
        raise RuntimeError("Fact-checker returned empty output.")

    return str(result).strip()


# ==================================================
# 5. EVIDENCE-BASED SCRIPT EDITOR
# ==================================================

def evidence_based_editor(task, script, research, fact_check):

    print(
        "\n[EVIDENCE EDITOR] Removing unsupported "
        "historical claims..."
    )

    supplied_sources = serialize_research(research)

    prompt = """
You are an independent historical evidence-based script editor.

The CEO's original topic is LOCKED.
Never change or replace it.

Your job is to correct the narration using ONLY the
actual supplied source excerpts and fact-check results.

STRICT RULES:

1. Remove historical claims marked NEEDS SOURCE.
2. Remove claims that cannot be directly supported by
   supplied source text.
3. Never turn an unconfirmed theory into a historical fact.
4. A theory may remain only if the supplied source text
   directly describes it as a theory.
5. Never invent dates, numbers, names, quotations or events.
6. Never invent evidence or citations.
7. Preserve facts directly supported by supplied excerpts.
8. Preserve the correct historical inscription details:
   CRO was carved into a tree.
   CROATOAN was carved into a palisade.
   Do not reverse these details.
9. Croatoan must not be described as a proven destination
   for the missing colonists.
10. Do not include claims about DNA studies, descendants,
    modern archaeology, disease, safe harbors or other theories
    unless the supplied excerpts directly support them.
11. Do not add a claim simply to reach the word count.
12. If the evidence cannot support 125-140 words,
    return the most accurate narration possible and explain
    that the length requirement cannot safely be met.
13. Preserve exactly six visual scenes and their timestamps.
14. Keep all visual scenes consistent with the corrected narration.
15. Do not create another concept or another video.

NARRATION LENGTH:
- Target 125-140 words.
- Aim for approximately 132 words.
- Count narration words before returning.

Return exactly:

EVIDENCE EDITOR REVIEW:
REMOVED UNSUPPORTED CLAIMS:
RETAINED VERIFIED CLAIMS:
EDITED SCRIPT:

The EDITED SCRIPT must contain:
- One complete narration.
- Exactly six timestamped visual scenes.
"""

    user_prompt = (
        f"CEO ORIGINAL REQUEST:\n{str(task)[:1200]}\n\n"
        f"CURRENT SCRIPT:\n{str(script)[:3500]}\n\n"
        f"FACT CHECK RESULTS:\n{str(fact_check)[:3500]}\n\n"
        f"SUPPLIED RESEARCH:\n{supplied_sources}"
    )

    result = ask_ai(prompt, user_prompt)

    if not result or not str(result).strip():
        raise RuntimeError(
            "Evidence-Based Editor returned empty output."
        )

    edited = str(result).strip()

    narration = extract_narration(edited)
    words = count_words(narration)

    print(
        "[EVIDENCE EDITOR] Narration word count:",
        words
    )

    if not narration:
        raise RuntimeError(
            "Evidence-Based Editor did not return a readable narration."
        )

    if not 125 <= words <= 140:
        print(
            "[EVIDENCE EDITOR] WARNING: "
            "Narration does not meet the 125-140 word requirement."
        )

    return edited


# ==================================================
# 6. MEDIA DEPARTMENT MANAGER
# ==================================================

def run_media_department(task):

    print("\n" + "=" * 55)
    print("MEDIA DEPARTMENT STARTED")
    print("=" * 55)

    # STEP 1: CONCEPT

    print("\n[MEDIA] Creative Strategist started...")

    concept = creative_strategist(task)

    # STEP 2: SCRIPT

    print("\n[MEDIA] Scriptwriter started...")

    script = scriptwriter(task, concept)

    # STEP 3: INITIAL EDITING

    print("\n[MEDIA] Quality Editor started...")

    edited_script = quality_editor(task, script)

    # STEP 4: RESEARCH

    print("\n[MEDIA] Research Agent started...")

    research = run_research(task, edited_script)

    if not isinstance(research, dict):
        research = {
            "status": "ERROR",
            "sources": [],
            "message": "Research agent returned invalid data."
        }

    print(
        "\n[MEDIA] Research status:",
        research.get("status")
    )

    # STEP 5: INITIAL FACT CHECK

    print("\n[MEDIA] Initial Fact-Checker started...")

    initial_fact_check = fact_checker(
        task,
        edited_script,
        research
    )

    # STEP 6: EVIDENCE-BASED CORRECTION

    print("\n[MEDIA] Evidence-Based Editor started...")

    evidence_edited_script = evidence_based_editor(
        task,
        edited_script,
        research,
        initial_fact_check
    )

    # STEP 7: FINAL INDEPENDENT FACT CHECK

    print("\n[MEDIA] Final Fact-Checker started...")

    fact_check = fact_checker(
        task,
        evidence_edited_script,
        research
    )

    print("\n[MEDIA] Final fact-check completed.")

    # STEP 8: FINAL RESULT

    narration = extract_narration(evidence_edited_script)
    narration_words = count_words(narration)

    print("\n" + "=" * 55)
    print("MEDIA DEPARTMENT COMPLETED")
    print("NARRATION WORDS:", narration_words)
    print("PUBLICATION APPROVED: False")
    print("=" * 55)

    return {
        "department": "media",
        "status": "REVIEW_REQUIRED",
        "message": (
            "Media production, evidence-based editing and "
            "final fact-check completed. CEO review is required."
        ),
        "original_ceo_topic": task,
        "concept": concept,
        "script": script,
        "edited_script": evidence_edited_script,
        "initial_fact_check": initial_fact_check,
        "narration_word_count": narration_words,
        "research": research,
        "fact_check": fact_check,
        "publication_approved": False,
        "specialists": [
            "Creative Strategist",
            "Scriptwriter",
            "Quality Editor",
            "Research Agent",
            "Independent Fact-Checker",
            "Evidence-Based Script Editor"
        ]
    }
