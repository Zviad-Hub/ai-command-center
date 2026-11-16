
from task_manager import submit_task
from config import APP_NAME, APP_VERSION, DEPARTMENTS


def show_header():
    print("=" * 60)
    print(f"  {APP_NAME} v{APP_VERSION}")
    print("  AI ORGANIZATION CONTROL CENTER")
    print("=" * 60)

    print("\nCEO: SYSTEM OWNER")
    print("AI DIRECTOR: ONLINE")

    print("\nDEPARTMENT MANAGERS:")

    for department in DEPARTMENTS:
        print(f"  [READY] {department.upper()} MANAGER")

    print("\nSECURITY PROTOCOL:")
    print("  [ON] Written authorization required")
    print("  [ON] CEO approval required")
    print("  [ON] Unauthorized pentesting blocked")

    print("\n" + "=" * 60)


def start():
    show_header()

    print("\nWelcome, CEO!")
    print("Enter your command below.")
    print("Type 'exit' to stop the system.")

    while True:
        try:
            task = input("\nCEO > ").strip()

            if task.lower() in ["exit", "quit", "გასვლა"]:
                print("\nAI COMMAND CENTER STOPPED.")
                break

            if not task:
                print("Please enter a task.")
                continue

            print("\n[AI DIRECTOR] Analyzing your command...")

            result = submit_task(task)

            print("\n" + "=" * 60)
            print("TASK SUMMARY")
            print("=" * 60)

            print("TASK ID:", result["id"])
            print("TASK:", result["task"])
            print("DEPARTMENTS:", ", ".join(result["departments"]))

            print("\nMANAGER RESULTS:")

            for item in result["results"]:
                print(
                    f"\n{item['department'].upper()}: "
                    f"{item['status']}"
                )
                print(item["message"])

            print("\nTASK REGISTERED SUCCESSFULLY.")

        except KeyboardInterrupt:
            print("\nSystem interrupted.")
            break

        except Exception as error:
            print("\nSYSTEM ERROR:", str(error))


if __name__ == "__main__":
    start()
