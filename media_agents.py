
from ai_brain import ask_ai
from research_agent import run_research


def creative_strategist(task):
    prompt = """
You are a professional YouTube Shorts Creative Strategist.
Create an engaging concept and hook.
Identify historical claims that need verification.
Write in English. Never invent facts.
Keep the response concise.
"""
    return ask_ai(prompt, task)


def scriptwriter(task, concept):
    prompt = """
You are a professional YouTube Shorts Scriptwriter.

Create a 45-60 second English video script.

Return:
VIDEO TITLE:
HOOK:
SCRIPT:
VISUAL DIRECTIONS:
FACTS TO VERIFY:

Use engaging storytelling.
Never present unverified claims as facts.
Keep it concise.
"""
    return ask_ai(
        prompt,
        f"CEO REQUEST:\n{task}\n\nCONCEPT:\n{concept}"
    )


def quality_editor(task, script):
    prompt = """
You are an independent professional Quality Editor.

Check:
- Storytelling and grammar
- 45-60 second timing
- Unsupported claims
- Misleading statements

Do not invent facts.

Return:
EDITOR REVIEW:
PROBLEMS:
CORRECTIONS:
APPROVED SCRIPT:

Keep it concise.
"""
    return ask_ai(
        prompt,
        f"CEO REQUEST:\n{task}\n\nSCRIPT:\n{script}"
    )


def fact_checker(task, script, research):
    prompt = """
You are an independent Historical Fact-Checker.

You have received web search results.
Search results are evidence leads, NOT automatic proof.

For every factual claim:
- Compare it with the supplied source material.
- Check whether the source directly supports the claim.
- Include the source title and URL.
- Never invent sources or evidence.

Use only these statuses:

VERIFIED:
Reliable supplied evidence directly supports the claim.

NEEDS SOURCE:
Evidence is missing, weak, or inconclusive.

CONTRADICTED:
Reliable supplied evidence directly contradicts the claim.

Return:
CLAIM:
STATUS:
EVIDENCE:
SOURCE URL:

OVERALL RESULT:
CLAIMS NEEDING REVISION:

Be concise. Do not claim independent verification beyond
the supplied search results.
"""
    return ask_ai(
        prompt,
        f"CEO REQUEST:\n{task[:500]}\n\n"
        f"SCRIPT:\n{script[:2500]}\n\n"
        f"RESEARCH RESULTS:\n{str(research)[:6500]}"
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
        "[MEDIA] Research status:",
        research.get("status")
    )

    print("\n[MEDIA] Independent Fact-Checker started...")
    fact_check = fact_checker(
        task,
        edited_script,
        research
    )

    print("[MEDIA] Fact-check completed.")

    return {
        "department": "media",
        "status": "COMPLETED",
        "message": "Media production, research and review completed.",
        "concept": concept,
        "script": script,
        "edited_script": edited_script,
        "research": research,
        "fact_check": fact_check,
        "specialists": [
            "Creative Strategist",
            "Scriptwriter",
            "Quality Editor",
            "Research Agent",
            "Fact-Checker"
        ]
    }
