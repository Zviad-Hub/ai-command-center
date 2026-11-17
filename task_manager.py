import json
from copy import deepcopy
import os
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from director import route_task
from managers import get_manager
from organization_quality import audit_organization_task
from organization_semantic_auditor import run_semantic_alignment_audit


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
            # Managers receive an isolated snapshot: a later department must
            # never be able to mutate an earlier department's recorded result.
            "previous_results": deepcopy(results)
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

    # STEP 3: Independently audit the complete department handoff.
    organization_audit = audit_organization_task(
        ceo_task, departments, results
    )

    semantic_audit_enabled = os.getenv(
        "AI_ORGANIZATION_SEMANTIC_AUDIT", ""
    ).strip().casefold() in {"1", "true", "yes", "enabled"}
    if semantic_audit_enabled:
        semantic_audit = run_semantic_alignment_audit(
            ceo_task, departments, results
        )
    else:
        semantic_audit = {
            "status": "NOT_RUN",
            "reason": "OPT_IN_DISABLED",
            "summary": "Optional AI semantic audit is disabled; human task-alignment review remains required.",
            "human_review_required": True,
        }

    semantic_status = semantic_audit.get("status")
    if semantic_status == "PASS":
        organization_audit["content_alignment_status"] = "AI_REVIEW_PASS_HUMAN_REVIEW_REQUIRED"
    elif semantic_status == "NEEDS_REVISION":
        organization_audit["content_alignment_status"] = "AI_REVIEW_NEEDS_REVISION"
    elif semantic_status == "UNAVAILABLE":
        organization_audit["content_alignment_status"] = "AI_REVIEW_UNAVAILABLE"
    else:
        organization_audit["content_alignment_status"] = "HUMAN_REVIEW_REQUIRED"

    semantic_gate_passed = semantic_status in {"PASS", "NOT_RUN"}
    overall_status = (
        "READY_FOR_HUMAN_REVIEW"
        if organization_audit["status"] == "PASS" and semantic_gate_passed
        else "REVIEW_REQUIRED"
    )

    # STEP 4: Save task record. Department outputs remain unchanged; both
    # organization audits are read-only and never authorize consequential actions.
    record = {
        "id": str(uuid.uuid4())[:8],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": ceo_task,
        "departments": departments,
        "routing": routing,
        "results": results,
        "organization_audit": organization_audit,
        "semantic_audit": semantic_audit,
        "overall_status": overall_status,
        "human_review_required": True,
    }

    tasks = load_tasks()
    tasks.append(record)
    save_tasks(tasks)

    return record



def build_public_task_summary(record):
    """Return gate statuses only; never expose task text, reports, or issue details."""
    if not isinstance(record, dict):
        return {
            "run_status": "FAILED",
            "error_code": "INVALID_TASK_RECORD",
            "human_review_required": True,
        }

    department_results = []
    raw_results = record.get("results", [])
    for item in raw_results if isinstance(raw_results, list) else []:
        if not isinstance(item, dict):
            continue

        row = {
            "department": str(item.get("department") or "unknown"),
            "status": str(item.get("status") or "UNKNOWN"),
        }

        specialist_reports = item.get("specialist_reports")
        specialist_results = item.get("specialist_results")
        specialists = item.get("specialists")
        auditors = item.get("auditors")
        if isinstance(specialist_reports, dict):
            row["specialist_count"] = len(specialist_reports)
        elif isinstance(specialist_results, list):
            row["specialist_count"] = len(specialist_results)
        elif isinstance(specialists, list):
            row["specialist_count"] = len(specialists)
        if isinstance(auditors, list):
            row["auditor_count"] = len(auditors)

        specialist_validation = item.get("specialist_quality_validation")
        if isinstance(specialist_validation, dict):
            row["specialist_validation_status"] = str(
                specialist_validation.get("status") or "UNKNOWN"
            )

        evidence_validation = item.get("evidence_validation")
        if isinstance(evidence_validation, dict):
            row["evidence_validation_status"] = str(
                evidence_validation.get("status") or "UNKNOWN"
            )

        for field in (
            "quality_review_passed",
            "publication_approved",
            "requires_ceo_approval",
            "execution_authorized",
            "execution_performed",
            "active_testing_available",
        ):
            value = item.get(field)
            if isinstance(value, bool):
                row[field] = value

        department_results.append(row)

    organization = record.get("organization_audit")
    if not isinstance(organization, dict):
        organization = {}
    organization_checks = []
    raw_checks = organization.get("department_checks", [])
    for check in raw_checks if isinstance(raw_checks, list) else []:
        if not isinstance(check, dict):
            continue
        issues = check.get("issues")
        organization_checks.append({
            "department": str(check.get("department") or "unknown"),
            "status": str(check.get("status") or "UNKNOWN"),
            "issue_count": len(issues) if isinstance(issues, list) else 0,
        })

    semantic = record.get("semantic_audit")
    if not isinstance(semantic, dict):
        semantic = {}

    return {
        "run_status": "FINISHED",
        "task_id": str(record.get("id") or ""),
        "overall_status": str(record.get("overall_status") or "UNKNOWN"),
        "departments": [
            str(value) for value in record.get("departments", [])
        ] if isinstance(record.get("departments"), list) else [],
        "department_results": department_results,
        "organization_audit": {
            "status": str(organization.get("status") or "UNKNOWN"),
            "content_alignment_status": str(
                organization.get("content_alignment_status") or "UNKNOWN"
            ),
            "department_checks": organization_checks,
        },
        "semantic_audit": {
            "status": str(semantic.get("status") or "UNKNOWN"),
            "task_coverage": str(semantic.get("task_coverage") or "UNKNOWN"),
        },
        "human_review_required": record.get("human_review_required") is True,
    }
