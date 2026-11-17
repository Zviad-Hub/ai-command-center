import json

from ai_brain import ask_ai
from error_diagnostics import safe_error_code


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
- Every selected specialist must use an exact ID from the list above.
- Every selected specialist must have a non-empty, specific mission.

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
            "deliverables": ["Expected deliverable"]
        }
    ],
    "execution_plan": ["Step 1", "Step 2"],
    "testing_strategy": ["Testing requirement"],
    "risks": ["Identified risk"],
    "requires_ceo_approval": true,
    "approval_reasons": ["Reason requiring approval"],
    "final_deliverables": ["Expected final result"]
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


def _safe_fallback_plan(task, reason):
    """Create a bounded advisory plan when the AI plan is malformed or unusable."""
    lowered = str(task or "").casefold()

    if any(term in lowered for term in ("frontend", "front-end", "ui", "interface", "css", "react")):
        selected = [
            ("frontend_developer", "Review only the supplied UI requirements, screenshots, or source material. Identify usability, accessibility, responsive-layout, and client-side risks; do not claim to inspect unavailable files."),
            ("qa_engineer", "Create a focused UI regression and accessibility test checklist from the supplied requirements. Propose tests only; do not execute them."),
        ]
    elif any(term in lowered for term in ("database", "sql", "query", "migration", "schema")):
        selected = [
            ("database_engineer", "Review supplied database schema, queries, and migration evidence. Identify data-integrity and performance questions; do not invent unseen schema details."),
            ("backend_developer", "Review supplied backend/database integration evidence and identify validation, transaction, and error-handling risks. Do not claim to inspect unavailable code."),
        ]
    elif any(term in lowered for term in ("deploy", "deployment", "ci/cd", "pipeline", "infrastructure", "server", "docker")):
        selected = [
            ("devops_engineer", "Review supplied deployment and infrastructure configuration only. Identify reliability, configuration, and rollback considerations; do not deploy or access external systems."),
            ("qa_engineer", "Prepare a pre-release verification and rollback test checklist based only on supplied deployment requirements. Do not run commands or tests."),
        ]
    elif any(term in lowered for term in ("security", "vulnerability", "authentication", "authorization", "pentest")):
        selected = [
            ("security_engineer", "Perform passive defensive analysis of supplied code, configuration, or architecture only. Do not scan, probe, connect to targets, generate exploits, or perform active testing."),
            ("code_reviewer", "Review supplied source material for security-relevant coding risks and recommend defensive fixes. Do not claim to inspect files that were not provided."),
        ]
    elif any(term in lowered for term in ("api", "backend", "endpoint", "server", "request", "response")):
        selected = [
            ("backend_developer", "Review supplied API/backend requirements or source material for logic, validation, error-handling, and reliability risks. Do not claim to inspect unavailable files."),
            ("qa_engineer", "Create API unit, integration, and failure-mode test scenarios from the supplied evidence. Propose tests only; do not execute them."),
        ]
    else:
        selected = [
            ("system_architect", "Translate the supplied task into a bounded architecture and evidence-review plan. Identify dependencies and missing inputs; do not invent repository facts."),
            ("qa_engineer", "Create acceptance criteria and a prioritized test strategy from the supplied task. Propose tests only; do not execute them."),
        ]

    selected_specialists = [
        {
            "specialist": specialist_id,
            "mission": mission,
            "deliverables": [
                "Evidence-based findings",
                "Missing information and assumptions",
                "Prioritized recommendations",
            ],
        }
        for specialist_id, mission in selected
    ]

    return {
        "department": "technical",
        "manager": "Technical Manager",
        "status": "PLAN_CREATED",
        "planning_method": "SAFE_RULE_BASED_FALLBACK",
        "planning_warning": str(reason),
        "task_understanding": (
            "The AI-generated specialist plan was unavailable or unusable. "
            "A conservative advisory plan was selected from the task keywords."
        ),
        "selected_specialists": selected_specialists,
        "execution_plan": [
            "Review only the task and evidence explicitly supplied by the CEO.",
            "Have the selected specialists return separate evidence-based findings.",
            "Synthesize findings, unknowns, and recommendations for independent review.",
        ],
        "testing_strategy": [
            "Prepare proposed acceptance and regression tests only.",
            "Do not execute tests or modify code without separate CEO approval.",
        ],
        "risks": [
            "The fallback plan is rule-based and may need CEO refinement.",
            "No repository or external system access is implied.",
        ],
        "requires_ceo_approval": True,
        "approval_reasons": [
            "Any implementation, code modification, test execution, or deployment requires separate CEO approval.",
        ],
        "final_deliverables": [
            "Specialist findings",
            "Prioritized technical recommendations",
            "Evidence gaps and proposed test plan",
        ],
        "execution_authorized": False,
        "message": "A conservative technical plan was created using safe fallback rules; CEO approval remains required.",
    }


def run_technical_manager(task):
    task = str(task or "").strip()

    if not task:
        return {
            "department": "technical",
            "manager": "Technical Manager",
            "status": "REJECTED",
            "message": "Technical task is empty.",
            "selected_specialists": [],
            "requires_ceo_approval": False,
            "execution_authorized": False,
        }

    user_prompt = f"CEO TASK:\n{task}"

    try:
        response = ask_ai(TECHNICAL_MANAGER_PROMPT, user_prompt)
    except Exception as error:
        return {
            "department": "technical",
            "manager": "Technical Manager",
            "status": "ERROR",
            "message": "Technical planning provider call failed.",
            "error": "TECHNICAL_PLANNING_FAILED",
            "error_code": safe_error_code(error),
            "selected_specialists": [],
            "requires_ceo_approval": True,
            "execution_authorized": False,
        }

    try:
        result = extract_json(response)
        if not isinstance(result, dict):
            raise ValueError("Technical Manager response must be a JSON object.")
    except (ValueError, json.JSONDecodeError):
        return _safe_fallback_plan(task, "AI manager returned malformed or non-JSON output.")

    selected = result.get("selected_specialists", [])
    if not isinstance(selected, list):
        selected = []

    valid_specialists = []
    for item in selected:
        if not isinstance(item, dict):
            continue

        specialist = str(
            item.get("specialist") or item.get("id") or ""
        ).strip()
        mission = str(item.get("mission", "")).strip()

        if specialist not in TECHNICAL_SPECIALISTS or not mission:
            continue

        deliverables = item.get("deliverables", [])
        if not isinstance(deliverables, list):
            deliverables = []

        valid_specialists.append({
            "specialist": specialist,
            "mission": mission,
            "deliverables": [
                str(value).strip()
                for value in deliverables
                if str(value).strip()
            ],
        })

    if not valid_specialists:
        return _safe_fallback_plan(
            task,
            "AI manager returned no valid specialist assignments.",
        )

    result["selected_specialists"] = valid_specialists
    result["department"] = "technical"
    result["manager"] = "Technical Manager"
    result["status"] = "PLAN_CREATED"
    result["planning_method"] = "AI_MANAGER"
    result["requires_ceo_approval"] = True
    result["execution_authorized"] = False
    result["message"] = (
        "Technical plan created by the AI manager. "
        "CEO approval is required before implementation."
    )

    return result
