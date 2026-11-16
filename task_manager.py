
import json
import os
import uuid
from datetime import datetime, timezone

from director import route_task
from managers import get_manager


def save_task(record):

    file_path = "tasks.json"

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            tasks = json.load(file)

        if not isinstance(tasks, list):
            tasks = []

    except (FileNotFoundError, json.JSONDecodeError):
        tasks = []

    tasks.insert(0, record)

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(
            tasks,
            file,
            ensure_ascii=False,
            indent=4
        )


def submit_task(ceo_task):

    task_id = str(uuid.uuid4())[:8]

    print("\n" + "=" * 60)
    print("AI COMMAND CENTER")
    print("=" * 60)

    print("\nCEO ORIGINAL TASK:")
    print(ceo_task)

    # 1. DIRECTOR ANALYSIS
    print("\n[DIRECTOR] Analyzing CEO request...")

    try:
        routing = route_task(ceo_task)

    except Exception as error:
        routing = {
            "analysis": f"Director error: {error}",
            "departments": ["media"],
            "requires_ceo_approval": True
        }

    departments = routing.get("departments", [])

    if not isinstance(departments, list):
        departments = []

    valid_departments = {
        "media",
        "tenders",
        "finance",
        "business",
        "pentester",
        "technical",
        "audit"
    }

    departments = [
        department
        for department in departments
        if department in valid_departments
    ]

    # CEO's original request is the authoritative task.
    # Director may select departments but cannot replace the topic.

    if not departments:
        departments = ["technical"]

    print("\nDIRECTOR ANALYSIS:")
    print(routing.get("analysis", ""))

    print("\nSELECTED DEPARTMENTS:")
    print(departments)

    # 2. DEPARTMENT EXECUTION
    results = []

    for department in departments:

        print("\n" + "-" * 50)
        print(f"[{department.upper()}] Starting...")
        print("-" * 50)

        manager = get_manager(department)

        try:
            result = manager.receive_task(
            ceo_task,
            context={
                "previous_results": results
            }
        )

        except Exception as error:
            result = {
                "department": department,
                "status": "ERROR",
                "message": str(error)
            }

        results.append(result)

        print("\nDEPARTMENT RESULT:")
        print(json.dumps(
            result,
            ensure_ascii=False,
            indent=2
        )[:5000])

    # 3. SAVE COMPLETE TASK HISTORY
    record = {
        "id": task_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": ceo_task,
        "analysis": routing.get("analysis", ""),
        "departments": departments,
        "requires_ceo_approval": routing.get(
            "requires_ceo_approval",
            True
        ),
        "results": results
    }

    save_task(record)

    print("\n" + "=" * 60)
    print("TASK COMPLETED")
    print("TASK ID:", task_id)
    print("=" * 60)

    return record
