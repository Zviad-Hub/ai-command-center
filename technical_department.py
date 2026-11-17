
from technical_manager import run_technical_manager
from technical_agents import run_specialist


def run_technical_department(task, context=None):
    task = str(task or "").strip()
    context = str(context or "").strip()

    if not task:
        return {
            "department": "technical",
            "status": "REJECTED",
            "message": "Technical task is empty.",
            "requires_ceo_approval": False
        }

    # STEP 1: Manager creates the execution plan.
    plan = run_technical_manager(task)

    if plan.get("status") != "PLAN_CREATED":
        return {
            "department": "technical",
            "status": "REVIEW_REQUIRED",
            "manager_plan": plan,
            "specialist_results": [],
            "requires_ceo_approval": True,
            "execution_authorized": False
        }

    selected_specialists = plan.get(
        "selected_specialists", []
    )

    specialist_results = []

    # STEP 2: Specialists perform their assigned analysis.
    # No real code execution or file modification is allowed here.
    for assignment in selected_specialists:
        specialist = assignment.get("specialist", "")
        mission = assignment.get("mission", "")

        if not specialist or not mission:
            continue

        result = run_specialist(
            specialist=specialist,
            mission=mission,
            context=context
        )

        specialist_results.append(result)

    # STEP 3: Evaluate specialist completion.
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
    elif failed:
        status = "PARTIALLY_COMPLETED"
    else:
        status = "COMPLETED"

    # STEP 4: Prepare final department report.
    return {
        "department": "technical",
        "status": status,
        "task": task,
        "manager_plan": plan,
        "specialist_results": specialist_results,
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
