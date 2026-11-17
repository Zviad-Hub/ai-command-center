
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
    "database_engineer": "Database Engineer",
}


TECHNICAL_MANAGER_PROMPT = """
You are the Technical Department Manager of an AI organization.

Your CEO speaks Georgian.

Your responsibilities:
1. Understand the CEO's technical task.
2. Select only the specialists needed.
3. Create clear, practical missions for each specialist.
4. Define the expected deliverables.
5. Identify technical risks.
6. Decide which tasks require CEO approval.

AVAILABLE SPECIALISTS:
- system_architect
- backend_developer
- frontend_developer
- devops_engineer
- qa_engineer
- code_reviewer
- security_engineer
- database_engineer

IMPORTANT RULES:

- Never invent completed work.
- Never claim code was tested unless tests were actually executed.
- Never claim a bug was fixed unless the change was actually made.
- Separate analysis, implementation and testing.
- Prefer isolated test environments.
- Never expose secrets, API keys or passwords.
- Never deploy to production without explicit CEO approval.
- Never merge code into the main branch without CEO approval.
- Never modify real project files without CEO approval.
- Security testing must remain passive unless written authorization
  and separate CEO approval are provided.
- If the task is unclear, identify what information is missing.

Return ONLY valid JSON using this structure:

{
    "department": "technical",
    "manager": "Technical Manager",
    "status": "PLAN_CREATED",
    "task_understanding": "Clear explanation of the task",
    "selected_specialists": [
        {
            "specialist": "backend_developer",
            "mission": "Specific mission",
            "deliverables": [
                "Expected deliverable"
            ]
        }
    ],
    "execution_plan": [
        "Step 1",
        "Step 2"
    ],
    "testing_strategy": [
        "Testing requirement"
    ],
    "risks": [
        "Identified risk"
    ],
    "requires_ceo_approval": true,
    "approval_reasons": [
        "Reason requiring approval"
    ],
    "final_deliverables": [
        "Expected final result"
    ]
}
"""


def extract_json(response):
    response = str(response or "").strip()

    if response.startswith("```"):
        response = response.split("\n", 1)[-1]
        if response.endswith("```"):
            response = response[:-3].strip()

    start = response.find("{")
    end = response.rfind("}")

    if start == -1 or end == -1 or end <= start:
        raise ValueError("Technical Manager returned invalid JSON.")

    return json.loads(response[start:end + 1])


def run_technical_manager(task):
    task = str(task or "").strip()

    if not task:
        return {
            "department": "technical",
            "manager": "Technical Manager",
            "status": "REJECTED",
            "message": "Technical task is empty.",
            "selected_specialists": [],
            "requires_ceo_approval": False
        }

    prompt = f"""
{TECHNICAL_MANAGER_PROMPT}

CEO TASK:
{task}
"""

    try:
        response = ask_ai(prompt)
        result = extract_json(response)

        selected = result.get("selected_specialists", [])

        if not isinstance(selected, list):
            raise ValueError("Invalid specialists list.")

        valid_specialists = []

        for item in selected:
            if not isinstance(item, dict):
                continue

            specialist = str(
                item.get("specialist", "")
            ).strip()

            if specialist not in TECHNICAL_SPECIALISTS:
                continue

            valid_specialists.append({
                "specialist": specialist,
                "mission": str(item.get("mission", "")).strip(),
                "deliverables": item.get("deliverables", [])
                if isinstance(item.get("deliverables", []), list)
                else []
            })

        result["selected_specialists"] = valid_specialists
        result["department"] = "technical"
        result["manager"] = "Technical Manager"

        # Planning alone never authorizes code changes or deployment.
        result["requires_ceo_approval"] = True

        result["execution_authorized"] = False
        result["message"] = (
            "Technical plan created. "
            "CEO approval is required before implementation."
        )

        if not valid_specialists:
            result["status"] = "REVIEW_REQUIRED"

        return result

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
