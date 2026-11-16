
from ai_brain import ask_ai
from research_agent import run_research


def creative_strategist(task):
    prompt = """
You are a professional YouTube Shorts Creative Strategist.

STRICT CEO TOPIC LOCK:
- The CEO's original request is the ONLY topic.
- Never replace or change the topic.
- Create exactly ONE video concept.
- Do not invent historical facts.
- Mark uncertain details as NEEDS SOURCE.

Return:
EXACT TOPIC:
VIDEO CONCEPT:
HOOK:
KEY QUESTIONS TO INVESTIGATE:
"""
    return ask_ai(prompt, task)


def scriptwriter(task, concept):
    prompt = """
You are a professional historical YouTube Shorts Scriptwriter.

The CEO ORIGINAL REQUEST is the final authority.
The topic must never change.

Create ONE English YouTube Shorts script
lasting approximately 60 seconds.

Rules:
- Strong opening hook.
- Natural, engaging narration.
- Timestamped visual directions.
- No invented dates, names, numbers or quotations.
- Unverified claims must be marked [NEEDS SOURCE].
- Do not invent sources.

Return:
VIDEO TITLE:
EXACT TOPIC:
HOOK:
SCRIPT:
VISUAL DIRECTIONS:
FACTS TO VERIFY:
"""
    return ask_ai(
        prompt,
        f"CEO ORIGINAL REQUEST:\n{task}\n\nCONCEPT:\n{str(concept)[:1800]}"
    )


def quality_editor(task, script):
    prompt = """
You are an independent Quality Editor.

Preserve the CEO's exact original topic.

Check:
- Topic consistency.
- Grammar and storytelling.
- 45-60 second timing.
- Unsupported historical claims.
- Invented or misleading details.

Do not add historical facts.
Do not invent sources.
Keep unsupported claims marked [NEEDS SOURCE].

Return:
TOPIC CHECK:
EDITOR REVIEW:
PROBLEMS:
CORRECTIONS:
EDITED SCRIPT:
FACTS STILL NEEDING VERIFICATION:
"""
    return ask_ai(
        prompt,
        f"CEO ORIGINAL REQUEST:\n{task}\n\nSCRIPT:\n{str(script)[:3000]}"
    )


def fact_checker(task, script, research):
    prompt = """
You are a STRICT independent historical fact-checker.

The CEO ORIGINAL TOPIC is mandatory.
Never change it.

EVIDENCE RULES:

1. Search-result snippets are not automatically proof.
2. A domain name alone does not verify a claim.
3. A source must directly support the specific claim.
4. Prefer original historical documents, government archives,
   museums and universities.
5. You may only use sources included in the supplied research.
6. Never invent source titles, URLs, quotations or evidence.
7. If a source does not directly support a claim,
   mark it NEEDS SOURCE.
8. Do not mark a claim VERIFIED based only on a search snippet.
9. Do not claim to have opened or independently verified a URL.
10. If evidence is insufficient, the overall result is REVIEW REQUIRED.

For EACH historical claim return:

CLAIM:
STATUS: VERIFIED / NEEDS SOURCE / CONTRADICTED
REASON:
SOURCE TITLE:
SOURCE URL:

A claim can only be VERIFIED if the supplied source content
directly supports it.

If no source directly supports it:
STATUS: NEEDS SOURCE
SOURCE TITLE: NONE
SOURCE URL: NONE

Return:

FACT CHECK RESULTS:
UNSUPPORTED CLAIMS:
CONTRADICTED CLAIMS:
OVERALL RESULT:

Overall result must be REVIEW REQUIRED if any claim
is NEEDS SOURCE or CONTRADICTED.

Never approve publication.
"""
    return ask_ai(
        prompt,
        f"CEO ORIGINAL REQUEST:\n{task[:700]}\n\n"
        f"SCRIPT:\n{str(script)[:3000]}\n\n"
        f"RESEARCH SOURCES:\n{str(research)[:5000]}"
    )


def run_media_department(task):

    print("\n[MEDIA] Creative Strategist started...")
    concept = creative_strategist(task)

    print("\n[MEDIA] Scriptwriter started...")
    script = scriptwriter(task, concept)

    print("\n[MEDIA] Quality Editor started...")
    edited_script = quality_editor(task, script)

    print("\n[MEDIA] Research Agent started...")
    research = run_research(task, edited_script)

    print("\n[MEDIA] Research status:", research.get("status"))

    print("\n[MEDIA] Independent Fact-Checker started...")
    fact_check = fact_checker(task, edited_script, research)

    print("\n[MEDIA] Fact-check completed.")

    return {
        "department": "media",
        "status": "REVIEW_REQUIRED",
        "message": (
            "Production and preliminary fact-check completed. "
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
