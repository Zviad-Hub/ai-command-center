
class DepartmentManager:

    def __init__(self, department):
        self.department = department

    def receive_task(self, task, context=None):

        context = context or {}

        print("\n" + "=" * 45)
        print(f"{self.department.upper()} MANAGER")
        print("=" * 45)

        print("RECEIVED MISSION:", task)

        # PENTESTER SECURITY GATE
        if self.department == "pentester":
            return {
                "department": "pentester",
                "status": "BLOCKED",
                "message": (
                    "შეღწევადობის ტესტირება დაბლოკილია. "
                    "საჭიროა წერილობითი თანხმობა "
                    "და CEO-ს ცალკე ნებართვა."
                )
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
                    "message": str(error)
                }

        # AUDIT DEPARTMENT
        if self.department == "audit":
            try:
                from audit_agents import run_audit

                previous_results = context.get(
                    "previous_results", []
                )

                media_result = next(
                    (
                        result for result in previous_results
                        if result.get("department") == "media"
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

        # OTHER DEPARTMENTS
        return {
            "department": self.department,
            "status": "RECEIVED",
            "message": (
                "დავალება მიღებულია. "
                "სპეციალიზებული აგენტები შემდეგ ეტაპზე დაემატება."
            )
        }


def get_manager(department):
    return DepartmentManager(department)
