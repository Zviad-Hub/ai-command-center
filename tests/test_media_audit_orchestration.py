import unittest
from unittest.mock import patch

from task_manager import submit_task


class MediaAuditOrchestrationTests(unittest.TestCase):

    def test_media_result_is_handed_to_audit_before_organization_signoff(self):
        media_result = {
            "department": "media",
            "status": "REVIEW_REQUIRED",
            "publication_approved": False,
            "edited_script": "A completed media draft.",
            "fact_check": "Claim 1 STATUS: VERIFIED",
            "validation": {"word_count_passed": True},
        }
        audit_result = {
            "department": "audit",
            "status": "PASSED_WITH_LIMITATIONS",
            "summary": {
                "total_checks": 12,
                "passed_checks": 12,
                "failed_checks": 0,
            },
            "publication_approved": False,
            "final_decision": "CEO_APPROVAL_REQUIRED",
        }
        seen = {}

        class FakeManager:
            def __init__(self, department):
                self.department = department

            def receive_task(self, task, context=None):
                if self.department == "media":
                    return media_result
                seen["previous_results"] = context.get("previous_results", [])
                return audit_result

        with (
            patch("task_manager.route_task", return_value={
                "departments": ["media", "audit"],
                "missions": {
                    "media": "Create the requested media package.",
                    "audit": "Independently audit the media package.",
                },
                "routing_method": "RULE_BASED",
                "requires_ceo_approval": True,
            }),
            patch("task_manager.get_manager", side_effect=lambda name: FakeManager(name)),
            patch("task_manager.load_tasks", return_value=[]),
            patch("task_manager.save_tasks") as save,
            patch("task_manager.os.getenv", return_value=""),
            patch("task_manager.run_semantic_alignment_audit", return_value={
                "status": "PASS",
                "task_coverage": "COMPLETE",
                "summary": "All requested items are represented.",
                "missing_requirements": [],
                "unsupported_claims": [],
                "contradictions": [],
                "evidence_gaps": [],
                "human_review_required": True,
            }),
        ):
            record = submit_task("Create a short video about the test topic.")

        self.assertEqual(
            [item["department"] for item in seen["previous_results"]],
            ["media"],
        )
        self.assertEqual(record["organization_audit"]["status"], "PASS")
        self.assertEqual(record["overall_status"], "READY_FOR_HUMAN_REVIEW")
        self.assertTrue(record["human_review_required"])
        save.assert_called_once()

    def test_media_workflow_without_independent_audit_is_not_ready(self):
        media_result = {
            "department": "media",
            "status": "REVIEW_REQUIRED",
            "publication_approved": False,
            "edited_script": "A completed media draft.",
            "fact_check": "Claim 1 STATUS: VERIFIED",
            "validation": {"word_count_passed": True},
        }

        class FakeManager:
            def receive_task(self, task, context=None):
                return media_result

        with (
            patch("task_manager.route_task", return_value={
                "departments": ["media"],
                "missions": {"media": "Create the requested media package."},
            }),
            patch("task_manager.get_manager", return_value=FakeManager()),
            patch("task_manager.load_tasks", return_value=[]),
            patch("task_manager.save_tasks"),
            patch("task_manager.os.getenv", return_value=""),
        ):
            record = submit_task("Create a short video about the test topic.")

        self.assertEqual(record["organization_audit"]["status"], "REVIEW_REQUIRED")
        self.assertEqual(record["overall_status"], "REVIEW_REQUIRED")
        self.assertTrue(any(
            "independent Audit department" in issue
            for issue in record["organization_audit"]["issues"]
        ))


if __name__ == "__main__":
    unittest.main()
