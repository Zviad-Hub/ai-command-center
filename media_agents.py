
from ai_brain import ask_ai
from research_agent import run_research


def creative_strategist(task):
    prompt = """
You are the Creative Strategist of an AI media company.

STRICT CEO AUTHORITY:
- The CEO's original task defines the ONLY permitted topic.
- Never change, replace, or expand the topic.
- Never suggest unrelated stories.
- Create ONE concept only.
- If the topic is unclear, ask for clarification.
- Never invent historical facts.

Return briefly:
TOPIC:
VIDEO TITLE:
HOOK:
STORY ANGLE:
"""
    return ask_ai(prompt, f"ORIGINAL CEO TASK:\n{task[:1800]}")


def scriptwriter(task, concept):
    prompt = """
You are a professional YouTube Shorts Scriptwriter.

MANDATORY RULES:
- Follow the exact topic in the original CEO task.
- Do not introduce another historical event or subject.
- Write in English.
- Target duration: 45-60 seconds.
- Use short, engaging narration.
- Never invent facts, dates, quotations or sources.
- Mark uncertain claims as NEEDS SOURCE.

Return:
VIDEO TITLE:
HOOK:
NARRATION:
TIMESTAMPED VISUAL DIRECTIONS:
FACTS TO VERIFY:

Keep the complete response concise.
"""
    return ask_ai(
        prompt,
        f"ORIGINAL CEO TASK:\n{task[:1800]}\n\n"
        f"APPROVED TOPIC CONCEPT:\n{concept[:1800]}"
    )


def quality_editor(task, script):
    prompt = """
You are an independent professional Quality Editor.

STRICT RULES:
- Preserve the exact subject requested by the CEO.
- Never replace the topic.
- Check grammar, clarity, storytelling and timing.
- Identify unsupported historical claims.
- Do not invent corrections or facts.
- Do not mark historical claims as verified.

Return:
EDITOR REVIEW:
PROBLEMS:
CORRECTIONS:
REVISED SCRIPT:

Keep it concise.
"""
    return ask_ai(
        prompt,
        f"ORIGINAL CEO TASK:\n{task[:1200]}\n\n"
        f"SCRIPT:\n{script[:3500]}"
    )


def fact_checker(task, script, research):
    prompt = """
You are an independent Historical Fact-Checker.

STRICT EVIDENCE POLICY:
- The original CEO topic must remain unchanged.
- Check every historical claim in the script.
- Use only the supplied research results.
- A search result is not automatically proof.
- VERIFIED only when a reliable source directly supports the claim.
- NEEDS SOURCE when evidence is missing or weak.
- CONTRADICTED only when reliable evidence directly contradicts it.
- Never invent sources, quotations, URLs or evidence.
- Do not claim that you independently verified inaccessible documents.

For every claim return:
CLAIM:
STATUS:
EVIDENCE:
SOURCE TITLE:
SOURCE URL:

Finish with:
OVERALL RESULT:
CLAIMS NEEDING CORRECTION:

Keep it concise.
"""
    return ask_ai(
        prompt,
        f"ORIGINAL CEO TASK:\n{task[:1200]}\n\n"
        f"SCRIPT:\n{script[:2500]}\n\n"
        f"RESEARCH:\n{str(research)[:4000]}"
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

    print("[MEDIA] Research status:", research.get("status"))

    print("\n[MEDIA] Independent Fact-Checker started...")
    fact_check = fact_checker(
        task,
        edited_script,
        research
    )

    print("\n[MEDIA] Production pipeline completed.")

    return {
        "department": "media",
        "status": "COMPLETED",
        "message": "Media production and evidence review completed.",
        "original_ceo_task": task,
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
