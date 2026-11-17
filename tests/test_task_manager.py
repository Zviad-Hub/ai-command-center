import unittest
from unittest.mock import Mock, patch

from task_manager import submit_task


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
        self.assertEqual(record["overall_status"], "COMPLETED")
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

        submit_task("Review this application.")

        self.assertEqual(
            manager.receive_task.call_args.args[0],
            "Review this application."
        )

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


if __name__ == "__main__":
    unittest.main()
