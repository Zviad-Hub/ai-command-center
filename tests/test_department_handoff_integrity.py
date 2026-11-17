import sys
import types
import unittest
from unittest.mock import patch

from managers import DepartmentManager


class DepartmentHandoffIntegrityTests(unittest.TestCase):
    def test_audit_receives_the_exact_preceding_media_result(self):
        media_result = {
            "department": "media",
            "status": "COMPLETED",
            "artifact": "final-video-script",
            "quality_notes": ["source list included"],
        }
        previous_results = [
            {"department": "finance", "status": "COMPLETED", "report": "budget"},
            media_result,
            {"department": "business", "status": "COMPLETED", "report": "strategy"},
        ]
        captured = {}

        def fake_run_audit(task, received_media_result):
            captured["task"] = task
            captured["media_result"] = received_media_result
            return {
                "department": "audit",
                "status": "PASSED_WITH_LIMITATIONS",
                "auditors": [],
                "summary": {"total_checks": 1, "passed_checks": 1, "failed_checks": 0},
                "failed_checks": [],
                "publication_approved": False,
                "final_decision": "CEO_APPROVAL_REQUIRED",
            }

        audit_module = types.ModuleType("audit_agents")
        audit_module.run_audit = fake_run_audit
        audit_module.run_general_audit = lambda task, results: {
            "department": "audit",
            "status": "PASSED_WITH_LIMITATIONS",
            "summary": {"total_checks": 1, "passed_checks": 1, "failed_checks": 0},
            "auditors": [],
            "failed_checks": [],
            "publication_approved": False,
            "final_decision": "CEO_APPROVAL_REQUIRED",
        }

        with patch.dict(sys.modules, {"audit_agents": audit_module}):
            result = DepartmentManager("audit").receive_task(
                "Independently review the finished media output.",
                context={"previous_results": previous_results},
            )

        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(
            captured["task"],
            "Independently review the finished media output.",
        )
        self.assertIs(captured["media_result"], media_result)

    def test_audit_uses_general_handoff_review_without_media(self):
        audit_module = types.ModuleType("audit_agents")
        audit_module.run_audit = unittest.mock.Mock(
            side_effect=AssertionError("Media-specific audit must not run without Media")
        )
        audit_module.run_general_audit = unittest.mock.Mock(return_value={
            "department": "audit",
            "status": "REVIEW_REQUIRED",
            "publication_approved": False,
            "final_decision": "CEO_APPROVAL_REQUIRED",
        })

        previous = [
            {"department": "finance", "status": "COMPLETED", "report": "Finance report"},
            {"department": "business", "status": "COMPLETED", "report": "Business report"},
        ]
        with patch.dict(sys.modules, {"audit_agents": audit_module}):
            result = DepartmentManager("audit").receive_task(
                "Review the preceding work.",
                context={"previous_results": previous},
            )

        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertFalse(result["publication_approved"])
        audit_module.run_audit.assert_not_called()
        audit_module.run_general_audit.assert_called_once_with(
            "Review the preceding work.", previous
        )


if __name__ == "__main__":
    unittest.main()
