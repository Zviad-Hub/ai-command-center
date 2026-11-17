"""Organization-wide deterministic handoff and completion audit.

This layer validates orchestration integrity and department-specific gates.
It cannot prove factual truth or semantic satisfaction of the CEO request;
those remain explicit human-review responsibilities.
"""


CORE_DEPARTMENTS = {"finance", "business", "tenders", "technical", "pentester"}
def _nonempty(value):
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return bool(value) and any(_nonempty(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return bool(value) and any(_nonempty(item) for item in value)
    return False


def _check_department_result(department, result):
    issues = []
    status = str(result.get("status") or "").upper()

    if department in {"finance", "business", "tenders", "technical"}:
        if status != "COMPLETED":
            issues.append(f"{department}: final status is {status or 'MISSING'}, not COMPLETED")
    elif department == "pentester":
        if status not in {"PREPARATION_ONLY", "PASSIVE_REVIEW_ONLY"}:
            issues.append(f"pentester: expected a passive-only result, received {status or 'MISSING'}")
    elif department == "media":
        # Media intentionally stops at REVIEW_REQUIRED; publication is never auto-approved.
        if status != "REVIEW_REQUIRED":
            issues.append(f"media: expected REVIEW_REQUIRED pending CEO publication approval, received {status or 'MISSING'}")
        if result.get("publication_approved") is not False:
            issues.append("media: publication_approved must be explicitly false")
        if not _nonempty(result.get("edited_script")):
            issues.append("media: final edited script is missing")
        if not _nonempty(result.get("fact_check")):
            issues.append("media: final fact-check is missing")
        if not isinstance(result.get("validation"), dict):
            issues.append("media: final script validation record is missing")
    elif department == "audit":
        if status != "PASSED_WITH_LIMITATIONS":
            issues.append(f"audit: independent audit did not pass ({status or 'MISSING'})")
        summary = result.get("summary") if isinstance(result.get("summary"), dict) else {}
        if not isinstance(summary.get("total_checks"), int) or summary.get("total_checks", 0) < 1:
            issues.append("audit: no completed audit checks were recorded")
        if summary.get("failed_checks") != 0:
            issues.append("audit: one or more independent checks failed")
        if result.get("publication_approved") is not False:
            issues.append("audit: publication_approved must remain explicitly false")
        if result.get("final_decision") != "CEO_APPROVAL_REQUIRED":
            issues.append("audit: final CEO approval boundary is missing")
    else:
        issues.append(f"{department}: no organization audit contract exists")
        return issues

    if department in CORE_DEPARTMENTS:
        if result.get("requires_ceo_approval") is not True:
            issues.append(f"{department}: CEO approval must remain explicitly required")
        if result.get("execution_authorized") is not False:
            issues.append(f"{department}: execution_authorized must be explicitly false")
        if result.get("execution_performed") is not False:
            issues.append(f"{department}: execution_performed must be explicitly false")
        if not _nonempty(result.get("report")):
            issues.append(f"{department}: final report is missing")

    safety_flags = (
        "execution_performed",
        "execution_authorized",
        "external_network_activity",
        "financial_transaction_performed",
        "tender_submitted",
        "external_contact_made",
        "active_testing_performed",
        "active_testing_available",
        "code_modified",
        "tests_executed",
        "exploit_code_generated",
    )
    for field in safety_flags:
        if field in result and result[field] is not False:
            issues.append(f"{department}: unsafe or ambiguous {field} flag")

    if department in {"finance", "business", "tenders", "technical"}:
        validation = result.get("specialist_quality_validation")
        if not isinstance(validation, dict) or validation.get("status") != "PASS":
            issues.append(f"{department}: independent specialist quality validation did not pass")
        if result.get("quality_review_passed") is not True:
            issues.append(f"{department}: independent manager/reviewer quality gate did not pass")

    if department == "pentester":
        validation = result.get("evidence_validation")
        if not isinstance(validation, dict) or validation.get("status") not in {"VALIDATED", "UNVERIFIED"}:
            issues.append("pentester: independent evidence validation is missing or failed")
        if result.get("quality_review_passed") is not True:
            issues.append("pentester: independent security review did not pass")
        if result.get("written_authorization_verified") is not False:
            issues.append("pentester: written authorization must not be treated as verified automatically")
        if result.get("requires_human_scope_review") is not True:
            issues.append("pentester: human scope review must remain required")

    return issues


def audit_organization_task(original_task, departments, results):
    """Audit department handoffs and final status without rewriting department outputs."""
    expected = list(dict.fromkeys(
        item for item in departments if isinstance(item, str) and item.strip()
    )) if isinstance(departments, list) else []
    entries = results if isinstance(results, list) else []
    issues = []
    checks = []

    if not str(original_task or "").strip():
        issues.append("original CEO task is missing")
    if not expected:
        issues.append("no departments were selected")

    by_department = {}
    for index, result in enumerate(entries):
        if not isinstance(result, dict):
            issues.append(f"result {index + 1} is not an object")
            continue
        department = str(result.get("department") or "").strip().lower()
        if not department:
            issues.append(f"result {index + 1} has no department identity")
            continue
        if department in by_department:
            issues.append(f"{department}: duplicate department result")
        else:
            by_department[department] = result
        if department not in expected:
            issues.append(f"{department}: unexpected department result")

    for department in expected:
        result = by_department.get(department)
        if not isinstance(result, dict):
            issue = f"{department}: expected department result is missing"
            checks.append({"department": department, "status": "MISSING", "issues": [issue]})
            issues.append(issue)
            continue
        department_issues = _check_department_result(department, result)
        checks.append({
            "department": department,
            "status": "PASS" if not department_issues else "REVIEW_REQUIRED",
            "issues": department_issues,
        })
        issues.extend(department_issues)

    if "media" in expected and "audit" not in expected:
        issues.append("media: independent Audit department was not included in the workflow")

    return {
        "status": "PASS" if not issues else "REVIEW_REQUIRED",
        "department_checks": checks,
        "issues": issues,
        "content_alignment_status": "HUMAN_REVIEW_REQUIRED",
        "human_review_required": True,
        "limitations": [
            "This audit checks orchestration, required quality gates, output presence and safety flags.",
            "It does not prove factual accuracy or semantic completion of every CEO requirement.",
            "Human review remains mandatory before publication, submission, transactions, implementation or deployment.",
        ],
    }
