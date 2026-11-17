"""Deterministic, independent quality checks for advisory department specialists.

These checks validate role coverage and minimum evidence discipline. They are
not factual verification and never replace the independent AI reviewer.
"""

ROLE_REQUIREMENTS = {
    "finance": {
        "financial_analyst": (
            ("calculation", "formula", "arithmetic", "revenue", "cost", "margin"),
            ("inputs", "assumption", "units", "missing", "uncertainty"),
        ),
        "risk_controller": (
            ("risk", "liquidity", "downside", "sensitivity", "exposure", "compliance"),
            ("mitigation", "uncertainty", "missing", "assumption", "control"),
        ),
        "budget_planner": (
            ("budget", "forecast", "scenario", "cash flow", "projection"),
            ("assumption", "missing", "inputs", "sensitivity", "cost"),
        ),
    },
    "business": {
        "market_analyst": (
            ("market", "customer", "demand", "competitor", "audience"),
            ("validation", "evidence", "unknown", "assumption", "research"),
        ),
        "strategy_planner": (
            ("strategy", "positioning", "value proposition", "options", "trade-off"),
            ("assumption", "dependency", "risk", "recommendation", "execution"),
        ),
        "operations_kpi_analyst": (
            ("kpi", "operations", "process", "capacity", "staffing"),
            ("formula", "measure", "data", "missing", "workflow"),
        ),
    },
    "tenders": {
        "eligibility_analyst": (
            ("eligibility", "criteria", "official tender", "requirements"),
            ("not provided", "cannot confirm", "evidence", "verification", "unknown"),
        ),
        "compliance_document_analyst": (
            ("compliance", "document", "checklist", "requirement", "registration"),
            ("missing", "unclear", "not provided", "met", "validity", "evidence"),
        ),
        "pricing_risk_analyst": (
            ("pricing", "price", "cost", "quantity", "financial"),
            ("risk", "assumption", "missing", "uncertainty", "sensitivity"),
        ),
    },
}


def validate_specialist_reports(department, specialist_reports):
    """Return a structured PASS/REVIEW_REQUIRED result for named specialist outputs."""
    requirements = ROLE_REQUIREMENTS.get(str(department or "").casefold())
    issues = []
    reports = specialist_reports if isinstance(specialist_reports, dict) else {}

    if requirements is None:
        issues.append(f"{department}: no independent specialist contract is defined")
    else:
        for specialist_id, groups in requirements.items():
            report = reports.get(specialist_id)
            if not isinstance(report, str) or not report.strip():
                issues.append(f"{specialist_id}: required specialist report is missing or empty")
                continue
            lowered = report.casefold()
            for index, alternatives in enumerate(groups):
                if not any(term in lowered for term in alternatives):
                    issues.append(
                        f"{specialist_id}: report lacks role-specific evidence element {index + 1}"
                    )

        unexpected = sorted(set(reports) - set(requirements))
        if unexpected:
            issues.append("unexpected specialist IDs: " + ", ".join(unexpected))

    return {
        "status": "PASS" if not issues else "REVIEW_REQUIRED",
        "checked_specialists": len(reports),
        "expected_specialists": len(requirements or {}),
        "issues": issues,
        "scope_note": "Deterministic role/evidence-shape checks; not proof of factual accuracy.",
    }
