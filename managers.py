
from director import DEPARTMENT_DESCRIPTIONS


class DepartmentManager:

    def __init__(self, department):
        self.department = department
        self.description = DEPARTMENT_DESCRIPTIONS.get(
            department,
            "General department"
        )

    def receive_task(self, task):
        print("\n" + "=" * 45)
        print(f"{self.department.upper()} MANAGER")
        print("=" * 45)

        print("MISSION:", self.description)
        print("RECEIVED TASK:", task)

        if self.department == "pentester":
            return self.security_check(task)

        return {
            "department": self.department,
            "task": task,
            "status": "WAITING_FOR_AI_AGENT",
            "message": "Task received. AI execution will be connected next."
        }

    def security_check(self, task):
        return {
            "department": "pentester",
            "task": task,
            "status": "BLOCKED",
            "message": (
                "Pentesting is prohibited until written authorization "
                "is uploaded, validated, and CEO approval is granted."
            )
        }


def get_manager(department):
    return DepartmentManager(department)
