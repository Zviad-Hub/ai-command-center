import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from director import route_task
from managers import get_manager


TASKS_FILE = Path(
    os.getenv(
        "AI_COMMAND_CENTER_TASKS_FILE",
        Path(__file__).resolve().with_name("tasks.json"),
    )
)

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
    """Load task history without silently discarding a damaged history file."""
    path = Path(TASKS_FILE)

    if not path.exists():
        return []

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            "Task history contains invalid JSON and was left untouched. "
            "Restore or repair the history file before submitting another task."
        ) from error
    except OSError as error:
        raise RuntimeError(
            f"Task history could not be read from {path}. "
            "Check file permissions and available disk space."
        ) from error

    if not isinstance(data, list):
        raise RuntimeError(
            "Task history has an invalid format: the root JSON value must be a list. "
            "The existing file was left untouched."
        )

    return data


def save_tasks(tasks):
    """Atomically replace task history so an interrupted write cannot truncate it."""
    if not isinstance(tasks, list):
        raise ValueError("Task history must be a list.")

    path = Path(TASKS_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(path.parent),
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as file:
            temporary_path = Path(file.name)
            json.dump(tasks, file, ensure_ascii=False, indent=4)
            file.flush()
            os.fsync(file.fileno())

        os.replace(temporary_path, path)
        temporary_path = None
    except (OSError, TypeError, ValueError) as error:
        raise RuntimeError(
            f"Task history could not be saved safely to {path}. "
            "The previous history file was not replaced."
        ) from error
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass


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

        except Exception:
            # Avoid copying provider exceptions or request details into the
            # persistent task log; diagnostics belong in controlled logs.
            result = {
                "department": department,
                "status": "ERROR",
                "message": "Department execution failed. Check the application logs for details.",
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
