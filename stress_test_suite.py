"""Deterministic routing stress tests and structural quality scoring.

No LLM calls, external network activity, or department actions are performed.
"""
from director import route_task


ROUTING_SCENARIOS = [
    {"id": "finance_budget", "task": "Prepare a financial budget and profit forecast.", "expected": ["finance"]},
    {"id": "business_strategy", "task": "Create a business strategy and market analysis.", "expected": ["business"]},
    {"id": "tender_compliance", "task": "Review this tender procurement bid and eligibility requirements.", "expected": ["tenders"]},
    {"id": "pentester_scope", "task": "Prepare a cybersecurity vulnerability assessment plan for my own application.", "expected": ["pentester"]},
    {"id": "technical_code_review", "task": "Review this Python code and identify bugs.", "expected": ["technical"]},
    {"id": "media_with_audit", "task": "Create one YouTube video script about an old mystery.", "expected": ["media", "audit"]},
    {"id": "independent_audit", "task": "Perform an independent audit of this report.", "expected": ["audit"]},
    {"id": "finance_business", "task": "Prepare a business strategy with a monthly budget and profit forecast.", "expected": ["finance", "business"]},
    {"id": "tender_finance", "task": "Analyze tender pricing, procurement costs and financial risks.", "expected": ["tenders", "finance"]},
    {"id": "technical_security", "task": "Review the API code and assess cybersecurity vulnerabilities.", "expected": ["pentester", "technical"]},
]


def run_routing_stress_tests():
    results = []
    for scenario in ROUTING_SCENARIOS:
        try:
            plan = route_task(scenario["task"])
            actual = plan.get("departments", []) if isinstance(plan, dict) else []
            passed = actual == scenario["expected"]
            results.append({
                "scenario_id": scenario["id"],
                "task": scenario["task"],
                "expected_departments": scenario["expected"],
                "actual_departments": actual,
                "routing_method": plan.get("routing_method", "UNKNOWN") if isinstance(plan, dict) else "INVALID",
                "passed": passed,
                "error": None,
            })
        except Exception as error:
            results.append({
                "scenario_id": scenario["id"],
                "task": scenario["task"],
                "expected_departments": scenario["expected"],
                "actual_departments": [],
                "routing_method": "ERROR",
                "passed": False,
                "error": str(error),
            })

    total = len(results)
    passed = sum(1 for item in results if item["passed"])
    return {
        "suite": "DIRECTOR_ROUTING_STRESS_TEST",
        "status": "PASS" if passed == total else "NEEDS_REVIEW",
        "passed": passed,
        "failed": total - passed,
        "total": total,
        "score_out_of_10": round(passed / total * 10, 2) if total else 0,
        "results": results,
        "external_actions_performed": False,
    }


def evaluate_task_record(record):
    """Score structural quality; this is not proof of factual correctness."""
    if not isinstance(record, dict):
        return {"score_out_of_10": 0, "status": "REJECTED", "checks": [], "issues": ["Task record must be an object."]}

    departments = record.get("departments", [])
    results = record.get("results", [])
    routing = record.get("routing", {})
    expected = routing.get("departments", []) if isinstance(routing, dict) else []
    issues = []
    checks = []
    score = 0

    def check(name, passed, points, issue):
        nonlocal score
        checks.append({"name": name, "passed": bool(passed), "points": points if passed else 0})
        if passed:
            score += points
        else:
            issues.append(issue)

    check("routing_consistency", isinstance(departments, list) and bool(departments) and departments == expected, 2,
          "Recorded departments do not match the Director routing plan.")

    result_departments = [item.get("department") for item in results if isinstance(item, dict)] if isinstance(results, list) else []
    check("department_coverage", isinstance(departments, list) and bool(departments) and isinstance(results, list) and bool(results) and len(results) == len(departments) and result_departments == departments, 2,
          "Every routed department must return exactly one result in routing order.")

    safe = isinstance(results, list) and all(
        isinstance(item, dict)
        and item.get("execution_performed") is not True
        and item.get("execution_authorized") is not True
        and item.get("external_network_activity") is not True
        and item.get("financial_transaction_performed") is not True
        and item.get("tender_submitted") is not True
        and item.get("external_contact_made") is not True
        and item.get("active_testing_performed") is not True
        and item.get("active_testing_available") is not True
        and item.get("code_modified") is not True
        and item.get("tests_executed") is not True
        for item in results
    )
    check("execution_safety", safe, 2,
          "A department claims an execution or external action forbidden by this advisory workflow.")

    approval = isinstance(results, list) and all(
        isinstance(item, dict) and (
            item.get("requires_ceo_approval") is True
            or item.get("advisory_only") is True
            or item.get("publication_approved") is False
        )
        for item in results
    )
    check("human_approval_gate", approval, 2,
          "A department result is missing its human approval gate.")

    honest = isinstance(results, list) and all(
        isinstance(item, dict) and (
            item.get("status") in ("COMPLETED", "PASS", "APPROVED", "REVIEW_REQUIRED", "PREPARATION_ONLY", "PASSIVE_REVIEW_ONLY")
            and (
                item.get("status") != "COMPLETED"
                or bool(
                (isinstance(item.get("report"), str) and item["report"].strip())
                or (isinstance(item.get("artifact"), str) and item["artifact"].strip())
                or item.get("publication_approved") is False
                or isinstance(item.get("specialist_results"), list)
                or isinstance(item.get("summary"), dict)
                )
            )
        )
        for item in results
    )
    check("completion_evidence", honest, 2,
          "A department claims completion without returning recognizable output.")

    return {
        "score_out_of_10": score,
        "status": "PASS" if score == 10 else "NEEDS_REVIEW",
        "checks": checks,
        "issues": issues,
        "human_review_required": True,
    }
