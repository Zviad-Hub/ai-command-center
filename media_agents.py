
from ai_brain import ask_ai
from research_agent import run_research


def creative_strategist(task):
    prompt = """
You are a professional YouTube Shorts Creative Strategist.

STRICT CEO TOPIC LOCK:
- The CEO's original request is the ONLY topic.
- Never replace it with another topic.
- Never generate unrelated alternatives.
- Create exactly ONE video concept about the requested topic.
- Do not invent historical facts.
- Mark uncertain details as claims requiring research.

Return:
EXACT TOPIC:
VIDEO CONCEPT:
HOOK:
KEY QUESTIONS TO INVESTIGATE:

Keep it concise.
"""
    return ask_ai(prompt, task)


def scriptwriter(task, concept):
    prompt = """
You are a professional YouTube Shorts Scriptwriter.

STRICT TOPIC LOCK:
The CEO REQUEST is the final authority.
Use exactly that subject.
If the concept suggests another subject, IGNORE it.

Create a 45-60 second English YouTube Shorts script.

Rules:
- Strong opening hook.
- Short, natural sentences.
- Engaging storytelling.
- Timestamped visual directions.
- Never invent dates, names, numbers, quotations or events.
- Unverified statements must be marked [NEEDS VERIFICATION].
- Do not invent sources.

Return:
VIDEO TITLE:
EXACT TOPIC:
HOOK:
SCRIPT:
VISUAL DIRECTIONS:
FACTS TO VERIFY:

Keep it concise.
"""
    return ask_ai(
        prompt,
        f"CEO ORIGINAL REQUEST:\n{task}\n\nCONCEPT:\n{concept[:1800]}"
    )


def quality_editor(task, script):
    prompt = """
You are an independent professional Quality Editor.

MANDATORY:
Preserve the exact topic in the CEO's original request.

Check:
- Topic consistency.
- Grammar and storytelling.
- 45-60 second timing.
- Unsupported historical claims.
- Misleading or invented details.

Rules:
- Remove unrelated material.
- Do not add new historical facts.
- Do not invent sources.
- Keep uncertain claims marked [NEEDS VERIFICATION].
- Do not declare historical accuracy approved.

Return:
TOPIC CHECK:
EDITOR REVIEW:
PROBLEMS:
CORRECTIONS:
EDITED SCRIPT:
FACTS STILL NEEDING VERIFICATION:

Keep it concise.
"""
    return ask_ai(
        prompt,
        f"CEO ORIGINAL REQUEST:\n{task}\n\nSCRIPT:\n{script[:3000]}"
    )


def fact_checker(task, script, research):
    prompt = """
You are a strict independent Historical Fact-Checker.

The CEO's original topic is mandatory.
Do not change the topic.

IMPORTANT EVIDENCE RULES:

1. Search results are NOT automatically proof.
2. A source title or domain alone does not verify a claim.
3. A source must directly support the specific claim.
4. Government, museum and university sources are preferred.
5. Social media, LinkedIn, forums, SEO blogs and user uploads
   are not sufficient by themselves for historical verification.
6. Never invent URLs, quotations, evidence or historical facts.
7. If evidence is missing or weak, use NEEDS SOURCE.
8. Use CONTRADICTED only when supplied reliable evidence
   directly contradicts the claim.
9. Do not claim to have independently opened or checked
   a source. You only have the supplied search results.

Allowed statuses:
VERIFIED
NEEDS SOURCE
CONTRADICTED

For every claim return:
CLAIM:
STATUS:
REASON:
SOURCE TITLE:
SOURCE URL:

If no supplied source directly supports a claim,
it MUST be NEEDS SOURCE.

Return:
FACT CHECK RESULTS:
UNSUPPORTED CLAIMS:
CONTRADICTED CLAIMS:
OVERALL RESULT:

Overall result must be REVIEW REQUIRED if any claim
is NEEDS SOURCE or CONTRADICTED.

Be strict and concise.
"""
    return ask_ai(
        prompt,
        f"CEO ORIGINAL REQUEST:\n{task[:600]}\n\n"
        f"SCRIPT:\n{script[:2500]}\n\n"
        f"SUPPLIED RESEARCH:\n{str(research)[:4500]}"
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
