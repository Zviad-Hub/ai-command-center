
class DepartmentManager:

    def __init__(self, department):
        self.department = department

    def receive_task(self, task):

        print("\n" + "=" * 45)
        print(f"{self.department.upper()} MANAGER")
        print("=" * 45)

        print("RECEIVED MISSION:", task)

        if self.department == "pentester":
            return {
                "department": "pentester",
                "task": task,
                "status": "BLOCKED",
                "message": (
                    "Written authorization document, "
                    "document validation and explicit CEO approval "
                    "are required. No testing started."
                )
            }

        return {
            "department": self.department,
            "task": task,
            "status": "RECEIVED",
            "message": (
                "Mission received. Specialist agents "
                "will be connected in the next stage."
            )
        }


def get_manager(department):
    return DepartmentManager(department)
