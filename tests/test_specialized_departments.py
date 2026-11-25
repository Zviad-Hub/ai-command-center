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
            "Arithmetic review: calculation formulas, revenue and cost inputs are incomplete; assumptions and units need clarification.",
            "Risk review: liquidity risk and downside sensitivity require mitigation; tax treatment is uncertain and requires local professional review.",
            "Budget forecast scenarios and cash flow projections use assumptions; missing inputs and cost sensitivity remain.",
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
        self.assertEqual(result["specialist_quality_validation"]["status"], "PASS")
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
            "Eligibility criteria from the official tender: notice not provided; cannot confirm without evidence.",
            "Compliance document checklist: attachments are missing and validity is unclear; evidence not provided.",
            "Pricing and quantity assumptions are missing; financial risk and uncertainty cannot be assessed.",
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
            "Market and customer demand review: validation evidence and assumptions remain incomplete.",
            "Business strategy and positioning options: trade-offs, dependencies and risks need review.",
            "Operations KPI measures and formulas need data; missing workflow inputs are identified.",
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
            "Financial arithmetic and calculation formula review: revenue inputs and assumptions are incomplete.",
            "Risk and liquidity review: downside sensitivity and mitigation are required.",
            "Budget forecast scenarios: revenue assumptions are unverified and missing inputs remain.",
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
            "Eligibility criteria from the official tender: notice not provided; cannot confirm without evidence.",
            "Compliance document checklist: requirements are missing and unclear; evidence not provided.",
            "Pricing and quantity assumptions: financial risk and uncertainty remain.",
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
            "REVIEW STATUS: PASS\nISSUES:\nREQUIRED CORRECTIONS:\nFINAL QUALITY SUMMARY: "
            "Evidence and limitations are represented correctly.",
            "REVIEW STATUS: PASS\nThe reviewer mentioned issues, required corrections, "
            "and final quality summary in passing, but supplied no structured findings.",
            "REVIEW STATUS: PASS\nISSUES: None.\nREQUIRED CORRECTIONS: None.\n"
            "FINAL QUALITY SUMMARY: Looks good.",
            "REVIEW STATUS: NEEDS_REVISION\nISSUES: None.\n"
            "REQUIRED CORRECTIONS: None.\n"
            "FINAL QUALITY SUMMARY: Evidence and limitations are represented correctly.",
        ]

        for review in invalid_reviews:
            with self.subTest(review=review):
                self.assertFalse(_review_is_substantive(review))

        self.assertTrue(_review_is_substantive(PASS_REVIEW))

    @patch("department_agents._research_context")
    @patch("department_agents.ask_ai")
    def test_manager_and_reviewer_receive_all_specialist_evidence(
        self, ai_mock, research_mock
    ):
        specialist_outputs = [
            "SPECIALIST_ALPHA: Revenue calculation inputs are incomplete; formulas, units and assumptions need verification.",
            "SPECIALIST_BETA: Liquidity risk requires downside sensitivity analysis and mitigation controls.",
            "SPECIALIST_GAMMA: Budget forecast assumptions are unverified; missing cash flow inputs remain.",
        ]
        manager_draft = (
            "EXECUTIVE SUMMARY\nINPUTS\nCALCULATIONS\nASSUMPTIONS\n"
            "RISKS\nRECOMMENDATIONS\nMISSING INFORMATION\n"
            "Manager synthesis: figures remain provisional."
        )
        ai_mock.side_effect = specialist_outputs + [manager_draft, PASS_REVIEW]
        research_mock.return_value = {
            "status": "NOT_CONFIGURED",
            "sources": [],
            "warning": "No research key."
        }

        result = run_department_workflow(
            "finance",
            "Review the supplied monthly operating budget.",
            context={"original_task": "Assess financial viability."}
        )

        manager_prompt = ai_mock.call_args_list[3].args[1]
        reviewer_prompt = ai_mock.call_args_list[4].args[1]

        for evidence in specialist_outputs:
            with self.subTest(evidence=evidence):
                self.assertIn(evidence, manager_prompt)
                self.assertIn(evidence, reviewer_prompt)

        self.assertIn(manager_draft, reviewer_prompt)
        self.assertIn("Review the supplied monthly operating budget.", reviewer_prompt)
        self.assertEqual(result["status"], "COMPLETED")
        self.assertTrue(result["quality_review_passed"])

    def test_business_heading_accepts_unicode_nonbreaking_hyphen(self):
        from department_agents import _missing_report_sections

        report = (
            "EXECUTIVE SUMMARY\\nBUSINESS CONTEXT\\nANALYSIS\\n"
            "OPTIONS AND TRADE‑OFFS\\nRISKS\\nRECOMMENDATIONS\\n"
            "KPIS\\nMISSING INFORMATION"
        )
        self.assertNotIn(
            "options and trade-offs",
            _missing_report_sections("business", report),
        )

    @patch("department_agents._research_context")
    @patch("department_agents.ask_ai")
    def test_business_and_tenders_preserve_specialist_evidence_for_review(
        self, ai_mock, research_mock
    ):
        scenarios = (
            (
                "business",
                "Assess whether the supplied customer-retention plan is viable.",
                [
                    "MARKET ANALYST: Market customer demand has not been measured; validation evidence and assumptions are missing.",
                    "STRATEGY PLANNER: Business strategy and positioning options have trade-offs, dependencies and risks.",
                    "OPERATIONS ANALYST: Operations retention KPI needs a defined formula, measurement data and denominator.",
                ],
                (
                    "EXECUTIVE SUMMARY\\nBUSINESS CONTEXT\\nANALYSIS\\n"
                    "OPTIONS AND TRADE-OFFS\\nRISKS\\nRECOMMENDATIONS\\n"
                    "KPIS\\nMISSING INFORMATION\\n"
                    "Business recommendation remains conditional."
                ),
            ),
            (
                "tenders",
                "Assess the supplied tender pack for eligibility and compliance gaps.",
                [
                    "ELIGIBILITY ANALYST: Official tender eligibility criteria are unclear; evidence cannot confirm the requirement.",
                    "COMPLIANCE ANALYST: Compliance document checklist shows one requirement is missing and not provided.",
                    "PRICING ANALYST: Delivery pricing costs cannot be confirmed; financial risk and uncertainty remain due to missing data.",
                ],
                (
                    "TENDER OVERVIEW\\nELIGIBILITY\\nMANDATORY DOCUMENTS\\n"
                    "DEADLINES\\nEVALUATION CRITERIA\\nCOMPLIANCE MATRIX\\n"
                    "RISKS AND GAPS\\nQUESTIONS\\nDRAFT RESPONSE PLAN\\n"
                    "MISSING MATERIAL\\n"
                    "No bid readiness conclusion is possible yet."
                ),
            ),
        )
        research_mock.return_value = {
            "status": "NOT_CONFIGURED",
            "sources": [],
            "warning": "No research key."
        }

        for department, mission, specialist_outputs, manager_draft in scenarios:
            with self.subTest(department=department):
                ai_mock.reset_mock()
                ai_mock.side_effect = specialist_outputs + [manager_draft, PASS_REVIEW]

                result = run_department_workflow(
                    department,
                    mission,
                    context={"original_task": f"CEO request for {department}."}
                )

                manager_prompt = ai_mock.call_args_list[3].args[1]
                reviewer_prompt = ai_mock.call_args_list[4].args[1]

                for evidence in specialist_outputs:
                    with self.subTest(department=department, evidence=evidence):
                        self.assertIn(evidence, manager_prompt)
                        self.assertIn(evidence, reviewer_prompt)

                self.assertIn(manager_draft, reviewer_prompt)
                self.assertIn(mission, manager_prompt)
                self.assertIn(mission, reviewer_prompt)
                self.assertEqual(result["status"], "COMPLETED")
                self.assertTrue(result["quality_review_passed"])
                self.assertEqual(len(result["specialist_reports"]), 3)
                self.assertFalse(result["execution_performed"])

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
            "Market customer demand and competitor evidence review; validation assumptions are missing.",
            "Business strategy positioning options and trade-offs; dependencies and risks identified.",
            "Operations KPI formulas and measurement data; missing process inputs identified.",
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


    @patch("department_agents._research_context")
    @patch("department_agents.ask_ai")
    def test_daily_quota_exhaustion_stops_remaining_specialist_calls(
        self, ai_mock, research_mock
    ):
        ai_mock.side_effect = RuntimeError("Groq daily quota has been exhausted.")
        research_mock.return_value = {"status": "NOT_CONFIGURED", "sources": []}

        result = run_department_workflow("finance", "Review a budget.")

        self.assertEqual(ai_mock.call_count, 1)
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(
            result["specialist_failures"][0]["error_code"],
            "PROVIDER_DAILY_QUOTA_EXHAUSTED",
        )
        self.assertEqual(
            [item["specialist"] for item in result["specialist_not_run"]],
            ["risk_controller", "budget_planner"],
        )
        self.assertTrue(all(
            item["status"] == "NOT_RUN"
            for item in result["specialist_not_run"]
        ))
        self.assertEqual(result["report"], "")


    @patch("department_agents._research_context")
    @patch("department_agents.ask_ai")
    def test_independent_specialist_validator_blocks_generic_reports_before_synthesis(
        self, ai_mock, research_mock
    ):
        ai_mock.side_effect = [
            "Done.",
            "Looks good.",
            "All fine.",
        ]
        research_mock.return_value = {"status": "NOT_CONFIGURED", "sources": []}

        result = run_department_workflow(
            "business",
            "Prepare a business strategy and operational review.",
        )

        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["report"], "")
        self.assertEqual(result["specialist_quality_validation"]["status"], "REVIEW_REQUIRED")
        self.assertTrue(result["specialist_quality_validation"]["issues"])
        self.assertEqual(ai_mock.call_count, 3)
        self.assertFalse(result["quality_review_passed"] if "quality_review_passed" in result else False)



if __name__ == "__main__":
    unittest.main()
