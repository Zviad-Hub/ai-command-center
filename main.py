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


def display_manager_result(item):
    """Print manager output without assuming every department has a message field."""

    department = str(item.get("department", "unknown")).upper()
    status = str(item.get("status", "UNKNOWN"))

    print(f"\n{department}: {status}")

    message = item.get("message")
    if message:
        print(message)

    report = item.get("report")
    if isinstance(report, str) and report.strip():
        print("\\nDEPARTMENT REPORT:\\n")
        print(report.strip())

    summary = item.get("summary")
    if isinstance(summary, dict):
        selected = summary.get("selected_specialists")
        completed = summary.get("completed_specialists")
        failed = summary.get("failed_specialists")

        if any(value is not None for value in (selected, completed, failed)):
            print(
                "Specialists — "
                f"selected: {selected if selected is not None else 'n/a'}, "
                f"completed: {completed if completed is not None else 'n/a'}, "
                f"failed: {failed if failed is not None else 'n/a'}"
            )

    specialist_results = item.get("specialist_results", [])
    if isinstance(specialist_results, list):
        for specialist in specialist_results:
            if not isinstance(specialist, dict):
                continue

            name = specialist.get("name") or specialist.get("specialist") or "Specialist"
            specialist_status = specialist.get("status", "UNKNOWN")
            print(f"  - {name}: {specialist_status}")

            detail = (
                specialist.get("report")
                or specialist.get("message")
                or specialist.get("error")
            )
            if detail:
                print(f"    {detail}")

    if not message and not summary and not specialist_results:
        print("No detailed report was returned by this manager.")


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
                display_manager_result(item)

            print("\nTASK RECORD SAVED.")
            print("Review each department status before approving any next step.")

        except KeyboardInterrupt:
            print("\nSystem interrupted.")
            break

        except Exception as error:
            print("\nSYSTEM ERROR:", str(error))


if __name__ == "__main__":
    start()
