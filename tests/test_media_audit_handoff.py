import unittest
from unittest.mock import patch

from managers import get_manager


class MediaAuditManagerHandoffTests(unittest.TestCase):

    def test_audit_requires_a_media_result(self):
        result = get_manager("audit").receive_task(
            "Audit the finished media package.",
            context={"previous_results": []},
        )
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertFalse(result["publication_approved"])

    def test_audit_receives_the_media_result_from_previous_department(self):
        media_result = {
            "department": "media",
            "status": "REVIEW_REQUIRED",
            "publication_approved": False,
            "edited_script": "A completed draft.",
        }
        expected = {
            "department": "audit",
            "status": "REVIEW_REQUIRED",
            "publication_approved": False,
        }
        with patch("audit_agents.run_audit", return_value=expected) as audit:
            result = get_manager("audit").receive_task(
                "Audit the finished media package.",
                context={"previous_results": [
                    {"department": "finance", "status": "COMPLETED"},
                    media_result,
                ]},
            )
        audit.assert_called_once_with("Audit the finished media package.", media_result)
        self.assertEqual(result, expected)

    def test_audit_does_not_substitute_an_unrelated_department_result(self):
        result = get_manager("audit").receive_task(
            "Audit the finished media package.",
            context={"previous_results": [
                {"department": "technical", "status": "COMPLETED"}
            ]},
        )
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertFalse(result["publication_approved"])

    def test_media_manager_dispatches_to_media_pipeline(self):
        expected = {
            "department": "media",
            "status": "REVIEW_REQUIRED",
            "publication_approved": False,
        }
        with patch("media_agents.run_media_department", return_value=expected) as media:
            result = get_manager("media").receive_task("Create a media package.")
        media.assert_called_once_with("Create a media package.")
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
