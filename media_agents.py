
from ai_brain import ask_ai


def creative_strategist(task):
    prompt = """
You are the Creative Strategist of a professional
English-language YouTube Shorts media department.

Your responsibilities:
- Understand the topic.
- Create an engaging video concept.
- Develop a powerful opening hook.
- Suggest a compelling narrative.
- Identify historical claims requiring verification.

Write in English.
Be creative, specific and engaging.
Never invent historical facts.
"""

    return ask_ai(prompt, task)


def scriptwriter(task, concept):
    prompt = """
You are a professional YouTube Shorts Scriptwriter.

Create a 45-60 second English narration script.

Requirements:
- Strong opening hook.
- Short, natural sentences.
- Engaging storytelling.
- Clear visual directions.
- Avoid presenting unverified claims as facts.

Return:
VIDEO TITLE:
HOOK:
SCRIPT:
VISUAL DIRECTIONS:
FACTS TO VERIFY:
"""

    combined_task = f"""
CEO REQUEST:
{task}

CREATIVE STRATEGY:
{concept}

Create the final video script.
"""

    return ask_ai(prompt, combined_task)


def quality_editor(task, script):
    prompt = """
You are an independent professional Quality Editor.

Review the supplied YouTube Shorts script.

Check:
- Storytelling quality.
- Grammar and clarity.
- Timing (45-60 seconds).
- Repetition.
- Unsupported historical claims.
- Misleading or overly dramatic statements.

Do not invent facts.

Return:
EDITOR REVIEW:
PROBLEMS FOUND:
RECOMMENDED CORRECTIONS:
APPROVED SCRIPT:
"""

    return ask_ai(
        prompt,
        f"CEO REQUEST:\n{task}\n\nSCRIPT:\n{script}"
    )


def fact_checker(task, script):
    prompt = """
You are an independent Historical Fact-Checker.

IMPORTANT:
You do NOT have internet access.
You have NOT independently verified historical facts.

Your job is to:
1. Extract every historical factual claim.
2. Identify claims requiring reliable external sources.
3. Detect unsupported assumptions.
4. Identify contradictions or suspicious dates.
5. Never pretend that a claim is verified.

Use ONLY these statuses:

NEEDS SOURCE:
No reliable source was supplied.

VERIFIED:
Only if reliable source evidence is explicitly included
in the provided material and directly supports the claim.

CONTRADICTED:
Only if supplied reliable source evidence directly
contradicts the claim.

For every claim provide:
- CLAIM:
- STATUS:
- REASON:
- SOURCE NEEDED:

At the end provide:
OVERALL FACT-CHECK RESULT:
CLAIMS THAT MUST BE REMOVED OR REWRITTEN:
"""

    return ask_ai(
        prompt,
        f"CEO REQUEST:\n{task}\n\nSCRIPT TO CHECK:\n{script}"
    )


def run_media_department(task):

    print("\n[MEDIA] Creative Strategist started...")

    concept = creative_strategist(task)

    print("[MEDIA] Creative concept completed.")

    print("\n[MEDIA] Scriptwriter started...")

    script = scriptwriter(task, concept)

    print("[MEDIA] Script completed.")

    print("\n[MEDIA] Quality Editor started...")

    edited_script = quality_editor(task, script)

    print("[MEDIA] Quality review completed.")

    print("\n[MEDIA] Independent Fact-Checker started...")

    fact_check = fact_checker(task, edited_script)

    print("[MEDIA] Fact-check completed.")

    return {
        "department": "media",
        "status": "COMPLETED",
        "message": "Media production and review completed.",
        "concept": concept,
        "script": script,
        "edited_script": edited_script,
        "fact_check": fact_check,
        "specialists": [
            "Creative Strategist",
            "Scriptwriter",
            "Quality Editor",
            "Fact-Checker"
        ]
    }
