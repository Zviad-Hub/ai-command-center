
import json

from ai_brain import ask_ai
from config import DEPARTMENTS


DIRECTOR_PROMPT = """
You are the Chief AI Director of a multi-department AI organization.

Your CEO speaks Georgian.

Your job:
1. Understand the CEO's task.
2. Select the appropriate departments.
3. You may select multiple departments.
4. Create a clear mission for each department.
5. Identify tasks requiring human approval.

Available departments:
- media
- tenders
- finance
- business
- pentester
- technical
- audit

IMPORTANT SECURITY RULES:
- Pentesting requires written authorization.
- Pentesting requires explicit CEO approval.
- Never authorize testing automatically.
- Never initiate financial transactions.
- Never submit tenders or publish content without CEO approval.

Return ONLY valid JSON in this format:

{
  "analysis": "Short explanation in Georgian",
  "departments": ["media"],
  "missions": {
    "media": "Detailed mission in Georgian"
  },
  "requires_ceo_approval": true
}
"""


def route_task(task):
    prompt = f"""
    Analyze this CEO task:

    {task}

    Choose only relevant departments from:
    {", ".join(DEPARTMENTS)}

    Return JSON only.
    """

    response = ask_ai(DIRECTOR_PROMPT, prompt)

    try:
        data = json.loads(response)

        departments = data.get("departments", [])

        if not departments:
            raise ValueError("No departments selected")

        if not all(d in DEPARTMENTS for d in departments):
            raise ValueError("Invalid department selected")

        missions = data.get("missions", {})

        for department in departments:
            if not isinstance(missions.get(department), str):
                raise ValueError("Missing department mission")

        return {
            "analysis": str(data.get("analysis", "")),
            "departments": list(dict.fromkeys(departments)),
            "missions": missions,
            "requires_ceo_approval": bool(
                data.get("requires_ceo_approval", True)
            )
        }

    except (json.JSONDecodeError, ValueError, TypeError):
        print("AI response invalid. Using safe fallback.")
        return {
            "analysis": "დავალება გადაეცემა ტექნიკურ დეპარტამენტს.",
            "departments": ["technical"],
            "missions": {
                "technical": task
            },
            "requires_ceo_approval": True
        }


def create_plan(task):
    plan = route_task(task)

    print("\nAI DIRECTOR — ANALYSIS")
    print("-" * 45)

    print(plan["analysis"])

    for department in plan["departments"]:
        print("\nMANAGER:", department.upper())
        print("MISSION:", plan["missions"][department])

    if "pentester" in plan["departments"]:
        print("\nSECURITY GATE ACTIVATED")
        print("Written authorization required.")
        print("CEO approval required.")
        print("Testing remains blocked.")

    print("\nCEO APPROVAL REQUIRED:",
          plan["requires_ceo_approval"])

    return plan["departments"]


if __name__ == "__main__":
    task = input("CEO > ")
    create_plan(task)
