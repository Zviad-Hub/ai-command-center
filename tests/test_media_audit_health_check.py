import unittest
from unittest.mock import patch

from media_audit_health_check import (
    is_system_health_check,
    run_media_audit_health_check,
)


class MediaAuditHealthCheckTests(unittest.TestCase):
    def test_detects_health_check_prompts(self):
        self.assertTrue(is_system_health_check("SYSTEM HEALTH CHECK: inspect all departments"))
        self.assertTrue(is_system_health_check("Run a complete system diagnostic"))
        self.assertFalse(is_system_health_check("Create a YouTube video about history."))

    def test_health_check_only_inspects_media_and_audit_entrypoints(self):
        result = run_media_audit_health_check("SYSTEM HEALTH CHECK")
        self.assertEqual(result["departments"], ["media", "audit"])
        self.assertEqual(len(result["results"]), 2)
        self.assertTrue(all(
            item["diagnostic_scope"] == "MODULE_AND_ENTRYPOINTS_ONLY"
            for item in result["results"]
        ))
        self.assertTrue(all(
            item["production_pipeline_executed"] is False
            for item in result["results"]
        ))
        self.assertTrue(all(
            item["publication_approved"] is False
            for item in result["results"]
        ))
        self.assertEqual(result["overall_status"], "DIAGNOSTIC_ONLY")
        self.assertTrue(result["human_review_required"])

    def test_missing_entrypoint_is_review_required_not_a_false_pass(self):
        with patch(
            "media_audit_health_check._check_module",
            side_effect=[
                {"status": "ERROR", "available": False,
                 "callables": {"run_media_department": False},
                 "issue_code": "MODULE_IMPORT_FAILED"},
                {"status": "CONFIGURATION_CHECKED", "available": True,
                 "callables": {"run_audit": True}, "issue_code": None},
            ],
        ):
            result = run_media_audit_health_check("SYSTEM HEALTH CHECK")

        self.assertEqual(result["overall_status"], "REVIEW_REQUIRED")
        self.assertEqual(result["results"][0]["issue_code"], "MODULE_IMPORT_FAILED")


if __name__ == "__main__":
    unittest.main()
