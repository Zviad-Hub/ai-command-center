import unittest
from unittest.mock import Mock, patch

from task_manager import build_public_task_summary, submit_task


class TaskManagerTests(unittest.TestCase):

    @patch("task_manager.save_tasks")
    @patch("task_manager.load_tasks", return_value=[])
    @patch("task_manager.get_manager")
    @patch("task_manager.route_task")
    def test_routes_department_specific_missions_and_context(
        self, route_mock, manager_factory, load_mock, save_mock
    ):
        route_mock.return_value = {
            "departments": ["media", "audit"],
            "missions": {
                "media": "Create the requested video.",
                "audit": "Independently audit the finished video."
            },
            "routing_method": "TEST"
        }

        media_manager = Mock()
        media_manager.receive_task.return_value = {
            "department": "media",
            "status": "REVIEW_REQUIRED",
            "artifact": "video-script",
            "edited_script": "Final edited script.",
            "fact_check": "VERIFIED claims were reviewed.",
            "validation": {"word_count_passed": True},
            "publication_approved": False
        }
        audit_manager = Mock()
        audit_manager.receive_task.return_value = {
            "department": "audit",
            "status": "PASSED_WITH_LIMITATIONS",
            "publication_approved": False,
            "summary": {"total_checks": 12, "passed_checks": 12, "failed_checks": 0},
            "final_decision": "CEO_APPROVAL_REQUIRED"
        }
        manager_factory.side_effect = [media_manager, audit_manager]

        record = submit_task("Create one video about an old mystery.")

        media_args = media_manager.receive_task.call_args
        self.assertEqual(media_args.args[0], "Create the requested video.")
        self.assertEqual(
            media_args.kwargs["context"]["original_task"],
            "Create one video about an old mystery."
        )
        self.assertEqual(
            media_args.kwargs["context"]["previous_results"],
            []
        )

        audit_args = audit_manager.receive_task.call_args
        self.assertEqual(
            audit_args.args[0],
            "Independently audit the finished video."
        )
        self.assertEqual(
            audit_args.kwargs["context"]["previous_results"],
            [media_manager.receive_task.return_value]
        )
        self.assertEqual(record["departments"], ["media", "audit"])
        self.assertEqual(len(record["results"]), 2)
        self.assertEqual(record["organization_audit"]["status"], "PASS")
        self.assertEqual(record["overall_status"], "READY_FOR_HUMAN_REVIEW")
        self.assertEqual(record["organization_audit"]["content_alignment_status"], "HUMAN_REVIEW_REQUIRED")
        self.assertTrue(record["human_review_required"])
        save_mock.assert_called_once()

    @patch("task_manager.save_tasks")
    @patch("task_manager.load_tasks", return_value=[])
    @patch("task_manager.get_manager")
    @patch("task_manager.route_task")
    def test_falls_back_to_original_task_if_mission_missing(
        self, route_mock, manager_factory, load_mock, save_mock
    ):
        route_mock.return_value = {
            "departments": ["technical"],
            "missions": {}
        }
        manager = Mock()
        manager.receive_task.return_value = {
            "department": "technical",
            "status": "REVIEW_REQUIRED"
        }
        manager_factory.return_value = manager

        record = submit_task("Review this application.")

        self.assertEqual(
            manager.receive_task.call_args.args[0],
            "Review this application."
        )
        # A department's REVIEW_REQUIRED result must be reflected in the
        # organization-level verdict as well.
        self.assertEqual(record["overall_status"], "REVIEW_REQUIRED")
        self.assertEqual(record["organization_audit"]["status"], "REVIEW_REQUIRED")

    @patch("task_manager.save_tasks")
    @patch("task_manager.load_tasks", return_value=[])
    @patch("task_manager.get_manager")
    @patch("task_manager.route_task")
    def test_later_manager_cannot_mutate_previous_recorded_results(
        self, route_mock, manager_factory, load_mock, save_mock
    ):
        route_mock.return_value = {
            "departments": ["media", "audit"],
            "missions": {
                "media": "Create the media output.",
                "audit": "Review the media output."
            }
        }

        original_media_result = {
            "department": "media",
            "status": "COMPLETED",
            "report": {
                "title": "Original title",
                "findings": ["verified source"]
            }
        }
        media_manager = Mock()
        media_manager.receive_task.return_value = original_media_result

        audit_manager = Mock()

        def mutate_previous_results(task, context=None):
            previous = context["previous_results"][0]
            previous["report"]["title"] = "Tampered title"
            previous["report"]["findings"].append("fabricated finding")
            return {"department": "audit", "status": "COMPLETED"}

        audit_manager.receive_task.side_effect = mutate_previous_results
        manager_factory.side_effect = [media_manager, audit_manager]

        record = submit_task("Create and audit one media output.")

        self.assertEqual(
            record["results"][0]["report"],
            {
                "title": "Original title",
                "findings": ["verified source"]
            }
        )
        self.assertEqual(
            original_media_result["report"],
            {
                "title": "Original title",
                "findings": ["verified source"]
            }
        )

    def test_rejects_empty_ceo_task_before_routing(self):
        with patch("task_manager.route_task") as route_mock:
            with self.assertRaises(ValueError):
                submit_task("   ")
        route_mock.assert_not_called()


    def test_semantic_alignment_audit_is_disabled_by_default(self):
        with patch.dict("os.environ", {"AI_ORGANIZATION_SEMANTIC_AUDIT": ""}), \
             patch("task_manager.route_task", return_value={
                 "departments": ["technical"], "missions": {"technical": "Review the app."}
             }), \
             patch("task_manager.get_manager") as manager_factory, \
             patch("task_manager.load_tasks", return_value=[]), \
             patch("task_manager.save_tasks"), \
             patch("task_manager.run_semantic_alignment_audit") as semantic_mock:
            manager = Mock()
            manager.receive_task.return_value = {
                "department": "technical", "status": "REVIEW_REQUIRED"
            }
            manager_factory.return_value = manager

            record = submit_task("Review the app.")

        semantic_mock.assert_not_called()
        self.assertEqual(record["semantic_audit"]["status"], "NOT_RUN")
        self.assertEqual(record["overall_status"], "REVIEW_REQUIRED")

    def test_opt_in_semantic_revision_blocks_ready_for_human_review_status(self):
        valid_finance_result = {
            "department": "finance",
            "status": "COMPLETED",
            "report": "Finance report with calculations and assumptions.",
            "requires_ceo_approval": True,
            "execution_authorized": False,
            "execution_performed": False,
            "specialist_quality_validation": {"status": "PASS", "issues": []},
            "quality_review_passed": True,
        }
        audit_pass = {
            "status": "PASS",
            "department_checks": [{"department": "finance", "status": "PASS", "issues": []}],
            "issues": [],
            "content_alignment_status": "HUMAN_REVIEW_REQUIRED",
            "human_review_required": True,
            "limitations": [],
        }
        semantic_revision = {
            "status": "NEEDS_REVISION",
            "task_coverage": "PARTIAL",
            "summary": "One requested item is missing.",
            "missing_requirements": ["Cash-flow sensitivity analysis is missing."],
            "human_review_required": True,
        }
        with patch.dict("os.environ", {"AI_ORGANIZATION_SEMANTIC_AUDIT": "true"}), \
             patch("task_manager.route_task", return_value={
                 "departments": ["finance"], "missions": {"finance": "Prepare the financial review."}
             }), \
             patch("task_manager.get_manager") as manager_factory, \
             patch("task_manager.load_tasks", return_value=[]), \
             patch("task_manager.save_tasks"), \
             patch("task_manager.audit_organization_task", return_value=audit_pass), \
             patch("task_manager.run_semantic_alignment_audit", return_value=semantic_revision) as semantic_mock:
            manager = Mock()
            manager.receive_task.return_value = valid_finance_result
            manager_factory.return_value = manager

            record = submit_task("Prepare the financial review and cash-flow analysis.")

        semantic_mock.assert_called_once()
        self.assertEqual(record["semantic_audit"]["status"], "NEEDS_REVISION")
        self.assertEqual(record["overall_status"], "REVIEW_REQUIRED")
        self.assertEqual(
            record["organization_audit"]["content_alignment_status"],
            "AI_REVIEW_NEEDS_REVISION",
        )


    def test_public_task_summary_exposes_gate_statuses_without_private_content(self):
        record = {
            "id": "safe1234",
            "task": "PRIVATE CEO TASK",
            "overall_status": "REVIEW_REQUIRED",
            "departments": ["finance"],
            "results": [{
                "department": "finance",
                "status": "COMPLETED",
                "report": "PRIVATE FINANCIAL REPORT",
                "specialist_reports": {"analyst": "PRIVATE SPECIALIST OUTPUT"},
                "specialist_quality_validation": {"status": "PASS"},
                "quality_review_passed": True,
                "requires_ceo_approval": True,
                "execution_performed": False,
            }, {
                "department": "media",
                "status": "REVIEW_REQUIRED",
                "specialists": ["Research Agent"],
                "validation": {
                    "word_count_passed": True,
                    "visual_scene_count_passed": False,
                    "timestamps_passed": True,
                },
                "warnings": ["PRIVATE MEDIA WARNING"],
                "publication_approved": False,
            }, {
                "department": "audit",
                "status": "REVIEW_REQUIRED",
                "auditors": [{"auditor": "PRIVATE AUDITOR NAME"}],
                "summary": {
                    "total_checks": 12,
                    "passed_checks": 10,
                    "failed_checks": 2,
                },
                "final_decision": "CEO_APPROVAL_REQUIRED",
                "publication_approved": False,
            }],
            "organization_audit": {
                "status": "REVIEW_REQUIRED",
                "content_alignment_status": "HUMAN_REVIEW_REQUIRED",
                "department_checks": [{
                    "department": "finance",
                    "status": "REVIEW_REQUIRED",
                    "issues": ["PRIVATE AUDIT DETAIL"],
                }],
            },
            "semantic_audit": {
                "status": "NOT_RUN",
                "summary": "PRIVATE SEMANTIC SUMMARY",
            },
            "human_review_required": True,
        }

        summary = build_public_task_summary(record)
        rendered = repr(summary)

        self.assertEqual(summary["run_status"], "FINISHED")
        self.assertEqual(summary["overall_status"], "REVIEW_REQUIRED")
        self.assertEqual(
            summary["department_results"][0]["specialist_validation_status"],
            "PASS",
        )
        self.assertEqual(summary["organization_audit"]["department_checks"][0]["issue_count"], 1)
        media_row = summary["department_results"][1]
        self.assertEqual(media_row["script_validation"]["visual_scene_count_passed"], False)
        self.assertEqual(media_row["warning_count"], 1)
        audit_row = summary["department_results"][2]
        self.assertEqual(audit_row["audit_failed_checks"], 2)
        self.assertEqual(audit_row["final_decision"], "CEO_APPROVAL_REQUIRED")
        self.assertTrue(summary["human_review_required"])
        for private_text in (
            "PRIVATE CEO TASK",
            "PRIVATE FINANCIAL REPORT",
            "PRIVATE SPECIALIST OUTPUT",
            "PRIVATE AUDIT DETAIL",
            "PRIVATE SEMANTIC SUMMARY",
        ):
            self.assertNotIn(private_text, rendered)

    def test_public_task_summary_exposes_safe_failure_diagnostics_only(self):
        record = {
            "id": "diag1234",
            "overall_status": "REVIEW_REQUIRED",
            "departments": ["media", "audit"],
            "results": [{
                "department": "media",
                "status": "ERROR",
                "failed_stage": "Research Agent",
                "message": "PRIVATE PROVIDER ERROR WITH SECRET DATA",
                "research": {
                    "status": "NO_RESULTS",
                    "source_count": 0,
                    "full_page_count": 0,
                    "snippet_count": 0,
                    "query": "PRIVATE SEARCH QUERY",
                    "sources": [{"url": "https://private.example"}],
                },
            }, {
                "department": "audit",
                "status": "REVIEW_REQUIRED",
                "failed_checks": [
                    {"auditor": "Evidence Auditor", "check": "Source verification", "passed": False, "details": "PRIVATE DETAILS"},
                    {"auditor": "Integrity Auditor", "check": "Research data structure", "passed": False, "details": "PRIVATE DETAILS"},
                ],
            }],
            "organization_audit": {"status": "REVIEW_REQUIRED", "department_checks": []},
            "semantic_audit": {"status": "NOT_RUN"},
            "human_review_required": True,
        }

        summary = build_public_task_summary(record)
        media_row, audit_row = summary["department_results"]

        self.assertEqual(media_row["failed_stage"], "Research Agent")
        self.assertEqual(media_row["research_status"], "NO_RESULTS")
        self.assertEqual(media_row["research_source_count"], 0)
        self.assertEqual(audit_row["failed_check_names"], [
            "Source verification",
            "Research data structure",
        ])
        self.assertEqual(audit_row["failed_auditor_names"], [
            "Evidence Auditor",
            "Integrity Auditor",
        ])

        rendered = repr(summary)
        for private_text in (
            "PRIVATE PROVIDER ERROR",
            "PRIVATE SEARCH QUERY",
            "private.example",
            "PRIVATE DETAILS",
            "SECRET DATA",
        ):
            self.assertNotIn(private_text, rendered)

    def test_public_task_summary_fails_safely_for_invalid_input(self):
        summary = build_public_task_summary(None)
        self.assertEqual(summary["run_status"], "FAILED")
        self.assertEqual(summary["error_code"], "INVALID_TASK_RECORD")
        self.assertTrue(summary["human_review_required"])


if __name__ == "__main__":
    unittest.main()
