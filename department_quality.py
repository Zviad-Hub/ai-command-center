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
            ("strategy", "positioning", "value proposition", "options", "trade-off",
             "go-to-market", "strategic direction", "launch strategy", "business model"),
            ("assumption", "dependency", "risk", "recommendation", "execution",
             "implementation", "competitive advantage"),
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


TECHNICAL_ROLE_REQUIREMENTS = {
    "system_architect": (
        ("architecture", "system design", "components", "structure"),
        ("dependency", "trade-off", "risk", "scalability", "missing"),
    ),
    "backend_developer": (
        ("backend", "api", "endpoint", "server", "data model"),
        ("validation", "error handling", "transaction", "reliability", "testing"),
    ),
    "frontend_developer": (
        ("frontend", "ui", "interface", "component", "accessibility"),
        ("responsive", "interaction", "usability", "state", "testing"),
    ),
    "devops_engineer": (
        ("devops", "deployment", "infrastructure", "pipeline", "ci/cd"),
        ("rollback", "monitoring", "configuration", "security", "reliability"),
    ),
    "qa_engineer": (
        ("qa", "test", "testing", "acceptance criteria", "regression"),
        (
            "coverage", "assertion", "edge case", "quality", "validation",
            "test suite", "test plan", "test matrix", "acceptance criterion",
            "expected result", "pass/fail", "performance metric",
            "measurable threshold", "test result artifact", "test strategy",
            "test scenario", "failure path", "verification",
        ),
    ),
    "code_reviewer": (
        ("code review", "code quality", "maintainability", "defect", "logic"),
        ("evidence", "risk", "recommendation", "readability", "test"),
    ),
    "security_engineer": (
        ("security", "authentication", "authorization", "threat", "access control"),
        ("defensive", "mitigation", "vulnerability", "risk", "hardening"),
    ),
    "database_engineer": (
        ("database", "schema", "query", "migration", "sql"),
        ("integrity", "index", "performance", "transaction", "consistency"),
    ),
}


def validate_technical_specialists(manager_plan, specialist_results):
    """Validate selected Technical roles before manager synthesis."""
    issues = []
    plan = manager_plan if isinstance(manager_plan, dict) else {}
    assignments = plan.get("selected_specialists", [])
    if not isinstance(assignments, list) or not assignments:
        issues.append("technical: manager plan contains no selected specialists")
        assignments = []

    selected = []
    for assignment in assignments:
        specialist_id = (
            assignment.get("id") or assignment.get("specialist") or assignment.get("name") or ""
            if isinstance(assignment, dict) else str(assignment or "")
        )
        specialist_id = str(specialist_id).strip()
        if specialist_id not in TECHNICAL_ROLE_REQUIREMENTS:
            issues.append(f"technical: unknown or invalid specialist assignment {specialist_id or '<empty>'}")
        else:
            selected.append(specialist_id)

    if len(selected) != len(set(selected)):
        issues.append("technical: duplicate specialist assignments are not allowed")

    results = specialist_results if isinstance(specialist_results, list) else []
    result_map = {}
    for item in results:
        if isinstance(item, dict):
            specialist_id = str(item.get("specialist") or item.get("id") or "")
            if specialist_id in result_map:
                issues.append(f"{specialist_id}: duplicate specialist result")
            result_map[specialist_id] = item

    for specialist_id in selected:
        item = result_map.get(specialist_id)
        if not isinstance(item, dict) or item.get("status") != "COMPLETED":
            issues.append(f"{specialist_id}: selected specialist has no completed result")
            continue
        report = str(item.get("report") or "").casefold()
        if not report.strip():
            issues.append(f"{specialist_id}: completed result has no report")
            continue
        for index, alternatives in enumerate(TECHNICAL_ROLE_REQUIREMENTS[specialist_id]):
            if not any(term in report for term in alternatives):
                issues.append(f"{specialist_id}: report lacks role-specific evidence element {index + 1}")

    unexpected = sorted(set(result_map) - set(selected))
    if unexpected:
        issues.append("unassigned specialist results: " + ", ".join(unexpected))

    return {
        "status": "PASS" if not issues else "REVIEW_REQUIRED",
        "selected_specialists": len(assignments),
        "validated_specialists": len(selected),
        "issues": issues,
        "scope_note": "Deterministic role and report-shape checks; not proof of factual accuracy.",
    }
