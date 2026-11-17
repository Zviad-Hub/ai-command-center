
from technical_manager import run_technical_manager
from technical_agents import run_specialist


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
