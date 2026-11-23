"""Evidence-oriented performance scorecards for AI department runs.

The scorecard is observability, not a factual-accuracy verdict. It never
changes department output, retries work, or grants permission to act.
"""


def _present(value):
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (dict, list, tuple)):
        return bool(value)
    return value is not None


def _specialist_counts(result):
    completed = failed = not_run = 0
    specialist_results = result.get("specialist_results")
    if isinstance(specialist_results, list):
        for item in specialist_results:
            if not isinstance(item, dict):
                continue
            status = str(item.get("status") or "").upper()
            if status == "COMPLETED":
                completed += 1
            elif status in {"ERROR", "FAILED"}:
                failed += 1
            elif status == "NOT_RUN":
                not_run += 1

    reports = result.get("specialist_reports")
    if isinstance(reports, dict):
        completed = max(completed, len(reports))
    failures = result.get("specialist_failures")
    if isinstance(failures, list):
        failed = max(failed, len(failures))
    skipped = result.get("specialist_not_run")
    if isinstance(skipped, list):
        not_run = max(not_run, len(skipped))

    if not any(key in result for key in (
        "specialist_results", "specialist_reports",
        "specialist_failures", "specialist_not_run"
    )):
        return None
    return {
        "completed": completed,
        "failed": failed,
        "not_run": not_run,
        "selected": completed + failed + not_run,
    }


def build_agent_performance_scorecard(results, organization_audit, semantic_audit):
    """Build a conservative per-department scorecard from recorded gate outcomes."""
    entries = results if isinstance(results, list) else []
    organization_audit = organization_audit if isinstance(organization_audit, dict) else {}
    semantic_audit = semantic_audit if isinstance(semantic_audit, dict) else {}

    checks = organization_audit.get("department_checks")
    check_map = {}
    if isinstance(checks, list):
        for check in checks:
            if isinstance(check, dict):
                name = str(check.get("department") or "").strip().lower()
                if name and name not in check_map:
                    check_map[name] = check

    departments = []
    for result in entries:
        if not isinstance(result, dict):
            continue
        department = str(result.get("department") or "unknown").strip().lower()
        structural_check = check_map.get(department, {})
        structural_status = str(structural_check.get("status") or "MISSING").upper()
        specialist_validation = result.get("specialist_quality_validation")
        evidence_validation = result.get("evidence_validation")
        reviewer_passed = result.get("quality_review_passed")
        gates = {
            "organization_contract": structural_status,
            "specialist_validation": (
                str(specialist_validation.get("status") or "UNKNOWN").upper()
                if isinstance(specialist_validation, dict) else "NOT_APPLICABLE_OR_MISSING"
            ),
            "evidence_validation": (
                str(evidence_validation.get("status") or "UNKNOWN").upper()
                if isinstance(evidence_validation, dict) else "NOT_APPLICABLE_OR_MISSING"
            ),
            "independent_review": (
                "PASS" if reviewer_passed is True
                else "FAIL" if reviewer_passed is False else "NOT_RECORDED"
            ),
        }
        row = {
            "department": department,
            "run_status": str(result.get("status") or "UNKNOWN").upper(),
            "scorecard_status": "PASS" if structural_status == "PASS" else "REVIEW_REQUIRED",
            "gates": gates,
            "report_present": _present(result.get("report")),
            "specialists": _specialist_counts(result),
            "requires_ceo_approval": result.get("requires_ceo_approval"),
            "execution_authorized": result.get("execution_authorized"),
            "execution_performed": result.get("execution_performed"),
            "blocker_count": len(structural_check.get("issues", []))
                if isinstance(structural_check.get("issues"), list) else 0,
        }
        departments.append(row)

    org_status = str(organization_audit.get("status") or "UNKNOWN").upper()
    semantic_status = str(semantic_audit.get("status") or "NOT_RUN").upper()
    all_structural_pass = bool(departments) and all(
        item["scorecard_status"] == "PASS" for item in departments
    ) and org_status == "PASS"
    ready_for_human_review = all_structural_pass and semantic_status == "PASS"

    return {
        "status": "READY_FOR_HUMAN_REVIEW" if ready_for_human_review else "REVIEW_REQUIRED",
        "department_count": len(departments),
        "departments_structurally_passed": sum(
            item["scorecard_status"] == "PASS" for item in departments
        ),
        "departments_review_required": sum(
            item["scorecard_status"] != "PASS" for item in departments
        ),
        "organization_audit_status": org_status,
        "semantic_audit_status": semantic_status,
        "departments": departments,
        "human_review_required": True,
        "limitations": [
            "This scorecard summarizes recorded workflow gates and specialist completion counts.",
            "It does not measure factual accuracy, reasoning quality, or real-world task success.",
            "It does not modify outputs, trigger retries, or authorize consequential actions.",
        ],
    }
