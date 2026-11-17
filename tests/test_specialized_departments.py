import unittest
from unittest.mock import patch

from department_agents import run_department_workflow
from managers import get_manager


class SpecializedDepartmentTests(unittest.TestCase):

    @patch("department_agents._research_context")
    @patch("department_agents.ask_ai")
    def test_finance_returns_advisory_report_without_transactions(
        self, ai_mock, research_mock
    ):
        ai_mock.return_value = "EXECUTIVE SUMMARY\nA sample budget analysis."
        research_mock.return_value = {
            "status": "NOT_CONFIGURED",
            "sources": [],
            "warning": "No research key."
        }

        result = run_department_workflow(
            "finance",
            "Analyze a monthly operating budget.",
            context={"original_task": "Prepare a budget review."}
        )

        self.assertEqual(result["status"], "COMPLETED")
        self.assertTrue(result["advisory_only"])
        self.assertTrue(result["requires_ceo_approval"])
        self.assertFalse(result["execution_authorized"])
        self.assertFalse(result["financial_transaction_performed"])
        self.assertFalse(result["execution_performed"])
        self.assertIn("sample budget analysis", result["report"])

    @patch("department_agents._research_context")
    @patch("department_agents.ask_ai")
    def test_tenders_workflow_never_submits_bid(
        self, ai_mock, research_mock
    ):
        ai_mock.return_value = "TENDER OVERVIEW\nDocuments to verify."
        research_mock.return_value = {
            "status": "PARTIAL",
            "sources": [],
            "warning": "Only partial research."
        }

        result = get_manager("tenders").receive_task(
            "Prepare a tender eligibility checklist.",
            context={"original_task": "Review tender opportunity."}
        )

        self.assertEqual(result["department"], "tenders")
        self.assertEqual(result["status"], "COMPLETED")
        self.assertFalse(result["tender_submitted"])
        self.assertFalse(result["external_contact_made"])
        self.assertFalse(result["execution_authorized"])

    @patch("department_agents._research_context")
    @patch("department_agents.ask_ai")
    def test_business_ai_failure_requires_review(
        self, ai_mock, research_mock
    ):
        ai_mock.side_effect = RuntimeError("Provider unavailable")
        research_mock.return_value = {
            "status": "NOT_CONFIGURED",
            "sources": []
        }

        result = run_department_workflow(
            "business",
            "Assess a new business idea."
        )

        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["report"], "")
        self.assertTrue(result["requires_ceo_approval"])
        self.assertFalse(result["execution_performed"])

    def test_empty_department_task_is_rejected(self):
        result = run_department_workflow("finance", " ")
        self.assertEqual(result["status"], "REJECTED")

    def test_unknown_department_is_not_silently_accepted(self):
        result = run_department_workflow("legal", "Review a contract.")
        self.assertEqual(result["status"], "REJECTED")

    @patch("department_agents.run_research")
    @patch("department_agents.ask_ai")
    def test_research_sources_are_marked_as_unverified_context(
        self, ai_mock, research_mock
    ):
        ai_mock.return_value = "Business analysis."
        research_mock.return_value = {
            "status": "COMPLETED",
            "sources": [{
                "title": "Candidate source",
                "url": "https://example.com",
                "domain": "example.com",
                "content_type": "SEARCH_RESULT_SNIPPET",
                "content": "Candidate text.",
                "verification_status": "NOT_VERIFIED"
            }],
            "warning": "Evidence candidates only."
        }

        with patch.dict("os.environ", {"TAVILY_API_KEY": "test-key"}):
            result = run_department_workflow("business", "Analyze a market.")

        self.assertEqual(result["research_status"], "COMPLETED")
        self.assertEqual(len(result["sources"]), 1)
        prompt = ai_mock.call_args.args[1]
        self.assertIn("NOT independently verified", prompt)
        self.assertIn("Candidate text.", prompt)


if __name__ == "__main__":
    unittest.main()
