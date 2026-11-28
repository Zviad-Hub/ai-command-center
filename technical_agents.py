
from ai_brain import ask_ai
from error_diagnostics import safe_error_code
from report_context import bounded_text


# ==================================================
# TECHNICAL SPECIALISTS
# ==================================================

SPECIALIST_PROMPTS = {
    "system_architect": """
You are a Senior System Architect.
Analyze software architecture, components, dependencies,
scalability, reliability, and technical risks.
Provide practical architecture recommendations.
""",

    "backend_developer": """
You are a Senior Backend Developer.
Analyze backend logic, APIs, server architecture,
business logic, data processing, and error handling.
Provide concrete implementation recommendations.
""",

    "frontend_developer": """
You are a Senior Frontend Developer.
Analyze user interfaces, usability, frontend logic,
accessibility, responsiveness, and client-side errors.
Provide practical recommendations.
""",

    "devops_engineer": """
You are a Senior DevOps Engineer.
Analyze deployment, CI/CD, infrastructure,
environment variables, configuration, and reliability.
Provide practical recommendations.
""",

    "qa_engineer": """
You are a Senior QA Engineer.
Analyze requirements, test scenarios, edge cases,
expected behavior, and possible software defects.
Provide a compact **TEST COVERAGE MATRIX** linking each requirement or risk to:
(1) a test scenario, (2) expected result, (3) a concrete assertion or measurable
acceptance criterion, and (4) priority. Include negative, boundary, edge-case,
and failure-path cases where relevant. List required test suites, performance
metrics, pass/fail thresholds, missing test data, and the evidence artifacts
needed to validate results. Explicitly identify coverage gaps. Propose tests,
but do not claim they were executed.
""",

    "code_reviewer": """
You are a Senior Code Reviewer.
Review code quality, maintainability, readability,
logic errors, potential bugs, and performance risks.
Do not claim to have inspected files that were not provided.
""",

    "security_engineer": """
You are a Defensive Security Engineer.
Analyze application security risks and recommend
defensive improvements.
Never perform unauthorized testing or exploitation.
""",

    "database_engineer": """
You are a Senior Database Engineer.
Analyze database structure, relationships, queries,
data integrity, migrations, and performance.
Provide practical recommendations.
"""
}


# ==================================================
# COMMON UTILITIES
# ==================================================

def normalize_specialist(specialist):
    """
    Supports both a specialist ID string and a
    specialist dictionary returned by Technical Manager.
    """

    if isinstance(specialist, dict):
        specialist_id = specialist.get("id", "")
        specialist_name = specialist.get("name", specialist_id)
        specialist_mission = specialist.get("mission", "")
    else:
        specialist_id = str(specialist or "").strip()
        specialist_name = specialist_id
        specialist_mission = ""

    return (
        str(specialist_id).strip(),
        str(specialist_name).strip(),
        str(specialist_mission).strip()
    )


# ==================================================
# RUN SPECIALIST
# ==================================================

def run_specialist(specialist, mission=None, context=None):

    specialist_id, specialist_name, assigned_mission = (
        normalize_specialist(specialist)
    )

    if specialist_id not in SPECIALIST_PROMPTS:
        return {
            "specialist": specialist_id,
            "status": "ERROR",
            "error": "Unknown technical specialist.",
            "execution_performed": False,
            "code_modified": False,
            "tests_executed": False,
            "requires_ceo_approval": True
        }

    # Prefer the specific mission assigned by the manager.
    actual_mission = assigned_mission or str(mission or "").strip()

    if not actual_mission:
        return {
            "specialist": specialist_id,
            "status": "ERROR",
            "error": "No mission was provided.",
            "execution_performed": False,
            "code_modified": False,
            "tests_executed": False,
            "requires_ceo_approval": True
        }

    context_text = str(context or "").strip()

    system_prompt = SPECIALIST_PROMPTS[specialist_id]

    user_prompt = f"""
SPECIALIST: {specialist_name}

ASSIGNED MISSION:
{bounded_text(actual_mission, 4500)}

ADDITIONAL CONTEXT:
{bounded_text(context_text, 8500) if context_text else "No additional context provided."}

INSTRUCTIONS:

1. Analyze only your assigned technical responsibility.
2. Keep your report concise (maximum 350 words); prioritize evidence, material risks,
   concrete recommendations, and missing inputs over repeated background.
3. Give practical, specific recommendations.
4. Identify risks, missing information, and dependencies.
5. Clearly distinguish facts from assumptions.
6. If source code is not provided, do not claim to have inspected it.
7. Do not claim that code was modified or tests were executed.
8. Do not deploy, execute, or modify anything.
9. Any real implementation or execution requires separate CEO approval.

Return a structured report with these sections:

SPECIALIST:
MISSION:
ANALYSIS:
TEST COVERAGE MATRIX:
TEST SUITES AND METRICS:
FINDINGS:
RECOMMENDATIONS:
RISKS:
DEPENDENCIES:
MISSING TEST DATA AND EVIDENCE:
NEXT STEPS:
"""

    try:
        response = ask_ai(system_prompt, user_prompt)

        if not response or not str(response).strip():
            raise ValueError("AI returned an empty specialist report.")

        return {
            "specialist": specialist_id,
            "specialist_name": specialist_name,
            "status": "COMPLETED",
            "report": str(response).strip(),
            "execution_performed": False,
            "code_modified": False,
            "tests_executed": False,
            "requires_ceo_approval": True,
            "execution_authorized": False
        }

    except Exception as error:
        return {
            "specialist": specialist_id,
            "specialist_name": specialist_name,
            "status": "ERROR",
            "error": "SPECIALIST_FAILED",
            "error_code": safe_error_code(error),
            "execution_performed": False,
            "code_modified": False,
            "tests_executed": False,
            "requires_ceo_approval": True,
            "execution_authorized": False
        }
