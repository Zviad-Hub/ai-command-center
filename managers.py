class DepartmentManager:

    def __init__(self, department):
        self.department = department

    def receive_task(self, task, context=None):

        context = context if isinstance(context, dict) else {}

        print("\n" + "=" * 45)
        print(f"{self.department.upper()} MANAGER")
        print("=" * 45)
        print("RECEIVED MISSION:", task)

        # PENTESTER SECURITY GATE
        # Active testing remains disabled until a separate,
        # verifiable authorization workflow is implemented.
        if self.department == "pentester":
            return {
                "department": "pentester",
                "status": "BLOCKED",
                "message": (
                    "შეღწევადობის აქტიური ტესტირება დაბლოკილია. "
                    "საჭიროა წერილობითი ავტორიზაცია, ზუსტი scope "
                    "და CEO-ს ცალკე ნებართვა."
                ),
                "execution_authorized": False,
                "execution_performed": False,
                "requires_ceo_approval": True
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
                    "message": str(error),
                    "execution_performed": False
                }

        # AUDIT DEPARTMENT
        if self.department == "audit":
            try:
                from audit_agents import run_audit

                previous_results = context.get("previous_results", [])
                media_result = next(
                    (
                        result for result in previous_results
                        if isinstance(result, dict)
                        and result.get("department") == "media"
                    ),
                    None
                )

                if not media_result:
                    return {
                        "department": "audit",
                        "status": "REVIEW_REQUIRED",
                        "message": (
                            "აუდიტმა მედიის შედეგი ვერ მიიღო. "
                            "დამოუკიდებელი შემოწმება ვერ დასრულდა."
                        ),
                        "publication_approved": False
                    }

                return run_audit(task, media_result)

            except Exception as error:
                return {
                    "department": "audit",
                    "status": "ERROR",
                    "message": str(error),
                    "publication_approved": False
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
                    "message": str(error),
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
                    "error": str(error),
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
