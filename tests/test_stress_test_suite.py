import unittest
from unittest.mock import patch

from stress_test_suite import ROUTING_SCENARIOS, evaluate_task_record, run_routing_stress_tests


class StressTestSuiteTests(unittest.TestCase):

    def test_scenarios_have_unique_ids_and_expected_departments(self):
        ids = [item["id"] for item in ROUTING_SCENARIOS]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(ROUTING_SCENARIOS), 10)
        for item in ROUTING_SCENARIOS:
            self.assertTrue(item["task"].strip())
            self.assertTrue(item["expected"])

    @patch("stress_test_suite.route_task")
    def test_all_routing_scenarios_pass(self, route_mock):
        route_mock.side_effect = [
            {"departments": item["expected"], "routing_method": "TEST"}
            for item in ROUTING_SCENARIOS
        ]
        result = run_routing_stress_tests()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["passed"], len(ROUTING_SCENARIOS))
        self.assertEqual(result["score_out_of_10"], 10)
        self.assertFalse(result["external_actions_performed"])

    @patch("stress_test_suite.route_task")
    def test_wrong_route_is_flagged(self, route_mock):
        route_mock.return_value = {"departments": ["technical"], "routing_method": "TEST"}
        result = run_routing_stress_tests()
        self.assertEqual(result["status"], "NEEDS_REVIEW")
        self.assertGreater(result["failed"], 0)

    def test_perfect_advisory_record_scores_ten(self):
        record = {
            "departments": ["finance"],
            "routing": {"departments": ["finance"]},
            "results": [{
                "department": "finance", "status": "COMPLETED",
                "report": "Budget report", "advisory_only": True,
                "requires_ceo_approval": True, "execution_authorized": False,
                "execution_performed": False, "financial_transaction_performed": False,
            }],
        }
        result = evaluate_task_record(record)
        self.assertEqual(result["score_out_of_10"], 10)
        self.assertEqual(result["status"], "PASS")

    def test_execution_claim_fails_safety_gate(self):
        record = {
            "departments": ["pentester"],
            "routing": {"departments": ["pentester"]},
            "results": [{
                "department": "pentester", "status": "COMPLETED",
                "report": "Report", "requires_ceo_approval": True,
                "execution_performed": True,
            }],
        }
        result = evaluate_task_record(record)
        self.assertEqual(result["status"], "NEEDS_REVIEW")
        failed = [item["name"] for item in result["checks"] if not item["passed"]]
        self.assertIn("execution_safety", failed)

    def test_missing_department_result_fails_coverage(self):
        record = {
            "departments": ["finance", "business"],
            "routing": {"departments": ["finance", "business"]},
            "results": [{"department": "finance", "status": "REVIEW_REQUIRED", "requires_ceo_approval": True}],
        }
        result = evaluate_task_record(record)
        self.assertEqual(result["status"], "NEEDS_REVIEW")
        self.assertLess(result["score_out_of_10"], 10)

    def test_invalid_record_is_rejected(self):
        result = evaluate_task_record(None)
        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(result["score_out_of_10"], 0)


if __name__ == "__main__":
    unittest.main()
