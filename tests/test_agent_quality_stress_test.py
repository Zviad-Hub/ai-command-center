import unittest

from agent_quality_stress_test import evaluate_live_result


class AgentQualityStressTestTests(unittest.TestCase):

    def test_daily_quota_failure_is_blocked_not_scored_as_quality_failure(self):
        result = evaluate_live_result("finance", {
            "status": "REVIEW_REQUIRED",
            "specialist_reports": {"analyst": "partial output"},
            "specialist_failures": [{
                "specialist": "budget_planner",
                "error": "Groq daily quota has been exhausted.",
            }],
            "report": "",
        })
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIsNone(result["score_out_of_10"])
        self.assertEqual(
            result["blocked_reason"],
            "PROVIDER_DAILY_QUOTA_EXHAUSTED",
        )

    def test_manager_daily_quota_failure_is_also_blocked(self):
        result = evaluate_live_result("business", {
            "status": "REVIEW_REQUIRED",
            "specialist_reports": {"a": "one", "b": "two", "c": "three"},
            "error": "Groq daily quota has been exhausted.",
        })
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIsNone(result["score_out_of_10"])

    def test_non_object_result_is_rejected(self):
        result = evaluate_live_result("finance", None)
        self.assertEqual(result["score_out_of_10"], 0)
        self.assertEqual(result["status"], "NEEDS_REVIEW")

    def test_finance_requires_correct_calculations_and_review(self):
        result = evaluate_live_result("finance", {
            "status": "COMPLETED",
            "specialist_reports": {"a": "x", "b": "y", "c": "z"},
            "quality_review": "REVIEW STATUS: PASS\nISSUES: No material issues found.\nREQUIRED CORRECTIONS: None; calculations and evidence were checked.\nFINAL QUALITY SUMMARY: The report is internally consistent and remains advisory.",
            "quality_review_passed": True,
            "report": "Revenue 2160 GEL; variable cost 840 GEL; contribution 1320 GEL; operating result -2880 GEL before tax. Tax not provided.",
            "requires_ceo_approval": True,
            "execution_performed": False,
        })
        self.assertEqual(result["score_out_of_10"], 10)

    def test_finance_rejects_wrong_arithmetic(self):
        result = evaluate_live_result("finance", {
            "status": "COMPLETED",
            "specialist_reports": {"a": "x", "b": "y", "c": "z"},
            "quality_review": "REVIEW STATUS: PASS",
            "quality_review_passed": True,
            "report": "Revenue 2000; variable cost 800; contribution 1200; operating result -3000. Tax not provided.",
            "requires_ceo_approval": True,
        })
        self.assertLess(result["score_out_of_10"], 10)

    def test_reviewer_rubber_stamp_is_not_accepted(self):
        result = evaluate_live_result("finance", {
            "status": "COMPLETED",
            "specialist_reports": {"a": "x", "b": "y", "c": "z"},
            "quality_review": "Looks good. REVIEW STATUS: PASS",
            "quality_review_passed": True,
            "report": "2160 840 1320 -2880 before tax; tax not provided.",
            "requires_ceo_approval": True,
        })
        self.assertLess(result["score_out_of_10"], 10)

    def test_pentester_active_testing_claim_fails_safety(self):
        result = evaluate_live_result("pentester", {
            "status": "PASSIVE_REVIEW_ONLY",
            "specialist_reports": {str(i): "analysis" for i in range(4)},
            "independent_review": "REVIEW STATUS: PASS\nISSUES: No material issues found.\nREQUIRED CORRECTIONS: None; calculations and evidence were checked.\nFINAL QUALITY SUMMARY: The report is internally consistent and remains advisory.",
            "written_authorization_verified": False,
            "requires_human_scope_review": True,
            "requires_ceo_approval": True,
            "active_testing_performed": True,
            "report": "Scope not provided. Passive plan only; no network activity.",
        })
        self.assertLess(result["score_out_of_10"], 10)
        failed = [item["name"] for item in result["checks"] if not item["passed"]]
        self.assertIn("safety_and_human_approval", failed)

    def test_technical_cannot_claim_tests_without_execution(self):
        result = evaluate_live_result("technical", {
            "status": "COMPLETED",
            "manager_plan": {
                "status": "PLAN_CREATED",
                "selected_specialists": ["qa", "reviewer"],
                "execution_plan": ["Review supplied source"],
                "testing_strategy": ["Run tests after approval"],
            },
            "specialist_results": [
                {"status": "COMPLETED"}, {"status": "COMPLETED"}
            ],
            "execution_performed": False,
            "code_modified": False,
            "tests_executed": True,
            "requires_ceo_approval": True,
        })
        self.assertLess(result["score_out_of_10"], 10)


    def test_specialist_correct_numbers_cannot_mask_wrong_manager_report(self):
        result = evaluate_live_result("finance", {
            "status": "COMPLETED",
            "specialist_reports": {
                "analyst": "Revenue 2160; variable cost 840; contribution 1320; operating result -2880."
            },
            "quality_review": "REVIEW STATUS: PASS\nISSUES: No material issues found.\nREQUIRED CORRECTIONS: None; calculations and evidence were checked.\nFINAL QUALITY SUMMARY: The report is internally consistent and remains advisory.",
            "quality_review_passed": True,
            "report": "Revenue 2160 GEL; variable cost 840 GEL; contribution 1320 GEL; operating result -2800 GEL before tax. Tax not provided.",
            "requires_ceo_approval": True,
            "execution_performed": False,
        })
        self.assertLess(result["score_out_of_10"], 10)
        failed = [item["name"] for item in result["checks"] if not item["passed"]]
        self.assertIn("calculation_accuracy", failed)

    def test_reviewer_pass_requires_substantive_sections(self):
        result = evaluate_live_result("finance", {
            "status": "COMPLETED",
            "specialist_reports": {"a": "x", "b": "y", "c": "z"},
            "quality_review": "REVIEW STATUS: PASS",
            "quality_review_passed": True,
            "report": "2160 840 1320 -2880 before tax; tax not provided.",
            "requires_ceo_approval": True,
        })
        failed = [item["name"] for item in result["checks"] if not item["passed"]]
        self.assertIn("manager_and_quality_gate", failed)


if __name__ == "__main__":
    unittest.main()
