
from ai_brain import ask_ai


def creative_strategist(task):
    prompt = """
You are the Creative Strategist of a professional
English-language YouTube Shorts media department.

Your job:
- Understand the requested topic.
- Create an engaging video concept.
- Find a strong opening hook.
- Suggest an interesting narrative direction.
- Identify what needs external fact verification.

Write your response in English.
Be creative, specific and engaging.
Do not invent historical facts.
"""

    return ask_ai(prompt, task)


def scriptwriter_and_editor(task, concept):
    prompt = """
You are two specialist agents working together:

1. PROFESSIONAL SCRIPTWRITER:
Write an engaging YouTube Shorts script in English.
Target duration: 45-60 seconds.
Use a powerful opening hook.
Keep sentences short and natural.
Include narration and visual suggestions.

2. QUALITY EDITOR:
Review the script.
Improve the storytelling, pacing and clarity.
Flag claims that require external fact verification.
Do not present unverified claims as established facts.

Return:
VIDEO TITLE:
HOOK:
SCRIPT:
VISUAL DIRECTIONS:
FACTS TO VERIFY:
QUALITY REVIEW:
"""

    combined_task = f"""
CEO REQUEST:
{task}

CREATIVE STRATEGY:
{concept}

Now write and review the final video script.
"""

    return ask_ai(prompt, combined_task)


def run_media_department(task):
    print("\n[MEDIA] Creative Strategist started...")

    concept = creative_strategist(task)

    print("[MEDIA] Creative concept completed.")
    print("[MEDIA] Scriptwriter and Editor started...")

    final_script = scriptwriter_and_editor(task, concept)

    print("[MEDIA] Script completed.")

    return {
        "department": "media",
        "status": "COMPLETED",
        "message": "Media production draft successfully created.",
        "concept": concept,
        "script": final_script,
        "specialists": [
            "Creative Strategist",
            "Scriptwriter",
            "Quality Editor"
        ]
    }
