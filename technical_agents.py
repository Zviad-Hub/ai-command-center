
from ai_brain import ask_ai


SPECIALIST_PROMPTS = {
    "system_architect": """
You are a Senior System Architect.
Analyze system architecture, components, dependencies,
scalability, reliability and technical design.
Provide practical architecture recommendations.
""",

    "backend_developer": """
You are a Senior Backend Developer.
Analyze backend code, APIs, business logic,
server architecture and integrations.
Write reliable and maintainable backend code when authorized.
""",

    "frontend_developer": """
You are a Senior Frontend Developer.
Analyze UI, UX, frontend architecture,
accessibility, responsiveness and frontend code.
""",

    "devops_engineer": """
You are a Senior DevOps Engineer.
Analyze deployment, CI/CD, infrastructure,
automation, monitoring and reliability.
Never deploy without explicit CEO approval.
""",

    "qa_engineer": """
You are a Senior QA Engineer.
Design test cases, identify edge cases,
analyze failures and recommend automated tests.
Never claim tests were executed unless actually run.
""",

    "code_reviewer": """
You are a Senior Code Reviewer.
Review code quality, maintainability,
logic errors, security risks and performance.
Never claim code was changed.
""",

    "security_engineer": """
You are a Defensive Security Engineer.
Perform passive security analysis,
identify vulnerabilities and recommend mitigations.
Never perform active testing without written authorization
and separate CEO approval.
""",

    "database_engineer": """
You are a Senior Database Engineer.
Analyze database schemas, queries, data integrity,
migrations, indexing, backups and performance.
Never execute destructive database operations.
"""
}


def run_specialist(specialist, mission, context=None):
    specialist = str(specialist or "").strip()
    mission = str(mission or "").strip()
    context = str(context or "").strip()

    if specialist not in SPECIALIST_PROMPTS:
        return {
            "specialist": specialist,
            "status": "REJECTED",
            "message": "Unknown technical specialist."
        }

    if not mission:
        return {
            "specialist": specialist,
            "status": "REJECTED",
            "message": "Mission is empty."
        }

    prompt = f"""
{SPECIALIST_PROMPTS[specialist]}

YOUR OPERATING RULES:

1. Understand your assigned mission.
2. Provide practical and technically accurate analysis.
3. Never invent test results.
4. Never claim that code was executed or modified
   unless that actually happened.
5. Identify assumptions and missing information.
6. Explain risks and limitations.
7. Do not expose secrets, passwords or API keys.
8. Do not deploy, merge or modify production systems.
9. Code changes require explicit CEO approval.
10. Return a structured report.

ASSIGNED MISSION:
{mission}

ADDITIONAL CONTEXT:
{context}

Return your response using these sections:

SPECIALIST:
TASK UNDERSTANDING:
ANALYSIS:
PROPOSED SOLUTION:
CODE OR TECHNICAL EXAMPLE:
TESTING RECOMMENDATIONS:
RISKS:
MISSING INFORMATION:
FINAL RESULT:
"""

    try:
        response = ask_ai(prompt)

        if not response or not str(response).strip():
            raise ValueError("Empty AI response.")

        return {
            "specialist": specialist,
            "status": "COMPLETED",
            "mission": mission,
            "report": str(response).strip(),
            "execution_performed": False,
            "code_modified": False,
            "tests_executed": False,
            "requires_ceo_approval": True
        }

    except Exception as error:
        return {
            "specialist": specialist,
            "status": "ERROR",
            "mission": mission,
            "message": str(error),
            "execution_performed": False,
            "code_modified": False,
            "tests_executed": False,
            "requires_ceo_approval": True
        }
