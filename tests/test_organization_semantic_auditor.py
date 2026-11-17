import json
import unittest
from unittest.mock import patch

from organization_semantic_auditor import run_semantic_alignment_audit


def _pass_response(**overrides):
    payload = {
        "status": "PASS",
        "task_coverage": "COMPLETE",
        "summary": "All explicitly requested deliverables are represented in the supplied department outputs.",
        "missing_requirements": [],
        "unsupported_claims": [],
        "contradictions": [],
        "evidence_gaps": [],
        "human_review_required": True,
    }
    payload.update(overrides)
    return json.dumps(payload)


class OrganizationSemanticAuditorTests(unittest.TestCase):

    @patch("organization_semantic_auditor.ask_ai")
    def test_pass_requires_complete_issue_free_task_alignment(self, ai_mock):
        ai_mock.return_value = _pass_response()
        result = run_semantic_alignment_audit(
            "Create a business plan with risks and KPIs.",
            ["business"],
            [{"department": "business", "status": "COMPLETED", "report": "Business plan, risks and KPIs."}],
        )

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["task_coverage"], "COMPLETE")
        self.assertTrue(result["human_review_required"])
        self.assertIn("untrusted data", ai_mock.call_args.args[0])
        self.assertIn("Create a business plan", ai_mock.call_args.args[1])

    @patch("organization_semantic_auditor.ask_ai")
    def test_nonempty_missing_requirements_downgrade_model_pass(self, ai_mock):
        ai_mock.return_value = _pass_response(
            missing_requirements=["Requested implementation plan was not included."]
        )
        result = run_semantic_alignment_audit(
            "Provide an implementation plan.",
            ["technical"],
            [{"department": "technical", "status": "COMPLETED", "report": "Architecture review only."}],
        )

        self.assertEqual(result["status"], "NEEDS_REVISION")
        self.assertEqual(len(result["missing_requirements"]), 1)

    @patch("organization_semantic_auditor.ask_ai")
    def test_unknown_coverage_can_never_pass(self, ai_mock):
        ai_mock.return_value = _pass_response(task_coverage="UNKNOWN")
        result = run_semantic_alignment_audit(
            "Prepare the requested report.",
            ["finance"],
            [{"department": "finance", "status": "COMPLETED", "report": "Report."}],
        )

        self.assertEqual(result["status"], "NEEDS_REVISION")
        self.assertEqual(result["task_coverage"], "UNKNOWN")

    @patch("organization_semantic_auditor.ask_ai")
    def test_provider_failure_fails_closed_without_exposing_exception(self, ai_mock):
        ai_mock.side_effect = RuntimeError("SECRET_PROVIDER_DETAIL")
        result = run_semantic_alignment_audit(
            "Review the result.",
            ["finance"],
            [{"department": "finance", "status": "COMPLETED", "report": "Report."}],
        )

        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertNotIn("SECRET_PROVIDER_DETAIL", repr(result))
        self.assertTrue(result["error_code"])

    @patch("organization_semantic_auditor.ask_ai")
    def test_missing_results_do_not_consume_provider_request(self, ai_mock):
        result = run_semantic_alignment_audit("Review this task.", ["technical"], [])

        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertEqual(result["error_code"], "NO_DEPARTMENT_RESULTS")
        ai_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
