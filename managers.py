
class DepartmentManager:

    def __init__(self, department):
        self.department = department

    def receive_task(self, task):

        print("\n" + "=" * 45)
        print(f"{self.department.upper()} MANAGER")
        print("=" * 45)

        print("RECEIVED MISSION:", task)

        # SECURITY GATE: Pentester
        if self.department == "pentester":
            return {
                "department": "pentester",
                "task": task,
                "status": "BLOCKED",
                "message": (
                    "შეღწევადობის ტესტირება დაბლოკილია. "
                    "საჭიროა კომპანიის წერილობითი თანხმობა "
                    "და CEO-ს ცალკე ნებართვა. ტესტირება არ დაწყებულა."
                )
            }

        # MEDIA DEPARTMENT
        if self.department == "media":
            try:
                from media_agents import run_media_department

                result = run_media_department(task)

                return result

            except Exception as error:
                return {
                    "department": "media",
                    "task": task,
                    "status": "ERROR",
                    "message": f"Media department error: {error}"
                }

        # OTHER DEPARTMENTS
        return {
            "department": self.department,
            "task": task,
            "status": "RECEIVED",
            "message": (
                "დავალება მიღებულია. "
                "სპეციალიზებული აგენტები შემდეგ ეტაპზე დაემატება."
            )
        }


def get_manager(department):
    return DepartmentManager(department)
