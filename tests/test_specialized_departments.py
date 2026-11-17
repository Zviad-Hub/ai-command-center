import unittest
from unittest.mock import patch

from department_agents import run_department_workflow
from managers import get_manager


PASS_REVIEW = (
    "REVIEW STATUS: PASS\n"
    "ISSUES: None.\n"
    "REQUIRED CORRECTIONS: None.\n"
    "FINAL QUALITY SUMMARY: Evidence and limitations are represented correctly."
)


class SpecializedDepartmentTests(unittest.TestCase):

    @patch("department_agents._research_context")
    @patch("department_agents.ask_ai")
    def test_finance_runs_specialists_manager_and_reviewer(
        self, ai_mock, research_mock
    ):
        ai_mock.side_effect = [
            "Arithmetic review: inputs are incomplete.",
            "Risk review: tax treatment requires local professional review.",
            "Budget scenarios: revenue assumptions are unverified.",
            "EXECUTIVE SUMMARY\nINPUTS\nCALCULATIONS\nASSUMPTIONS\nRISKS\nRECOMMENDATIONS\nMISSING INFORMATION\nA sample budget analysis.",
            PASS_REVIEW
        ]
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
        self.assertEqual(len(result["specialist_reports"]), 3)
        self.assertTrue(result["quality_review_passed"])
        self.assertTrue(result["advisory_only"])
        self.assertTrue(result["requires_ceo_approval"])
        self.assertFalse(result["execution_authorized"])
        self.assertFalse(result["financial_transaction_performed"])
        self.assertFalse(result["execution_performed"])
        self.assertIn("sample budget analysis", result["report"])
        self.assertEqual(ai_mock.call_count, 5)

    @patch("department_agents._research_context")
    @patch("department_agents.ask_ai")
    def test_tenders_workflow_never_submits_bid(
        self, ai_mock, research_mock
    ):
        ai_mock.side_effect = [
            "Eligibility: official notice not supplied.",
            "Documents: cannot confirm without attachments.",
            "Pricing: no quantities or pricing schedule supplied.",
            "TENDER OVERVIEW\nELIGIBILITY\nMANDATORY DOCUMENTS\nDEADLINES\nEVALUATION CRITERIA\nCOMPLIANCE MATRIX\nRISKS AND GAPS\nQUESTIONS\nDRAFT RESPONSE PLAN\nMISSING MATERIAL\nDocuments to verify.",
            PASS_REVIEW
        ]
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
        self.assertTrue(result["quality_review_passed"])
        self.assertFalse(result["tender_submitted"])
        self.assertFalse(result["external_contact_made"])
        self.assertFalse(result["execution_authorized"])
        self.assertEqual(len(result["specialist_reports"]), 3)

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
        self.assertEqual(len(result["specialist_failures"]), 3)
        self.assertEqual(ai_mock.call_count, 3)

    @patch("department_agents._research_context")
    @patch("department_agents.ask_ai")
    def test_reviewer_must_explicitly_pass(
        self, ai_mock, research_mock
    ):
        ai_mock.side_effect = [
            "Market review complete.",
            "Strategy review complete.",
            "KPI review complete.",
            "Draft business report.",
            "REVIEW STATUS: NEEDS_REVISION\nISSUES: Unsupported market claim."
        ]
        research_mock.return_value = {"status": "NOT_CONFIGURED", "sources": []}

        result = run_department_workflow("business", "Assess a business idea.")

        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["report"], "")
        self.assertIn("draft_report", result)
        self.assertIn("quality_review", result)
        self.assertFalse(result["execution_authorized"])
        self.assertEqual(ai_mock.call_count, 5)

    @patch("department_agents._research_context")
    @patch("department_agents.ask_ai")
    def test_specialist_failure_stops_manager_and_reviewer(
        self, ai_mock, research_mock
    ):
        def fail_second_call(system_prompt, user_prompt):
            if ai_mock.call_count == 2:
                raise RuntimeError("Provider unavailable")
            return "Specialist analysis returned."

        ai_mock.side_effect = fail_second_call
        research_mock.return_value = {"status": "NOT_CONFIGURED", "sources": []}

        result = run_department_workflow("finance", "Review a budget.")

        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["report"], "")
        self.assertEqual(len(result["specialist_failures"]), 1)
        self.assertEqual(ai_mock.call_count, 3)
        self.assertFalse(result["execution_performed"])


    @patch("department_agents._research_context")
    @patch("department_agents.ask_ai")
    def test_reviewer_one_line_pass_is_not_accepted(self, ai_mock, research_mock):
        ai_mock.side_effect = [
            "Financial specialist findings.",
            "Risk specialist findings.",
            "Budget specialist findings.",
            "EXECUTIVE SUMMARY\nINPUTS\nCALCULATIONS\nASSUMPTIONS\nRISKS\nRECOMMENDATIONS\nMISSING INFORMATION\nComplete finance report.",
            "REVIEW STATUS: PASS",
        ]
        research_mock.return_value = {"status": "NOT_CONFIGURED", "sources": []}

        result = run_department_workflow("finance", "Review a budget.")

        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["report"], "")
        self.assertFalse(result.get("quality_review_passed", False))

    @patch("department_agents._research_context")
    @patch("department_agents.ask_ai")
    def test_incomplete_tender_report_is_rejected_even_with_reviewer_pass(
        self, ai_mock, research_mock
    ):
        ai_mock.side_effect = [
            "Eligibility findings.",
            "Compliance findings.",
            "Pricing risk findings.",
            "TENDER OVERVIEW\nELIGIBILITY\nMANDATORY DOCUMENTS\nA partial report.",
            PASS_REVIEW,
        ]
        research_mock.return_value = {"status": "NOT_CONFIGURED", "sources": []}

        result = run_department_workflow("tenders", "Review tender documents.")

        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["report"], "")
        self.assertIn("deadlines", result["missing_report_sections"])
        self.assertIn("compliance matrix", result["missing_report_sections"])

    def test_reviewer_rejects_headings_without_real_section_content(self):
        from department_agents import _review_is_substantive

        invalid_reviews = [
            "REVIEW STATUS: PASS\\nISSUES:\\nREQUIRED CORRECTIONS:\\nFINAL QUALITY SUMMARY: "
            "Evidence and limitations are represented correctly.",
            "REVIEW STATUS: PASS\\nThe reviewer mentioned issues, required corrections, "
            "and final quality summary in passing, but supplied no structured findings.",
            "REVIEW STATUS: PASS\\nISSUES: None.\\nREQUIRED CORRECTIONS: None.\\n"
            "FINAL QUALITY SUMMARY: Looks good.",
            "REVIEW STATUS: NEEDS_REVISION\\nISSUES: None.\\n"
            "REQUIRED CORRECTIONS: None.\\n"
            "FINAL QUALITY SUMMARY: Evidence and limitations are represented correctly.",
        ]

        for review in invalid_reviews:
            with self.subTest(review=review):
                self.assertFalse(_review_is_substantive(review))

        self.assertTrue(_review_is_substantive(PASS_REVIEW))

    def test_substantive_reviewer_requires_all_sections(self):
        from department_agents import _review_is_substantive

        self.assertTrue(_review_is_substantive(PASS_REVIEW))
        self.assertFalse(_review_is_substantive("REVIEW STATUS: PASS"))
        self.assertFalse(_review_is_substantive(
            "REVIEW STATUS: NEEDS_REVISION\nISSUES: Missing evidence."
        ))

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
        ai_mock.side_effect = [
            "Market evidence review.",
            "Strategy review.",
            "Operations review.",
            "EXECUTIVE SUMMARY\nBUSINESS CONTEXT\nANALYSIS\nOPTIONS AND TRADE-OFFS\nRISKS\nRECOMMENDATIONS\nKPIS\nMISSING INFORMATION\nBusiness analysis.",
            PASS_REVIEW
        ]
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
        self.assertTrue(all(
            "NOT independently verified" in call.args[1]
            for call in ai_mock.call_args_list[:3]
        ))
        self.assertTrue(all(
            "Candidate text." in call.args[1]
            for call in ai_mock.call_args_list[:3]
        ))
        self.assertTrue(result["quality_review_passed"])


if __name__ == "__main__":
    unittest.main()
