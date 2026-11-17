import json
import os
import uuid
from datetime import datetime, timezone

from director import route_task
from managers import get_manager


TASKS_FILE = "tasks.json"

VALID_DEPARTMENTS = [
    "media",
    "tenders",
    "finance",
    "business",
    "pentester",
    "technical",
    "audit"
]


def load_tasks():
    if not os.path.exists(TASKS_FILE):
        return []

    try:
        with open(TASKS_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        return data if isinstance(data, list) else []

    except (json.JSONDecodeError, OSError):
        return []


def save_tasks(tasks):
    with open(TASKS_FILE, "w", encoding="utf-8") as file:
        json.dump(
            tasks,
            file,
            ensure_ascii=False,
            indent=4
        )


def submit_task(ceo_task):

    ceo_task = str(ceo_task or "").strip()

    if not ceo_task:
        raise ValueError("CEO task cannot be empty.")

    # STEP 1: Director analyzes and routes the task.
    routing = route_task(ceo_task)

    if not isinstance(routing, dict):
        raise ValueError("Director returned an invalid routing plan.")

    departments = routing.get("departments", [])

    if not isinstance(departments, list):
        departments = []

    departments = list(dict.fromkeys(
        department
        for department in departments
        if department in VALID_DEPARTMENTS
    ))

    if not departments:
        departments = ["technical"]

    missions = routing.get("missions", {})
    if not isinstance(missions, dict):
        missions = {}

    # STEP 2: Each manager receives its own mission, not a generic copy
    # of the CEO task. The original request remains available as context.
    results = []

    for department in departments:

        mission = missions.get(department)
        if not isinstance(mission, str) or not mission.strip():
            mission = ceo_task

        context = {
            "original_task": ceo_task,
            "department_mission": mission,
            "previous_results": list(results)
        }

        try:
            manager = get_manager(department)

            result = manager.receive_task(
                mission,
                context=context
            )

            if not isinstance(result, dict):
                result = {
                    "department": department,
                    "status": "ERROR",
                    "message": "Department returned an invalid result.",
                    "execution_performed": False,
                    "requires_ceo_approval": True
                }

        except Exception as error:
            result = {
                "department": department,
                "status": "ERROR",
                "message": str(error),
                "execution_performed": False,
                "requires_ceo_approval": True
            }

        results.append(result)

    # STEP 3: Save task record.
    record = {
        "id": str(uuid.uuid4())[:8],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": ceo_task,
        "departments": departments,
        "routing": routing,
        "results": results
    }

    tasks = load_tasks()
    tasks.append(record)
    save_tasks(tasks)

    return record
