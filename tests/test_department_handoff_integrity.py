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
                "status": "COMPLETED",
                "publication_approved": False,
            }

        audit_module = types.ModuleType("audit_agents")
        audit_module.run_audit = fake_run_audit

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

    def test_audit_refuses_to_run_without_a_media_result(self):
        audit_module = types.ModuleType("audit_agents")
        audit_module.run_audit = unittest.mock.Mock(
            side_effect=AssertionError("Audit must not run without Media input")
        )

        with patch.dict(sys.modules, {"audit_agents": audit_module}):
            result = DepartmentManager("audit").receive_task(
                "Review the preceding work.",
                context={
                    "previous_results": [
                        {"department": "finance", "status": "COMPLETED"},
                        {"department": "business", "status": "COMPLETED"},
                    ]
                },
            )

        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertFalse(result["publication_approved"])
        audit_module.run_audit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
