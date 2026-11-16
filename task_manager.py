
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from director import create_plan
from managers import get_manager

TASKS_FILE = Path("tasks.json")


def save_task(task_data):
    tasks = []

    if TASKS_FILE.exists():
        try:
            tasks = json.loads(TASKS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            tasks = []

    tasks.append(task_data)

    TASKS_FILE.write_text(
        json.dumps(tasks, ensure_ascii=False, indent=4),
        encoding="utf-8"
    )


def submit_task(task):
    task_id = str(uuid.uuid4())[:8]

    print("\nAI DIRECTOR: Analyzing task...")

    departments = create_plan(task)
    results = []

    for department in departments:
        manager = get_manager(department)
        result = manager.receive_task(task)
        results.append(result)

    task_data = {
        "id": task_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": task,
        "departments": departments,
        "results": results
    }

    save_task(task_data)

    print("\nTASK SAVED")
    print("TASK ID:", task_id)

    return task_data


if __name__ == "__main__":
    print("AI COMMAND CENTER")
    print("Enter your task below.")

    while True:
        task = input("\nCEO > ").strip()

        if task.lower() in ["exit", "quit", "გასვლა"]:
            break

        if not task:
            continue

        submit_task(task)
