class DepartmentManager:

    def __init__(self, department):
        self.department = department

    def receive_task(self, task, context=None):

        context = context if isinstance(context, dict) else {}

        print("\n" + "=" * 45)
        print(f"{self.department.upper()} MANAGER")
        print("=" * 45)
        print("MISSION RECEIVED (details withheld).")

        # PENTESTER DEPARTMENT — DEFENSIVE, PASSIVE-ONLY WORKFLOW; NO NETWORK OPERATIONS
        if self.department == "pentester":
            try:
                from pentester_agents import run_pentester_department
                return run_pentester_department(task, context=context)
            except Exception as error:
                return {
                    "department": "pentester",
                    "status": "REVIEW_REQUIRED",
                    "message": "Pentester workflow failed safely.",
                    "error": "WORKFLOW_FAILED",
                    "report": "",
                    "requires_ceo_approval": True,
                    "execution_authorized": False,
                    "execution_performed": False,
                    "active_testing_available": False,
                    "external_network_activity": False
                }

        # MEDIA DEPARTMENT
        if self.department == "media":
            try:
                from media_agents import run_media_department
                return run_media_department(task)
            except Exception as error:
                return {
                    "department": "media",
                    "status": "ERROR",
                    "message": "Department workflow failed safely; internal error details were withheld.",
                    "execution_performed": False
                }

        # AUDIT DEPARTMENT
        if self.department == "audit":
            try:
                from audit_agents import run_audit, run_general_audit

                previous_results = context.get("previous_results", [])
                if not isinstance(previous_results, list):
                    previous_results = []

                media_result = next(
                    (
                        result for result in previous_results
                        if isinstance(result, dict)
                        and result.get("department") == "media"
                    ),
                    None
                )

                if media_result:
                    # Preserve the specialized Media compliance/evidence audit.
                    media_audit = run_audit(task, media_result)
                    other_results = [
                        result for result in previous_results
                        if isinstance(result, dict)
                        and result.get("department") not in {"media", "audit"}
                    ]
                    if other_results:
                        handoff_audit = run_general_audit(task, other_results)
                        media_audit["auditors"].extend(handoff_audit.get("auditors", []))
                        media_audit["summary"]["total_checks"] += handoff_audit["summary"]["total_checks"]
                        media_audit["summary"]["passed_checks"] += handoff_audit["summary"]["passed_checks"]
                        media_audit["summary"]["failed_checks"] += handoff_audit["summary"]["failed_checks"]
                        media_audit["failed_checks"].extend(handoff_audit.get("failed_checks", []))
                        if handoff_audit.get("status") != "PASSED_WITH_LIMITATIONS":
                            media_audit["status"] = "REVIEW_REQUIRED"
                            media_audit["message"] = "აუდიტმა მედიის ან სხვა დეპარტამენტის შემოწმებაში შეუსაბამობა აღმოაჩინა."
                    return media_audit

                return run_general_audit(task, previous_results)

            except Exception:
                return {
                    "department": "audit",
                    "status": "ERROR",
                    "message": "Department workflow failed safely; internal error details were withheld.",
                    "publication_approved": False,
                    "final_decision": "CEO_APPROVAL_REQUIRED",
                    "requires_ceo_approval": True,
                    "execution_authorized": False,
                    "execution_performed": False
                }

        # TECHNICAL DEPARTMENT
        if self.department == "technical":
            try:
                from technical_department import run_technical_department

                return run_technical_department(
                    task,
                    context={
                        "original_task": context.get("original_task", task),
                        "department_mission": context.get("department_mission", task),
                        "previous_results": context.get("previous_results", [])
                    }
                )

            except Exception as error:
                return {
                    "department": "technical",
                    "status": "ERROR",
                    "message": "Department workflow failed safely; internal error details were withheld.",
                    "execution_performed": False,
                    "code_modified": False,
                    "tests_executed": False,
                    "requires_ceo_approval": True,
                    "execution_authorized": False
                }

        # FINANCE, BUSINESS AND TENDERS
        if self.department in ("finance", "business", "tenders"):
            try:
                from department_agents import run_department_workflow

                return run_department_workflow(
                    self.department,
                    task,
                    context=context
                )

            except Exception as error:
                return {
                    "department": self.department,
                    "status": "REVIEW_REQUIRED",
                    "message": "Specialized department workflow failed.",
                    "error": "WORKFLOW_FAILED",
                    "report": "",
                    "advisory_only": True,
                    "requires_ceo_approval": True,
                    "execution_authorized": False,
                    "execution_performed": False
                }

        return {
            "department": self.department,
            "status": "NOT_IMPLEMENTED",
            "message": "No workflow is implemented for this department.",
            "requires_ceo_approval": True,
            "execution_performed": False
        }


def get_manager(department):
    return DepartmentManager(department)
