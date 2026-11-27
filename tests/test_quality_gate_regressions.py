import unittest

from agent_quality_stress_test import (
    evaluate_live_result,
    _business_experiment_quality,
    _business_kpi_quality,
    _pentester_specialist_quality,
)
from department_quality import validate_technical_specialists
from department_agents import _missing_report_sections as missing_business_sections
from pentester_agents import _missing_report_sections as missing_pentester_sections


PASS_REVIEW = (
    "REVIEW STATUS: PASS\n"
    "ISSUES: No material issues found in the supplied evidence.\n"
    "REQUIRED CORRECTIONS: None; all calculations and evidence limits were checked.\n"
    "FINAL QUALITY SUMMARY: The report is internally consistent, complete, and advisory only."
)


class QualityGateRegressionTests(unittest.TestCase):

    def test_qa_report_with_test_suites_metrics_and_thresholds_meets_contract(self):
        result = validate_technical_specialists(
            {"selected_specialists": [{"specialist": "qa_engineer"}]},
            [{
                "specialist": "qa_engineer",
                "status": "COMPLETED",
                "report": (
                    "QA test plan: define test suites, performance metrics, "
                    "pass/fail thresholds, expected results, and missing test data."
                ),
            }],
        )
        self.assertEqual(result["status"], "PASS", result["issues"])

    def test_finance_reconciliation_uses_final_calculation_value_not_inputs(self):
        specialists = {
            "financial_analyst": (
                "Operating result before tax | 1,320 GEL contribution - "
                "4,200 GEL fixed costs = -2,880 GEL."
            ),
            "risk_controller": (
                "Operating result before tax: 1,320 - 4,200 = -2,880 GEL."
            ),
            "budget_planner": (
                "Operating result before tax: 1,320 - 4,200 = -2,880 GEL."
            ),
        }
        result = evaluate_live_result("finance", {
            "status": "COMPLETED",
            "specialist_reports": specialists,
            "quality_review": PASS_REVIEW,
            "quality_review_passed": True,
            "report": (
                "Revenue 2,160 GEL; variable cost 840 GEL; contribution "
                "1,320 GEL; operating result before tax -2,880 GEL. "
                "Taxes were not provided."
            ),
            "requires_ceo_approval": True,
            "execution_performed": False,
        })
        check = next(item for item in result["checks"] if item["name"] == "calculation_accuracy")
        self.assertTrue(check["passed"], check["detail"])

    def test_business_kpi_table_accepts_named_formulas_not_fixed_kpi_vocabulary(self):
        report = """
        ### KPIs
        | KPI | Formula | What it measures |
        |-----|---------|------------------|
        | Foot-Traffic Conversion Ratio | FCR = samples handed out / pass-by count | Capture |
        | Online Interest Score | OIS = likes + shares / total reach | Interest |
        | Sample-to-Purchase Intent Ratio | SPIR = buy statements / samples | Intent |
        | Cost-per-Unit Production | CPU = ingredient cost / sellable units | Cost |
        """
        passed, count = _business_kpi_quality(report)
        self.assertTrue(passed, count)
        self.assertEqual(count, 4)

    def test_business_numbered_experiments_are_counted_as_distinct_deliverables(self):
        report = """
        Experiment 1: conduct a foot-traffic count.
        Experiment 2: publish a menu mock-up and measure interest.
        Experiment 3: prepare a small home-kitchen batch and record unit cost.
        """
        passed, count = _business_experiment_quality(report)
        self.assertTrue(passed, count)
        self.assertEqual(count, 3)

    def test_pentester_equivalent_evidence_language_is_accepted(self):
        reports = {
            "scope_analyst": (
                "Scope not provided. Authorization not verified. Human scope review required. "
                "Asset inventory and trust boundaries remain unknown."
            ),
            "web_security": (
                "No artifacts supplied. No verified vulnerabilities. Potential issues are "
                "hypotheses and checklist items. Defensive remediation is recommended."
            ),
            "infrastructure_security": (
                "No architecture artifacts supplied. No verified infrastructure issues. "
                "Potential concerns remain hypotheses. Defensive hardening is recommended."
            ),
            "vulnerability_analyst": (
                "No CVEs, no scan reports, no proof-of-concept data. Therefore no vulnerability "
                "can be assigned a severity or confidence level. No CVE assigned. "
                "Confidence is unassessed. Remediation is recommended. Safe retest criteria "
                "must wait until evidence and authorization are reviewed."
            ),
        }
        passed, issues = _pentester_specialist_quality(reports)
        self.assertTrue(passed, issues)

    def test_business_required_heading_accepts_unicode_nonbreaking_hyphen(self):
        report = """
        EXECUTIVE SUMMARY
        BUSINESS CONTEXT
        ANALYSIS
        OPTIONS AND TRADE‑OFFS
        RISKS
        RECOMMENDATIONS
        KPIS
        MISSING INFORMATION
        """
        self.assertEqual(missing_business_sections("business", report), [])

    def test_pentester_required_headings_accept_unicode_dash_and_qualifier(self):
        report = """
        EXECUTIVE SUMMARY
        SCOPE AND AUTHORIZATION GAPS
        ASSET AND TRUST‑BOUNDARY SUMMARY
        THREAT MODEL (Preliminary)
        EVIDENCE REVIEW
        FINDINGS
        SEVERITY AND CONFIDENCE
        REMEDIATION PLAN
        SAFE VALIDATION PLAN
        REQUIRED HUMAN APPROVALS
        LIMITATIONS
        """
        self.assertEqual(missing_pentester_sections(report), [])

    def test_technical_live_scorecard_uses_actual_selected_specialist_count(self):
        manager_plan = {
            "status": "PLAN_CREATED",
            "selected_specialists": [
                {"specialist": "system_architect"},
                {"specialist": "code_reviewer"},
                {"specialist": "qa_engineer"},
            ],
            "execution_plan": ["Collect repository and architecture evidence."],
            "testing_strategy": ["Propose tests; do not execute them."],
        }
        specialist_results = [
            {
                "specialist": "system_architect",
                "status": "COMPLETED",
                "report": "Architecture components and dependencies are not provided; risks remain unknown.",
            },
            {
                "specialist": "code_reviewer",
                "status": "COMPLETED",
                "report": "Code review evidence and maintainability risks cannot be assessed without source files.",
            },
            {
                "specialist": "qa_engineer",
                "status": "COMPLETED",
                "report": "QA test coverage plan: test suites, performance metrics, pass/fail thresholds, and validation.",
            },
        ]
        report = (
            "TECHNICAL DEPARTMENT — FINAL REPORT\n"
            "STATUS: COMPLETED\n"
            "MANAGER SYNTHESIS:\nEvidence is not provided; no source code was inspected.\n"
            "EVIDENCE LIMITATIONS:\nNo source code was provided and no tests were executed.\n"
            "EXECUTION AND APPROVAL:\nNo code was modified; CEO approval is required.\n"
        )
        result = evaluate_live_result("technical", {
            "status": "COMPLETED",
            "manager_plan": manager_plan,
            "specialist_results": specialist_results,
            "quality_review": PASS_REVIEW,
            "quality_review_passed": True,
            "report": report,
            "code_modified": False,
            "tests_executed": False,
            "execution_performed": False,
            "requires_ceo_approval": True,
        })
        check = next(item for item in result["checks"] if item["name"] == "specialist_contribution")
        self.assertTrue(check["passed"], check["detail"])


if __name__ == "__main__":
    unittest.main()
