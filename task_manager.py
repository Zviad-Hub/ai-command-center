
import json

from ai_brain import ask_ai


TECHNICAL_SPECIALISTS = {
    "system_architect": "System Architect",
    "backend_developer": "Backend Developer",
    "frontend_developer": "Frontend Developer",
    "devops_engineer": "DevOps Engineer",
    "qa_engineer": "QA Engineer",
    "code_reviewer": "Code Reviewer",
    "security_engineer": "Security Engineer",
    "database_engineer": "Database Engineer"
}


SYSTEM_PROMPT = """
You are the Technical Department Manager of an AI organization.

Your job is to analyze software engineering requests and coordinate
the appropriate technical specialists.

You must return valid JSON only.

Never claim that code was executed, files were modified,
tests were completed, or deployment occurred unless explicitly true.

Security work must remain defensive and passive.
Never authorize active security testing.

CEO approval is mandatory before implementation.
"""


def extract_json(text):
    text = str(text or "").strip()

    if text.startswith("```"):
        lines = text.splitlines()

        if lines:
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        text = "\n".join(lines)

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end <= start:
        raise ValueError("AI did not return valid JSON.")

    return json.loads(text[start:end + 1])


def run_technical_manager(task):

    user_prompt = f"""
Analyze this customer request:

{task}

Available specialists:
{json.dumps(TECHNICAL_SPECIALISTS, indent=2)}

Select all specialists needed for this request.

Return this JSON structure:

{{
    "department": "technical",
    "manager": "Technical Manager",
    "status": "PLANNED",
    "task_analysis": "Brief analysis",
    "selected_specialists": [
        {{
            "id": "system_architect",
            "mission": "Specific individual mission"
        }}
    ],
    "execution_plan": [],
    "testing_strategy": [],
    "technical_risks": [],
    "missing_information": [],
    "requires_ceo_approval": true
}}

Each selected specialist must have an individual mission.

Do not invent completed work.
Do not execute code.
Do not modify files.
CEO approval is required before implementation.
"""

    try:
        response = ask_ai(
            SYSTEM_PROMPT,
            user_prompt
        )

        plan = extract_json(response)

        selected = []

        for specialist in plan.get("selected_specialists", []):

            if not isinstance(specialist, dict):
                continue

            specialist_id = specialist.get("id")

            if specialist_id not in TECHNICAL_SPECIALISTS:
                continue

            selected.append({
                "id": specialist_id,
                "name": TECHNICAL_SPECIALISTS[specialist_id],
                "mission": str(
                    specialist.get("mission", "")
                ).strip()
            })

        if not selected:
            return {
                "department": "technical",
                "manager": "Technical Manager",
                "status": "REVIEW_REQUIRED",
                "message": "No valid specialists were selected.",
                "selected_specialists": [],
                "requires_ceo_approval": True,
                "execution_authorized": False
            }

        plan["department"] = "technical"
        plan["manager"] = "Technical Manager"
        plan["status"] = "PLANNED"
        plan["selected_specialists"] = selected
        plan["requires_ceo_approval"] = True
        plan["execution_authorized"] = False
        plan["execution_performed"] = False

        return plan

    except Exception as error:
        return {
            "department": "technical",
            "manager": "Technical Manager",
            "status": "ERROR",
            "message": "Technical planning failed.",
            "error": str(error),
            "selected_specialists": [],
            "requires_ceo_approval": True,
            "execution_authorized": False
        }
