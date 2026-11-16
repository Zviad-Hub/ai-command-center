
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from director import route_task
from managers import get_manager

TASKS_FILE = Path("tasks.json")


def load_tasks():
    if not TASKS_FILE.exists():
        return []

    try:
        return json.loads(
            TASKS_FILE.read_text(encoding="utf-8")
        )
    except (json.JSONDecodeError, OSError):
        return []


def save_task(task_data):
    tasks = load_tasks()
    tasks.append(task_data)

    TASKS_FILE.write_text(
        json.dumps(tasks, ensure_ascii=False, indent=4),
        encoding="utf-8"
    )


def submit_task(task):
    task_id = str(uuid.uuid4())[:8]

    print("\n[AI DIRECTOR] Analyzing CEO task...")

    try:
        plan = route_task(task)
    except Exception as error:
        print("[AI DIRECTOR ERROR]", error)

        plan = {
            "analysis": "AI unavailable. Task requires review.",
            "departments": ["technical"],
            "missions": {"technical": task},
            "requires_ceo_approval": True
        }

    departments = plan["departments"]
    results = []

    print("\nDIRECTOR ANALYSIS:")
    print(plan["analysis"])

    for department in departments:
        manager = get_manager(department)

        mission = plan["missions"].get(
            department,
            task
        )

        result = manager.receive_task(mission)

        if department == "pentester":
            result["status"] = "BLOCKED"
            result["message"] = (
                "Written authorization and CEO approval "
                "are required. No testing started."
            )

        results.append(result)

    task_data = {
        "id": task_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": task,
        "analysis": plan["analysis"],
        "departments": departments,
        "requires_ceo_approval": plan["requires_ceo_approval"],
        "results": results
    }

    save_task(task_data)

    print("\nTASK SAVED:", task_id)

    return task_data


if __name__ == "__main__":
    task = input("CEO > ").strip()

    if task:
        submit_task(task)
