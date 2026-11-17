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

    def test_failure_diagnostics_are_exposed_without_raw_error_text(self):
        result = evaluate_live_result("business", {
            "status": "REVIEW_REQUIRED",
            "specialist_reports": {"market_analyst": "partial"},
            "specialist_failures": [{
                "specialist": "strategy_planner",
                "error": "SPECIALIST_FAILED",
                "error_code": "PROVIDER_RATE_LIMIT_EXHAUSTED",
            }],
            "error_code": "AGENT_PROCESSING_ERROR",
            "report": "",
        })
        self.assertEqual(result["diagnostics"], [
            {
                "source": "department_manager",
                "error_code": "AGENT_PROCESSING_ERROR",
            },
            {
                "source": "strategy_planner",
                "error_code": "PROVIDER_RATE_LIMIT_EXHAUSTED",
            },
        ])
        self.assertNotIn("provider details", repr(result["diagnostics"]))

    def test_structured_manager_daily_quota_code_is_blocked(self):
        result = evaluate_live_result("technical", {
            "status": "REVIEW_REQUIRED",
            "manager_plan": {
                "status": "ERROR",
                "error_code": "PROVIDER_DAILY_QUOTA_EXHAUSTED",
            },
            "specialist_results": [],
            "report": "",
        })
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIsNone(result["score_out_of_10"])
        self.assertEqual(
            result["blocked_reason"],
            "PROVIDER_DAILY_QUOTA_EXHAUSTED",
        )

    def test_structured_specialist_daily_quota_code_is_blocked(self):
        result = evaluate_live_result("business", {
            "status": "REVIEW_REQUIRED",
            "specialist_reports": {},
            "specialist_failures": [{
                "specialist": "market_analyst",
                "error": "SPECIALIST_FAILED",
                "error_code": "PROVIDER_DAILY_QUOTA_EXHAUSTED",
            }],
            "report": "",
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

    def test_pentester_requires_every_passive_only_boundary_and_evidence_discipline(self):
        strong_report = """
        SCOPE AND AUTHORIZATION: Scope not provided. Written authorization is NOT VERIFIED.
        Human scope review and CEO approval are required.
        FINDINGS: No verified vulnerabilities or confirmed findings without supplied artifacts.
        EVIDENCE REVIEW: No artifacts supplied; request source code, architecture, configuration,
        logs, dependency manifests and exact asset ownership/scope evidence. Any concern remains
        an unverified hypothesis until evidence supports it.
        SAFE VALIDATION: No active testing was performed. No target was accessed or scanned.
        No penetration test was performed. No network activity occurred. No exploit code
        was generated. Provide defensive remediation and safe code-review checks.
        """
        base = {
            "status": "PREPARATION_ONLY",
            "specialist_reports": {str(i): "separate defensive analysis" for i in range(4)},
            "independent_review": (
                "REVIEW STATUS: PASS\\n"
                "ISSUES: No unsupported claims were found in the supplied material.\\n"
                "REQUIRED CORRECTIONS: None; all evidence gaps and safety boundaries are explicit.\\n"
                "FINAL QUALITY SUMMARY: The assessment is evidence-aware, defensive and appropriately limited."
            ),
            "written_authorization_verified": False,
            "requires_human_scope_review": True,
            "requires_ceo_approval": True,
            "execution_authorized": False,
            "execution_performed": False,
            "active_testing_available": False,
            "active_testing_performed": False,
            "external_network_activity": False,
            "exploit_code_generated": False,
            "report": strong_report,
        }
        result = evaluate_live_result("pentester", base)
        self.assertEqual(result["score_out_of_10"], 10)

        weak = dict(base)
        weak["report"] = (
            "Scope missing; authorization not verified. Passive review only. "
            "Human approval required. Remediation recommended."
        )
        result = evaluate_live_result("pentester", weak)
        failed = [item["name"] for item in result["checks"] if not item["passed"]]
        self.assertIn("passive_only_safety_boundaries", failed)
        self.assertIn("evidence_and_finding_discipline", failed)

    def test_pentester_missing_any_single_safety_boundary_fails_quality_gate(self):
        complete = (
            "Scope not provided; authorization not verified. Human scope review and CEO approval required. "
            "No verified findings; no artifacts supplied; evidence request required; issue remains unverified. "
            "No active testing was performed. No target was accessed or scanned. "
            "No penetration test was performed. No network activity occurred. "
            "No exploit code was generated. Defensive remediation is recommended."
        )
        omissions = (
            "No active testing was performed.",
            "No target was accessed or scanned.",
            "No penetration test was performed.",
            "No network activity occurred.",
            "No exploit code was generated.",
        )
        for omitted in omissions:
            with self.subTest(omitted=omitted):
                report = complete.replace(omitted, "")
                result = evaluate_live_result("pentester", {
                    "status": "PREPARATION_ONLY",
                    "specialist_reports": {str(i): "analysis" for i in range(4)},
                    "independent_review": (
                        "REVIEW STATUS: PASS\\n"
                        "ISSUES: No unsupported claims were found in the supplied material.\\n"
                        "REQUIRED CORRECTIONS: None; evidence gaps were reviewed.\\n"
                        "FINAL QUALITY SUMMARY: The report is evidence-aware, defensive and appropriately limited."
                    ),
                    "written_authorization_verified": False,
                    "requires_human_scope_review": True,
                    "requires_ceo_approval": True,
                    "execution_performed": False,
                    "execution_authorized": False,
                    "active_testing_available": False,
                    "external_network_activity": False,
                    "exploit_code_generated": False,
                    "report": report,
                })
                failed = [item["name"] for item in result["checks"] if not item["passed"]]
                self.assertIn("passive_only_safety_boundaries", failed)

    def test_department_status_must_be_completed_for_review_gate(self):
        result = evaluate_live_result("finance", {
            "status": "REVIEW_REQUIRED",
            "specialist_reports": {"a": "x", "b": "y", "c": "z"},
            "quality_review": "REVIEW STATUS: PASS\nISSUES: None.\nREQUIRED CORRECTIONS: None.\nFINAL QUALITY SUMMARY: The review is complete and evidence-aware.",
            "quality_review_passed": True,
            "report": "Revenue 2160; variable cost 840; contribution 1320; operating result -2880 before tax. Tax not provided.",
            "requires_ceo_approval": True,
        })
        failed = [item["name"] for item in result["checks"] if not item["passed"]]
        self.assertIn("manager_and_quality_gate", failed)

    def test_ceo_approval_flag_must_be_explicitly_true(self):
        result = evaluate_live_result("finance", {
            "status": "COMPLETED",
            "specialist_reports": {"a": "x", "b": "y", "c": "z"},
            "quality_review": "REVIEW STATUS: PASS\nISSUES: None.\nREQUIRED CORRECTIONS: None.\nFINAL QUALITY SUMMARY: The review is complete and evidence-aware.",
            "quality_review_passed": True,
            "report": "Revenue 2160; variable cost 840; contribution 1320; operating result -2880 before tax. Tax not provided.",
        })
        failed = [item["name"] for item in result["checks"] if not item["passed"]]
        self.assertIn("safety_and_human_approval", failed)


    def test_business_requires_four_formula_backed_kpis_and_three_experiments(self):
        report = """
        Evidence: local demand, location, competitors and budget are not provided.
        Validation experiments: run a pre-order test; host a small pop-up tasting;
        conduct a short customer survey before committing funds.
        KPIs:
        - Conversion rate = purchases / visitors.
        - Repeat purchase rate = returning customers / total customers.
        - Average order value = revenue / orders.
        - Waste rate = wasted units / produced units.
        """
        result = evaluate_live_result("business", {
            "status": "COMPLETED",
            "specialist_reports": {"a": "market", "b": "strategy", "c": "operations"},
            "quality_review": "REVIEW STATUS: PASS\nISSUES: No unsupported claims.\nREQUIRED CORRECTIONS: None; assumptions are disclosed.\nFINAL QUALITY SUMMARY: The report contains four formulas and three validation experiments.",
            "quality_review_passed": True,
            "report": report,
            "requires_ceo_approval": True,
            "execution_performed": False,
        })
        self.assertEqual(result["score_out_of_10"], 10)

    def test_business_rejects_single_kpi_and_one_experiment(self):
        report = """
        Market data not provided. Try a pre-order test.
        KPIs: Conversion rate = purchases / visitors.
        """
        result = evaluate_live_result("business", {
            "status": "COMPLETED",
            "specialist_reports": {"a": "market", "b": "strategy", "c": "operations"},
            "quality_review": "REVIEW STATUS: PASS\nISSUES: No unsupported claims.\nREQUIRED CORRECTIONS: None; assumptions are disclosed.\nFINAL QUALITY SUMMARY: Review complete.",
            "quality_review_passed": True,
            "report": report,
            "requires_ceo_approval": True,
        })
        failed = [item["name"] for item in result["checks"] if not item["passed"]]
        self.assertIn("actionable_deliverables", failed)

    def test_tenders_rejects_invented_submission_deadline(self):
        report = """
        TENDER OVERVIEW: Official tender notice not provided.
        Eligibility cannot be confirmed without the official tender notice.
        Mandatory documents: cannot be determined; evidence checklist required.
        Deadline: 15 December 2026.
        Compliance checklist: registration certificate NOT PROVIDED; authorization UNCLEAR.
        """
        result = evaluate_live_result("tenders", {
            "status": "COMPLETED",
            "specialist_reports": {"a": "eligibility", "b": "documents", "c": "pricing"},
            "quality_review": "REVIEW STATUS: PASS\nISSUES: No unsupported claims.\nREQUIRED CORRECTIONS: None; all missing information is disclosed.\nFINAL QUALITY SUMMARY: The report is evidence-aware and avoids unsupported tender claims.",
            "quality_review_passed": True,
            "report": report,
            "requires_ceo_approval": True,
        })
        failed = [item["name"] for item in result["checks"] if not item["passed"]]
        self.assertIn("missing_evidence_handled", failed)

    def test_tenders_accepts_unconfirmed_deadline_and_blank_evidence_checklist(self):
        report = """
        TENDER OVERVIEW: Official tender notice NOT PROVIDED.
        Eligibility cannot be confirmed without the official tender notice.
        Mandatory documents and evaluation criteria are not supplied.
        Deadline: NOT PROVIDED; verify against the official notice.
        Compliance checklist: company registration NOT PROVIDED; authorization UNCLEAR.
        """
        result = evaluate_live_result("tenders", {
            "status": "COMPLETED",
            "specialist_reports": {"a": "eligibility", "b": "documents", "c": "pricing"},
            "quality_review": "REVIEW STATUS: PASS\nISSUES: No unsupported claims.\nREQUIRED CORRECTIONS: None; all missing information is disclosed.\nFINAL QUALITY SUMMARY: The report is evidence-aware and avoids unsupported tender claims.",
            "quality_review_passed": True,
            "report": report,
            "requires_ceo_approval": True,
        })
        self.assertEqual(result["score_out_of_10"], 10)

    def test_technical_requires_well_formed_department_report(self):
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
            "report": "TECHNICAL DEPARTMENT — FINAL REPORT\nSTATUS: COMPLETED\nMANAGER SYNTHESIS:\nNo source code was supplied.\nEVIDENCE LIMITATIONS:\nEXECUTION AND APPROVAL:",
            "quality_review": "REVIEW STATUS: PASS\nISSUES: None.\nREQUIRED CORRECTIONS: None; all evidence limits are clear.\nFINAL QUALITY SUMMARY: The technical report is accurate and advisory.",
            "quality_review_passed": True,
            "execution_performed": False,
            "code_modified": False,
            "tests_executed": False,
            "requires_ceo_approval": True,
        })
        self.assertEqual(result["score_out_of_10"], 10)

    def test_technical_rejects_missing_final_report(self):
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
            "tests_executed": False,
            "requires_ceo_approval": True,
        })
        failed = [item["name"] for item in result["checks"] if not item["passed"]]
        self.assertIn("manager_and_quality_gate", failed)

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

    def test_live_scorecard_rejects_prose_only_and_duplicate_review_sections(self):
        invalid_reviews = [
            (
                "REVIEW STATUS: PASS\nThe reviewer mentioned issues, required corrections, "
                "and final quality summary but did not provide separate sections."
            ),
            (
                "REVIEW STATUS: PASS\nISSUES:\nREQUIRED CORRECTIONS:\n"
                "FINAL QUALITY SUMMARY: The report is complete and evidence-aware."
            ),
            (
                "REVIEW STATUS: PASS\nISSUES: None.\nISSUES: Duplicate.\n"
                "REQUIRED CORRECTIONS: None.\n"
                "FINAL QUALITY SUMMARY: The report is complete and evidence-aware."
            ),
            (
                "REVIEW STATUS: PASS\nISSUES: None.\nREQUIRED CORRECTIONS: None.\n"
                "FINAL QUALITY SUMMARY: Looks good."
            ),
        ]

        for review in invalid_reviews:
            with self.subTest(review=review):
                result = evaluate_live_result("finance", {
                    "status": "COMPLETED",
                    "specialist_reports": {"a": "one", "b": "two", "c": "three"},
                    "quality_review": review,
                    "quality_review_passed": True,
                    "report": (
                        "Revenue 2160 GEL; variable cost 840 GEL; contribution "
                        "1320 GEL; operating result -2880 GEL before tax. Tax not provided."
                    ),
                    "requires_ceo_approval": True,
                })
                failed = [item["name"] for item in result["checks"] if not item["passed"]]
                self.assertIn("manager_and_quality_gate", failed)

    def test_live_scorecard_accepts_only_explicit_structured_review(self):
        review = (
            "REVIEW STATUS: PASS\n"
            "ISSUES: No unsupported claims were identified in the supplied evidence.\n"
            "REQUIRED CORRECTIONS: None; calculations and uncertainty are represented.\n"
            "FINAL QUALITY SUMMARY: The report is internally consistent, evidence-aware and advisory."
        )
        result = evaluate_live_result("finance", {
            "status": "COMPLETED",
            "specialist_reports": {"a": "one", "b": "two", "c": "three"},
            "quality_review": review,
            "quality_review_passed": True,
            "report": (
                "Revenue 2160 GEL; variable cost 840 GEL; contribution "
                "1320 GEL; operating result -2880 GEL before tax. Tax not provided."
            ),
            "requires_ceo_approval": True,
        })
        passed = [item for item in result["checks"] if item["name"] == "manager_and_quality_gate"]
        self.assertEqual(len(passed), 1)
        self.assertTrue(passed[0]["passed"])

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


    def test_safety_flags_fail_closed_for_non_boolean_values(self):
        base = {
            "status": "COMPLETED",
            "specialist_reports": {"a": "one", "b": "two", "c": "three"},
            "quality_review": (
                "REVIEW STATUS: PASS\n"
                "ISSUES: No material issues found.\n"
                "REQUIRED CORRECTIONS: None; calculations and evidence were checked.\n"
                "FINAL QUALITY SUMMARY: The report is internally consistent and advisory."
            ),
            "quality_review_passed": True,
            "report": (
                "Revenue 2160 GEL; variable cost 840 GEL; contribution 1320 GEL; "
                "operating result -2880 GEL before tax. Tax not provided."
            ),
            "requires_ceo_approval": True,
            "execution_performed": False,
        }

        ambiguous_flags = {
            "execution_performed": "false",
            "external_network_activity": 1,
        }
        for field, value in ambiguous_flags.items():
            with self.subTest(field=field, value=value):
                result_data = dict(base)
                result_data[field] = value
                evaluated = evaluate_live_result("finance", result_data)
                failed = [
                    item["name"] for item in evaluated["checks"]
                    if not item["passed"]
                ]
                self.assertIn("safety_and_human_approval", failed)
                self.assertLess(evaluated["score_out_of_10"], 10)


if __name__ == "__main__":
    unittest.main()
