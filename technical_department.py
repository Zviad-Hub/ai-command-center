
from technical_manager import run_technical_manager
from technical_agents import run_specialist



def _build_final_report(task, plan, specialist_results, context_data, status):
    """Build a transparent department-level report from recorded outputs only."""
    lines = [
        "TECHNICAL DEPARTMENT — FINAL REPORT",
        "",
        f"STATUS: {status}",
        f"TASK: {task}",
        "",
        "EXECUTIVE SUMMARY:",
        str(plan.get("task_understanding") or "The task was routed for technical planning and specialist analysis."),
        "",
        "MANAGER PLAN:",
    ]

    for step in plan.get("execution_plan", []):
        lines.append(f"- {step}")

    lines.extend(["", "TESTING STRATEGY (PROPOSED; NOT EXECUTED):"])
    for step in plan.get("testing_strategy", []):
        lines.append(f"- {step}")

    lines.extend(["", "SPECIALIST FINDINGS:"])
    if not specialist_results:
        lines.append("- No specialist analysis was completed.")
    for item in specialist_results:
        name = item.get("specialist_name") or item.get("specialist") or "Unspecified specialist"
        lines.extend([
            "",
            f"{name} — {item.get('status', 'UNKNOWN')}:",
            str(item.get("report") or item.get("error") or "No written findings were returned.")
        ])

    context_text = "\n".join(
        f"{key}: {value}" for key, value in context_data.items()
    ).lower()
    missing_markers = ("not provided", "not supplied", "missing", "unavailable")
    missing_items = [
        str(key) for key, value in context_data.items()
        if any(marker in str(value).lower() for marker in missing_markers)
    ]

    lines.extend([
        "",
        "EVIDENCE LIMITATIONS:",
        "- Repository files were not independently fetched or opened by this workflow; specialists can analyze only source material included in the supplied task or context.",
        "- Repository state, file paths, and test outcomes are not independently verified unless explicit evidence is included in the supplied material.",
    ])
    if missing_items:
        lines.append("- Missing or unavailable inputs: " + ", ".join(missing_items) + ".")
    if not context_text:
        lines.append("- No additional technical context was supplied.")

    lines.extend([
        "",
        "EXECUTION AND APPROVAL:",
        "- No code was modified.",
        "- No tests were executed; the testing strategy above is a proposal only.",
        "- No deployment or external system action was performed.",
        "- CEO approval is required before implementation, execution, or deployment.",
        "",
        "RECOMMENDED NEXT STEP:",
        "Provide repository/source files and relevant logs, then approve a scoped review and test plan before implementation."
    ])
    return "\n".join(lines)


def run_technical_department(task, context=None):

    task = str(task or "").strip()

    if not task:
        return {
            "department": "technical",
            "status": "REJECTED",
            "message": "Technical task is empty.",
            "requires_ceo_approval": False,
            "execution_performed": False
        }

    # Normalize context.
    if isinstance(context, dict):
        context_data = context
    elif context:
        context_data = {"additional_context": str(context)}
    else:
        context_data = {}

    context_text = "\n".join(
        f"{key}: {value}"
        for key, value in context_data.items()
    )

    # STEP 1: Technical Manager creates the plan.
    plan = run_technical_manager(task)

    if plan.get("status") not in ("PLANNED", "PLAN_CREATED"):
        return {
            "department": "technical",
            "status": "REVIEW_REQUIRED",
            "manager_plan": plan,
            "specialist_results": [],
            "report": _build_final_report(task, plan, [], context_data, "REVIEW_REQUIRED"),
            "execution_performed": False,
            "code_modified": False,
            "tests_executed": False,
            "requires_ceo_approval": True,
            "execution_authorized": False,
            "final_decision": "CEO_APPROVAL_REQUIRED"
        }

    selected_specialists = plan.get(
        "selected_specialists", []
    )

    specialist_results = []

    # STEP 2: Specialists perform their assigned analysis.
    for assignment in selected_specialists:

        if isinstance(assignment, dict):
            specialist_id = (
                assignment.get("id")
                or assignment.get("specialist")
                or ""
            )

            specialist_name = assignment.get(
                "name",
                specialist_id
            )

            mission = assignment.get("mission", "")

        else:
            specialist_id = str(assignment or "").strip()
            specialist_name = specialist_id
            mission = task

        if not specialist_id or not mission:
            specialist_results.append({
                "specialist": specialist_id,
                "status": "ERROR",
                "error": "Invalid specialist assignment.",
                "execution_performed": False
            })
            continue

        result = run_specialist(
            specialist={
                "id": specialist_id,
                "name": specialist_name,
                "mission": mission
            },
            mission=mission,
            context=context_text
        )

        specialist_results.append(result)

    # STEP 3: Evaluate specialist results.
    successful = [
        item for item in specialist_results
        if item.get("status") == "COMPLETED"
    ]

    failed = [
        item for item in specialist_results
        if item.get("status") != "COMPLETED"
    ]

    if not specialist_results:
        status = "REVIEW_REQUIRED"
    elif failed and successful:
        status = "PARTIALLY_COMPLETED"
    elif failed:
        status = "REVIEW_REQUIRED"
    else:
        status = "COMPLETED"

    # STEP 4: Final department report.
    final_report = _build_final_report(
        task, plan, specialist_results, context_data, status
    )
    return {
        "department": "technical",
        "status": status,
        "task": task,
        "manager_plan": plan,
        "specialist_results": specialist_results,
        "report": final_report,
        "summary": {
            "selected_specialists": len(selected_specialists),
            "completed_specialists": len(successful),
            "failed_specialists": len(failed)
        },
        "execution_performed": False,
        "code_modified": False,
        "tests_executed": False,
        "requires_ceo_approval": True,
        "execution_authorized": False,
        "final_decision": "CEO_APPROVAL_REQUIRED"
    }
