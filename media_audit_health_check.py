"""Safe, non-production diagnostics for Media and Audit.

A SYSTEM HEALTH CHECK must inspect department wiring without pretending to
create a video, requiring live research, or auditing a nonexistent artifact.
This module deliberately does not call AI providers or external services.
"""
from datetime import datetime, timezone
import importlib
import uuid


HEALTH_CHECK_MARKERS = (
    "system health check",
    "health check",
    "system diagnostic",
    "diagnostic all departments",
)


def is_system_health_check(task):
    text = str(task or "").casefold()
    return any(marker in text for marker in HEALTH_CHECK_MARKERS)


def _check_module(module_name, required_callables):
    try:
        module = importlib.import_module(module_name)
    except Exception:
        return {
            "status": "ERROR",
            "available": False,
            "callables": {name: False for name in required_callables},
            "issue_code": "MODULE_IMPORT_FAILED",
        }

    callables = {
        name: callable(getattr(module, name, None))
        for name in required_callables
    }
    passed = all(callables.values())
    return {
        "status": "CONFIGURATION_CHECKED" if passed else "REVIEW_REQUIRED",
        "available": passed,
        "callables": callables,
        "issue_code": None if passed else "REQUIRED_ENTRYPOINT_MISSING",
    }


def run_media_audit_health_check(task):
    """Check Media/Audit entry points; do not run production workflows."""
    media = _check_module(
        "media_agents",
        ("run_media_department", "validate_script", "extract_narration"),
    )
    audit = _check_module(
        "audit_agents",
        ("run_audit", "compliance_auditor", "evidence_auditor", "integrity_auditor"),
    )

    results = [
        {
            "department": "media",
            "status": media["status"],
            "diagnostic_scope": "MODULE_AND_ENTRYPOINTS_ONLY",
            "checks": media["callables"],
            "issue_code": media["issue_code"],
            "production_pipeline_executed": False,
            "publication_approved": False,
        },
        {
            "department": "audit",
            "status": audit["status"],
            "diagnostic_scope": "MODULE_AND_ENTRYPOINTS_ONLY",
            "checks": audit["callables"],
            "issue_code": audit["issue_code"],
            "production_pipeline_executed": False,
            "publication_approved": False,
        },
    ]

    has_errors = any(item["status"] != "CONFIGURATION_CHECKED" for item in results)
    return {
        "id": str(uuid.uuid4())[:8],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": str(task or ""),
        "departments": ["media", "audit"],
        "results": results,
        "routing": {"routing_method": "BUILT_IN_HEALTH_DIAGNOSTIC"},
        "organization_audit": {
            "status": "REVIEW_REQUIRED" if has_errors else "CONFIGURATION_CHECKED",
            "content_alignment_status": "NOT_APPLICABLE",
            "department_checks": [
                {
                    "department": item["department"],
                    "status": item["status"],
                    "issues": [item["issue_code"]] if item["issue_code"] else [],
                }
                for item in results
            ],
        },
        "semantic_audit": {
            "status": "NOT_RUN",
            "task_coverage": "NOT_APPLICABLE",
        },
        "overall_status": "REVIEW_REQUIRED" if has_errors else "DIAGNOSTIC_ONLY",
        "human_review_required": True,
        "diagnostic_note": (
            "Configuration checks only. Specialist execution, live research, "
            "content quality, factual accuracy, and publication readiness were not tested."
        ),
    }
