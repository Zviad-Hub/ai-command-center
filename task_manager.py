import json
import os
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from director import route_task
from managers import get_manager


def _default_tasks_file():
    """Return an OS-appropriate private application-data path."""
    override = os.getenv("AI_COMMAND_CENTER_TASKS_FILE", "").strip()
    if override:
        return Path(os.path.expandvars(os.path.expanduser(override)))

    if sys.platform == "win32":
        base = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA")
        if base:
            data_dir = Path(base)
        else:
            data_dir = Path.home() / "AppData" / "Local"
        return data_dir / "AI Command Center" / "tasks.json"

    if sys.platform == "darwin":
        return (
            Path.home()
            / "Library"
            / "Application Support"
            / "AI Command Center"
            / "tasks.json"
        )

    state_home = os.getenv("XDG_STATE_HOME")
    data_dir = Path(state_home) if state_home else Path.home() / ".local" / "state"
    return data_dir / "ai-command-center" / "tasks.json"


TASKS_FILE = _default_tasks_file()

# Compatibility path for users upgrading from older versions that stored
# task history beside task_manager.py. The old file is copied, never deleted.
LEGACY_TASKS_FILE = Path(__file__).resolve().with_name("tasks.json")

VALID_DEPARTMENTS = [
    "media",
    "tenders",
    "finance",
    "business",
    "pentester",
    "technical",
    "audit"
]


def _read_tasks_file(path):
    try:
        with Path(path).open("r", encoding="utf-8") as file:
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


def load_tasks():
    """Load private task history, migrating a legacy local file when present."""
    path = Path(TASKS_FILE)

    if path.exists():
        return _read_tasks_file(path)

    legacy_path = Path(LEGACY_TASKS_FILE)
    if legacy_path != path and legacy_path.exists():
        legacy_tasks = _read_tasks_file(legacy_path)
        save_tasks(legacy_tasks)
        return legacy_tasks

    return []


def save_tasks(tasks):
    """Atomically save task history in the private application-data directory."""
    if not isinstance(tasks, list):
        raise ValueError("Task history must be a list.")

    path = Path(TASKS_FILE)
    temporary_path = None

    try:
        path.parent.mkdir(parents=True, exist_ok=True)

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
            # Avoid persisting raw provider exceptions or request details.
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
