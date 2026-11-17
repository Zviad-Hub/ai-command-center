import json
import re
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

    # Health checks use a non-production diagnostic path. They must not
    # trigger Media research/script generation or Audit of a nonexistent asset.
    from media_audit_health_check import (
        is_system_health_check,
        run_media_audit_health_check,
    )
    if is_system_health_check(ceo_task):
        record = run_media_audit_health_check(ceo_task)
        tasks = load_tasks()
        tasks.append(record)
        save_tasks(tasks)
        return record

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

    # STEP 2: Execute Audit last so it can independently review every
    # completed department result, regardless of whether Media was selected.
    results = []
    execution_order = [item for item in departments if item != "audit"]
    if "audit" in departments:
        execution_order.append("audit")

    # Each manager receives its own mission, not a generic copy of the CEO task.
    # The original request remains available as context.
    for department in execution_order:

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

    # Semantic alignment is a required quality gate by default. It may be
    # explicitly disabled for controlled cost/testing reasons, but NOT_RUN
    # must never be treated as a successful audit.
    semantic_audit_enabled = os.getenv(
        "AI_ORGANIZATION_SEMANTIC_AUDIT", "1"
    ).strip().casefold() not in {"0", "false", "no", "disabled", "off"}
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

    semantic_gate_passed = semantic_status == "PASS"
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

        # Expose safe, structured failure diagnostics without publishing raw
        # provider errors, prompts, source URLs, or generated content.
        failed_stage = item.get("failed_stage")
        if isinstance(failed_stage, str) and failed_stage.strip():
            row["failed_stage"] = failed_stage.strip()[:80]

        error_type = item.get("error_type")
        if isinstance(error_type, str) and error_type.strip():
            row["error_type"] = error_type.strip()[:80]
        error_code = item.get("error_code")
        if isinstance(error_code, str) and error_code.strip():
            row["error_code"] = error_code.strip()[:100]

        research = item.get("research")
        if isinstance(research, dict):
            research_status = research.get("status")
            if isinstance(research_status, str):
                row["research_status"] = research_status.upper()[:40]
            for source_field in ("source_count", "full_page_count", "snippet_count"):
                source_value = research.get(source_field)
                if isinstance(source_value, int) and not isinstance(source_value, bool):
                    row[f"research_{source_field}"] = max(0, source_value)

        failed_checks = item.get("failed_checks")
        if isinstance(failed_checks, list):
            safe_names = []
            safe_auditors = []
            for check in failed_checks:
                if not isinstance(check, dict):
                    continue
                check_name = check.get("check")
                auditor_name = check.get("auditor")
                if isinstance(check_name, str) and check_name.strip():
                    safe_names.append(check_name.strip()[:100])
                if isinstance(auditor_name, str) and auditor_name.strip():
                    safe_auditors.append(auditor_name.strip()[:80])
            if safe_names:
                row["failed_check_names"] = safe_names[:30]
            if safe_auditors:
                row["failed_auditor_names"] = list(dict.fromkeys(safe_auditors))[:10]

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

        # Publish aggregate specialist outcomes and safe error codes only.
        # Never expose specialist reports, raw exception messages, or prompts.
        specialist_failures = item.get("specialist_failures")
        specialist_not_run = item.get("specialist_not_run")
        completed_count = len(specialist_reports) if isinstance(specialist_reports, dict) else 0
        failed_count = 0
        not_run_count = len(specialist_not_run) if isinstance(specialist_not_run, list) else 0
        failure_codes = []

        if isinstance(specialist_results, list):
            for specialist in specialist_results:
                if not isinstance(specialist, dict):
                    continue
                status = str(specialist.get("status") or "").upper()
                if status == "COMPLETED":
                    completed_count += 1
                elif status == "ERROR":
                    failed_count += 1
                    code = specialist.get("error_code")
                    if isinstance(code, str) and re.fullmatch(r"[A-Z0-9_]{1,100}", code.strip().upper()):
                        failure_codes.append(code.strip().upper())
                elif status == "NOT_RUN":
                    not_run_count += 1

        if isinstance(specialist_failures, list):
            failed_count += len(specialist_failures)
            for failure in specialist_failures:
                if not isinstance(failure, dict):
                    continue
                code = failure.get("error_code")
                if isinstance(code, str) and re.fullmatch(r"[A-Z0-9_]{1,100}", code.strip().upper()):
                    failure_codes.append(code.strip().upper())

        has_specialist_diagnostics = (
            isinstance(specialist_reports, dict)
            or isinstance(specialist_results, list)
            or isinstance(specialist_failures, list)
            or isinstance(specialist_not_run, list)
        )
        if has_specialist_diagnostics:
            row["specialist_completed_count"] = completed_count
            row["specialist_failure_count"] = failed_count
            row["specialist_not_run_count"] = not_run_count
            row["specialist_selected_count"] = completed_count + failed_count + not_run_count
            if failure_codes:
                row["specialist_failure_codes"] = list(dict.fromkeys(failure_codes))[:20]

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

        validation = item.get("validation")
        if isinstance(validation, dict):
            script_gates = (
                "word_count_passed",
                "visual_scene_count_passed",
                "timestamps_passed",
                "narration_found",
            )
            row["script_validation"] = {
                field: validation[field]
                for field in script_gates
                if isinstance(validation.get(field), bool)
            }

        audit_summary = item.get("summary")
        if isinstance(audit_summary, dict):
            for field in ("total_checks", "passed_checks", "failed_checks"):
                value = audit_summary.get(field)
                if isinstance(value, int) and not isinstance(value, bool):
                    row[f"audit_{field}"] = value
        final_decision = item.get("final_decision")
        if isinstance(final_decision, str):
            row["final_decision"] = final_decision
        warnings = item.get("warnings")
        if isinstance(warnings, list):
            row["warning_count"] = len(warnings)

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
        issue_list = issues if isinstance(issues, list) else []
        issue_codes = []
        for issue in issue_list:
            value = str(issue).casefold()
            if "specialist quality validation" in value:
                code = "SPECIALIST_QUALITY_GATE_FAILED"
            elif "manager/reviewer quality gate" in value or "independent security review" in value:
                code = "INDEPENDENT_REVIEW_FAILED"
            elif "execution" in value or "unsafe or ambiguous" in value or "active_testing" in value:
                code = "EXECUTION_SAFETY_GATE_FAILED"
            elif "publication_approved" in value:
                code = "PUBLICATION_APPROVAL_FLAG_INVALID"
            elif "written authorization" in value or "human scope review" in value or "passive-only" in value:
                code = "PENTESTER_SCOPE_GATE_FAILED"
            elif "evidence validation" in value:
                code = "EVIDENCE_VALIDATION_FAILED"
            elif "audit:" in value:
                code = "INDEPENDENT_AUDIT_GATE_FAILED"
            elif "missing" in value or "not provided" in value:
                code = "REQUIRED_EVIDENCE_MISSING"
            elif "status" in value:
                code = "DEPARTMENT_STATUS_NOT_ACCEPTED"
            else:
                code = "ORCHESTRATION_INTEGRITY_ISSUE"
            issue_codes.append(code)
        organization_checks.append({
            "department": str(check.get("department") or "unknown"),
            "status": str(check.get("status") or "UNKNOWN"),
            "issue_count": len(issue_list),
            "issue_codes": list(dict.fromkeys(issue_codes)),
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
            "missing_requirement_count": len(semantic.get("missing_requirements", []))
                if isinstance(semantic.get("missing_requirements"), list) else 0,
            "unsupported_claim_count": len(semantic.get("unsupported_claims", []))
                if isinstance(semantic.get("unsupported_claims"), list) else 0,
            "contradiction_count": len(semantic.get("contradictions", []))
                if isinstance(semantic.get("contradictions"), list) else 0,
            "evidence_gap_count": len(semantic.get("evidence_gaps", []))
                if isinstance(semantic.get("evidence_gaps"), list) else 0,
            "error_code": str(semantic.get("error_code") or "")[:100]
                if isinstance(semantic.get("error_code"), str) else "",
        },
        "human_review_required": record.get("human_review_required") is True,
    }
