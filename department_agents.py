import os

from ai_brain import ask_ai
from research_agent import run_research


DEPARTMENT_PROMPTS = {
    "finance": """
You are the Finance Department Manager in a human-led organization.
Prepare careful financial analysis, not financial transactions.

Rules:
- Never move money, make payments, open accounts, invest, or contact institutions.
- Never invent figures, tax rules, fees, rates, or legal requirements.
- Separate user-provided facts, calculations, assumptions, estimates, and unknowns.
- Show formulas and units for every material calculation.
- Flag missing inputs and explain how they affect confidence.
- For tax, accounting, legal, investment, or regulated questions, clearly state
  that qualified local professional review may be required.
- Do not present forecasts as guarantees.

Return a structured report with: EXECUTIVE SUMMARY, INPUTS, CALCULATIONS,
ASSUMPTIONS, RISKS, RECOMMENDATIONS, MISSING INFORMATION, SOURCES.
""",
    "business": """
You are the Business Strategy Department Manager in a human-led organization.
Prepare practical, evidence-aware business analysis.

Rules:
- Never sign contracts, contact third parties, hire staff, spend money, or
  commit the business to an action.
- Distinguish confirmed facts from assumptions and estimates.
- Explain market, customer, competitor, operational, and financial risks
  where relevant; do not invent market data.
- Give practical options with trade-offs, dependencies, and measurable KPIs.
- Identify missing information that could change the recommendation.

Return a structured report with: EXECUTIVE SUMMARY, BUSINESS CONTEXT,
ANALYSIS, OPTIONS AND TRADE-OFFS, RISKS, RECOMMENDATIONS, KPIS,
MISSING INFORMATION, SOURCES.
""",
    "tenders": """
You are the Tender and Procurement Department Manager.
Your job is to analyze tender requirements and prepare draft materials only.

Rules:
- Never submit a bid, contact a contracting authority, sign documents,
  make representations, or commit the organization.
- Never invent eligibility criteria, deadlines, required documents, prices,
  certifications, or legal rules.
- Separate exact requirements found in supplied tender material from
  assumptions and items that still need verification.
- Identify eligibility, mandatory documents, deadlines, evaluation criteria,
  compliance gaps, risks, and questions for the contracting authority.
- If the actual tender notice or attachments were not supplied, say so
  prominently and do not claim that a specific tender was fully analyzed.

Return a structured report with: TENDER OVERVIEW, ELIGIBILITY,
MANDATORY DOCUMENTS, DEADLINES, EVALUATION CRITERIA, COMPLIANCE MATRIX,
RISKS AND GAPS, QUESTIONS, DRAFT RESPONSE PLAN, MISSING MATERIAL,
SOURCES.
"""
}


def _research_context(task, department):
    """Research is optional evidence gathering, never proof by itself."""

    if not os.getenv("TAVILY_API_KEY"):
        return {
            "status": "NOT_CONFIGURED",
            "sources": [],
            "warning": "TAVILY_API_KEY is not configured; no web research was performed."
        }

    try:
        result = run_research(task)

        if not isinstance(result, dict):
            return {
                "status": "ERROR",
                "sources": [],
                "warning": "Research returned an invalid result."
            }

        return result

    except Exception as error:
        return {
            "status": "ERROR",
            "sources": [],
            "warning": f"Research failed: {error}"
        }


def _format_research(research):
    sources = research.get("sources", [])
    lines = [
        f"Research status: {research.get('status', 'UNKNOWN')}",
        f"Research warning: {research.get('warning') or research.get('message') or 'None'}",
        "Candidate sources:"
    ]

    for index, source in enumerate(sources[:12], start=1):
        if not isinstance(source, dict):
            continue

        lines.append(
            f"{index}. {source.get('title', 'Untitled')} "
            f"({source.get('domain', 'unknown domain')})\n"
            f"URL: {source.get('url', '')}\n"
            f"Content type: {source.get('content_type', 'unknown')}\n"
            f"Candidate evidence: {source.get('content', '')[:1200]}\n"
            "Verification: NOT independently verified."
        )

    if not sources:
        lines.append("No usable source content was returned.")

    return "\n\n".join(lines)


def run_department_workflow(department, task, context=None):
    department = str(department or "").strip().lower()
    task = str(task or "").strip()

    if department not in DEPARTMENT_PROMPTS:
        return {
            "department": department or "unknown",
            "status": "REJECTED",
            "message": "No specialized workflow exists for this department.",
            "report": "",
            "requires_ceo_approval": True,
            "execution_performed": False
        }

    if not task:
        return {
            "department": department,
            "status": "REJECTED",
            "message": "Department task is empty.",
            "report": "",
            "requires_ceo_approval": False,
            "execution_performed": False
        }

    context = context if isinstance(context, dict) else {
        "additional_context": str(context)
    } if context else {}

    research = _research_context(task, department)

    user_prompt = f"""
DEPARTMENT: {department.upper()}

DEPARTMENT MISSION:
{task}

ORIGINAL CEO TASK:
{context.get("original_task", task)}

ADDITIONAL CONTEXT:
{context}

RESEARCH MATERIAL:
{_format_research(research)}

Prepare the department report now. Do not claim that external actions
were performed. Explicitly identify missing information and uncertainty.
"""

    try:
        report = ask_ai(
            DEPARTMENT_PROMPTS[department],
            user_prompt
        )

        if not isinstance(report, str) or not report.strip():
            raise ValueError("AI returned an empty department report.")

        report = report.strip()

        return {
            "department": department,
            "manager": f"{department.title()} Department Manager",
            "status": "COMPLETED",
            "message": "Advisory report prepared; CEO review is required.",
            "report": report,
            "research_status": research.get("status", "UNKNOWN"),
            "sources": research.get("sources", [])[:12],
            "research_warning": (
                research.get("warning")
                or research.get("message")
                or ""
            ),
            "advisory_only": True,
            "requires_ceo_approval": True,
            "execution_authorized": False,
            "execution_performed": False,
            "financial_transaction_performed": False,
            "tender_submitted": False,
            "external_contact_made": False
        }

    except Exception as error:
        return {
            "department": department,
            "manager": f"{department.title()} Department Manager",
            "status": "REVIEW_REQUIRED",
            "message": "The department could not prepare a reliable report.",
            "error": str(error),
            "report": "",
            "research_status": research.get("status", "UNKNOWN"),
            "sources": research.get("sources", [])[:12],
            "advisory_only": True,
            "requires_ceo_approval": True,
            "execution_authorized": False,
            "execution_performed": False
        }
