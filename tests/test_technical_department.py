import unittest
from unittest.mock import patch

from technical_department import run_technical_department


PASS_REVIEW = (
    "REVIEW STATUS: PASS\n"
    "ISSUES: No material issues found.\n"
    "REQUIRED CORRECTIONS: None; evidence limits and approval boundaries are clear.\n"
    "FINAL QUALITY SUMMARY: The report is complete, evidence-aware, and advisory only."
)


class TechnicalDepartmentTests(unittest.TestCase):

    @patch("technical_department.ask_ai")
    @patch("technical_department.run_specialist")
    @patch("technical_department.run_technical_manager")
    def test_manager_synthesizes_specialists_and_reviewer_approves_final_report(
        self, manager_mock, specialist_mock, ask_ai_mock
    ):
        manager_mock.return_value = {
            "status": "PLAN_CREATED",
            "task_understanding": "Review backend API reliability.",
            "selected_specialists": [
                {
                    "specialist": "backend_developer",
                    "mission": "Review API error handling.",
                },
                {
                    "specialist": "qa_engineer",
                    "mission": "Propose focused regression tests.",
                },
            ],
            "execution_plan": ["Inspect supplied API evidence."],
            "testing_strategy": ["Run regression tests after CEO approval."],
        }
        specialist_mock.side_effect = [
            {
                "specialist": "backend_developer",
                "specialist_name": "Backend Developer",
                "status": "COMPLETED",
                "report": "The supplied notes describe API error handling.",
            },
            {
                "specialist": "qa_engineer",
                "specialist_name": "QA Engineer",
                "status": "COMPLETED",
                "report": "Recommend unit and integration tests.",
            },
        ]
        ask_ai_mock.side_effect = [
            "EXECUTIVE SUMMARY\nThe supplied API notes were reviewed.\nTECHNICAL RECOMMENDATIONS\nAdd regression coverage.",
            PASS_REVIEW,
        ]

        result = run_technical_department(
            "Review the backend API.",
            context={"source_code": "NOT PROVIDED", "test_logs": "NOT PROVIDED"},
        )

        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(specialist_mock.call_count, 2)
        self.assertEqual(ask_ai_mock.call_count, 2)
        self.assertIn("MANAGER SYNTHESIS:", result["report"])
        self.assertIn("The supplied API notes were reviewed.", result["report"])
        self.assertIn("Backend Developer — COMPLETED:", result["report"])
        self.assertIn("No tests were executed", result["report"])
        self.assertIn("Missing or unavailable inputs: source_code, test_logs", result["report"])
        self.assertTrue(result["quality_review_passed"])
        self.assertIn("REVIEW STATUS: PASS", result["quality_review"])
        self.assertTrue(result["requires_ceo_approval"])
        self.assertFalse(result["execution_performed"])
        self.assertFalse(result["code_modified"])
        self.assertFalse(result["tests_executed"])
        self.assertFalse(result["execution_authorized"])

    @patch("technical_department.ask_ai")
    @patch("technical_department.run_specialist")
    @patch("technical_department.run_technical_manager")
    def test_manager_and_reviewer_receive_all_technical_evidence(
        self, manager_mock, specialist_mock, ask_ai_mock
    ):
        mission = "Review the supplied order-processing API for reliability."
        manager_plan = {
            "status": "PLAN_CREATED",
            "task_understanding": "Check API reliability using supplied evidence.",
            "selected_specialists": [
                {"specialist": "backend_developer", "mission": "Inspect API error handling."},
                {"specialist": "qa_engineer", "mission": "Identify regression test gaps."},
            ],
            "execution_plan": ["Inspect the supplied API evidence."],
            "testing_strategy": ["Propose tests; do not execute them."],
        }
        specialist_results = [
            {
                "specialist": "backend_developer",
                "specialist_name": "Backend Developer",
                "status": "COMPLETED",
                "report": "BACKEND EVIDENCE: Retry behavior is not documented.",
            },
            {
                "specialist": "qa_engineer",
                "specialist_name": "QA Engineer",
                "status": "COMPLETED",
                "report": "QA EVIDENCE: No failure-mode test cases were supplied.",
            },
        ]
        manager_draft = (
            "EXECUTIVE SUMMARY\\nThe API review is limited to supplied material.\\n"
            "TECHNICAL RECOMMENDATIONS\\nDocument retry behavior."
        )
        manager_mock.return_value = manager_plan
        specialist_mock.side_effect = specialist_results
        ask_ai_mock.side_effect = [manager_draft, PASS_REVIEW]

        result = run_technical_department(
            mission,
            context={"source_code": "API SOURCE NOT PROVIDED", "ticket": "INC-204"}
        )

        manager_prompt = ask_ai_mock.call_args_list[0].args[1]
        reviewer_prompt = ask_ai_mock.call_args_list[1].args[1]

        for evidence in (
            "BACKEND EVIDENCE: Retry behavior is not documented.",
            "QA EVIDENCE: No failure-mode test cases were supplied.",
            "PLAN_CREATED",
            "INC-204",
        ):
            with self.subTest(evidence=evidence):
                self.assertIn(evidence, manager_prompt)
                self.assertIn(evidence, reviewer_prompt)

        self.assertIn(mission, manager_prompt)
        self.assertIn(mission, reviewer_prompt)
        self.assertIn(manager_draft, reviewer_prompt)
        self.assertIn("No tests were executed", reviewer_prompt)
        self.assertEqual(result["status"], "COMPLETED")
        self.assertTrue(result["quality_review_passed"])
        self.assertFalse(result["code_modified"])
        self.assertFalse(result["tests_executed"])
        self.assertFalse(result["execution_authorized"])

    def test_reviewer_requires_distinct_populated_sections(self):
        from technical_department import _review_is_substantive

        invalid_reviews = [
            (
                "REVIEW STATUS: PASS\\nISSUES:\\nREQUIRED CORRECTIONS:\\n"
                "FINAL QUALITY SUMMARY: Evidence and execution limits are represented correctly."
            ),
            (
                "REVIEW STATUS: PASS\\nThe reviewer mentioned issues, required corrections, "
                "and final quality summary without structured findings."
            ),
            (
                "REVIEW STATUS: PASS\\nISSUES: None.\\nREQUIRED CORRECTIONS: None.\\n"
                "FINAL QUALITY SUMMARY: Looks good."
            ),
            (
                "REVIEW STATUS: PASS\\nISSUES: None.\\nISSUES: Duplicate heading.\\n"
                "REQUIRED CORRECTIONS: None.\\n"
                "FINAL QUALITY SUMMARY: Evidence and execution limits are represented correctly."
            ),
            (
                "REVIEW STATUS: NEEDS_REVISION\\nISSUES: Unsupported claim.\\n"
                "REQUIRED CORRECTIONS: Correct it.\\n"
                "FINAL QUALITY SUMMARY: Evidence and execution limits are represented correctly."
            ),
        ]

        for review in invalid_reviews:
            with self.subTest(review=review):
                self.assertFalse(_review_is_substantive(review))

        self.assertTrue(_review_is_substantive(PASS_REVIEW))

    @patch("technical_department.ask_ai")
    @patch("technical_department.run_specialist")
    @patch("technical_department.run_technical_manager")
    def test_reviewer_rejection_blocks_final_report(
        self, manager_mock, specialist_mock, ask_ai_mock
    ):
        manager_mock.return_value = {
            "status": "PLAN_CREATED",
            "selected_specialists": [
                {"specialist": "qa_engineer", "mission": "Review test coverage."}
            ],
            "execution_plan": ["Review supplied test information."],
            "testing_strategy": ["Propose regression tests."],
        }
        specialist_mock.return_value = {
            "specialist": "qa_engineer",
            "status": "COMPLETED",
            "report": "Test coverage review.",
        }
        ask_ai_mock.side_effect = [
            "Draft report with an unsupported claim.",
            "REVIEW STATUS: NEEDS_REVISION\nISSUES: Unsupported claim remains.",
        ]

        result = run_technical_department("Review test coverage.")

        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["report"], "")
        self.assertIn("draft_report", result)
        self.assertIn("quality_review", result)
        self.assertFalse(result["quality_review_passed"])
        self.assertFalse(result["execution_authorized"])

    @patch("technical_department.ask_ai")
    @patch("technical_department.run_specialist")
    @patch("technical_department.run_technical_manager")
    def test_reviewer_rubber_stamp_does_not_pass(
        self, manager_mock, specialist_mock, ask_ai_mock
    ):
        manager_mock.return_value = {
            "status": "PLAN_CREATED",
            "selected_specialists": [
                {"specialist": "qa_engineer", "mission": "Review tests."}
            ],
        }
        specialist_mock.return_value = {
            "specialist": "qa_engineer",
            "status": "COMPLETED",
            "report": "Reviewed the supplied test notes.",
        }
        ask_ai_mock.side_effect = [
            "Draft report.",
            "REVIEW STATUS: PASS",
        ]

        result = run_technical_department("Review tests.")

        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["report"], "")
        self.assertFalse(result["quality_review_passed"])

    @patch("technical_department.ask_ai")
    @patch("technical_department.run_specialist")
    @patch("technical_department.run_technical_manager")
    def test_specialist_failure_stops_manager_and_reviewer(
        self, manager_mock, specialist_mock, ask_ai_mock
    ):
        manager_mock.return_value = {
            "status": "PLAN_CREATED",
            "selected_specialists": [
                {"specialist": "backend_developer", "mission": "Review API."}
            ],
        }
        specialist_mock.return_value = {
            "specialist": "backend_developer",
            "status": "ERROR",
            "error": "Provider unavailable.",
        }

        result = run_technical_department("Review API.")

        ask_ai_mock.assert_not_called()
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["report"], "")
        self.assertEqual(result["summary"]["failed_specialists"], 1)

    @patch("technical_department.run_specialist")
    @patch("technical_department.run_technical_manager")
    def test_manager_review_required_does_not_run_specialists(
        self, manager_mock, specialist_mock
    ):
        manager_mock.return_value = {
            "status": "REVIEW_REQUIRED",
            "selected_specialists": [],
        }

        result = run_technical_department("Unclear technical task.")

        specialist_mock.assert_not_called()
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["report"], "")
        self.assertFalse(result["execution_authorized"])
        self.assertEqual(result["final_decision"], "CEO_APPROVAL_REQUIRED")

    @patch("technical_department.ask_ai")
    @patch("technical_department.run_specialist")
    @patch("technical_department.run_technical_manager")
    def test_report_generation_error_fails_closed(
        self, manager_mock, specialist_mock, ask_ai_mock
    ):
        manager_mock.return_value = {
            "status": "PLAN_CREATED",
            "selected_specialists": [
                {"specialist": "qa_engineer", "mission": "Review tests."}
            ],
        }
        specialist_mock.return_value = {
            "specialist": "qa_engineer",
            "status": "COMPLETED",
            "report": "Reviewed test plan.",
        }
        ask_ai_mock.side_effect = RuntimeError("Provider unavailable.")

        result = run_technical_department("Review tests.")

        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["report"], "")
        self.assertFalse(result["quality_review_passed"])
        self.assertFalse(result["execution_authorized"])

    @patch("technical_department.run_technical_manager")
    def test_empty_task_is_rejected(self, manager_mock):
        result = run_technical_department("   ")

        manager_mock.assert_not_called()
        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(result["report"], "")


if __name__ == "__main__":
    unittest.main()
