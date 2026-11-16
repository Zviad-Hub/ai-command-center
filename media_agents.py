
from ai_brain import ask_ai
from research_agent import run_research


def creative_strategist(task):

    prompt = """
You are a professional YouTube Shorts Creative Strategist.

STRICT CEO TOPIC LOCK:
- The CEO's original request is the ONLY topic.
- Never change, replace or expand the topic.
- Create exactly ONE video concept.
- Do not invent historical facts.
- Uncertain details must be marked NEEDS SOURCE.

Be concise.

Return exactly:

EXACT TOPIC:
VIDEO CONCEPT:
HOOK:
KEY QUESTIONS TO INVESTIGATE:

Maximum 180 words.
"""

    return ask_ai(prompt, str(task)[:1500])


def scriptwriter(task, concept):

    prompt = """
You are a professional historical YouTube Shorts Scriptwriter.

THE CEO ORIGINAL REQUEST IS THE FINAL AUTHORITY.
The topic must never change.

Create ONE English YouTube Shorts video script.

STRICT LENGTH:
- Narration: 125-140 words.
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
"""

    user_prompt = (
        f"CEO ORIGINAL REQUEST:\n{str(task)[:1500]}\n\n"
        f"APPROVED CONCEPT:\n{str(concept)[:1000]}"
    )

    return ask_ai(prompt, user_prompt)


def quality_editor(task, script):

    prompt = """
You are an independent professional Quality Editor.

THE CEO ORIGINAL REQUEST IS THE FINAL AUTHORITY.

Your job is to improve the supplied script without changing
its historical subject or inventing information.

CHECK:
1. Exact topic preservation.
2. Grammar and natural English.
3. Approximately 60-second narration.
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

Return exactly:

TOPIC CHECK:
EDITOR REVIEW:
PROBLEMS:
CORRECTIONS:
EDITED SCRIPT:
FACTS STILL NEEDING VERIFICATION:

The EDITED SCRIPT must contain the complete narration
and all six timestamped visual directions.

Keep the review concise.
"""

    user_prompt = (
        f"CEO ORIGINAL REQUEST:\n{str(task)[:1200]}\n\n"
        f"ORIGINAL SCRIPT:\n{str(script)[:3500]}"
    )

    return ask_ai(prompt, user_prompt)


def fact_checker(task, script, research):

    prompt = """
You are a STRICT independent historical fact-checker.

The CEO ORIGINAL TOPIC is mandatory.
Never change the topic.

EVIDENCE RULES:

1. Search-result snippets are not automatically proof.
2. A domain name alone does not verify a claim.
3. A source must directly support the specific claim.
4. Prefer government archives, museums, universities
   and original historical documents.
5. Use ONLY the supplied research sources.
6. Never invent source titles, URLs, quotations or evidence.
7. Do not claim to have opened or independently checked URLs.
8. Do not mark a claim VERIFIED unless supplied source content
   directly supports that specific claim.
9. If evidence is insufficient, mark NEEDS SOURCE.
10. Use CONTRADICTED only when supplied evidence directly
    contradicts the claim.
11. Never approve publication.

For each important historical claim return:

CLAIM:
STATUS: VERIFIED / NEEDS SOURCE / CONTRADICTED
REASON:
SOURCE TITLE:
SOURCE URL:

If no supplied source directly supports a claim:

STATUS: NEEDS SOURCE
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
        f"SCRIPT TO CHECK:\n{str(script)[:3000]}\n\n"
        f"SUPPLIED RESEARCH:\n{str(research)[:3500]}"
    )

    return ask_ai(prompt, user_prompt)


def run_media_department(task):

    print("\n[MEDIA] Creative Strategist started...")

    concept = creative_strategist(task)

    if not concept or not concept.strip():
        raise RuntimeError("Creative Strategist returned empty output.")

    print("\n[MEDIA] Scriptwriter started...")

    script = scriptwriter(task, concept)

    if not script or not script.strip():
        raise RuntimeError("Scriptwriter returned empty output.")

    print("\n[MEDIA] Quality Editor started...")

    edited_script = quality_editor(task, script)

    if not edited_script or not edited_script.strip():
        raise RuntimeError("Quality Editor returned empty output.")

    print("\n[MEDIA] Research Agent started...")

    research = run_research(task, edited_script)

    print(
        "\n[MEDIA] Research status:",
        research.get("status")
    )

    print("\n[MEDIA] Independent Fact-Checker started...")

    fact_check = fact_checker(
        task,
        edited_script,
        research
    )

    print("\n[MEDIA] Fact-check completed.")

    return {
        "department": "media",
        "status": "REVIEW_REQUIRED",
        "message": (
            "Media production and preliminary fact-check completed. "
            "CEO review is required before publication."
        ),
        "original_ceo_topic": task,
        "concept": concept,
        "script": script,
        "edited_script": edited_script,
        "research": research,
        "fact_check": fact_check,
        "publication_approved": False,
        "specialists": [
            "Creative Strategist",
            "Scriptwriter",
            "Quality Editor",
            "Research Agent",
            "Independent Fact-Checker"
        ]
    }
