import unittest

from agent_performance_scorecard import build_agent_performance_scorecard


class AgentPerformanceScorecardTests(unittest.TestCase):
    def test_reports_gate_outcomes_without_claiming_factual_accuracy(self):
        results = [{
            "department": "finance",
            "status": "COMPLETED",
            "report": "A financial report.",
            "specialist_results": [
                {"status": "COMPLETED"},
                {"status": "ERROR"},
                {"status": "NOT_RUN"},
            ],
            "specialist_quality_validation": {"status": "PASS"},
            "quality_review_passed": True,
            "requires_ceo_approval": True,
            "execution_authorized": False,
            "execution_performed": False,
        }]
        organization = {
            "status": "PASS",
            "department_checks": [{
                "department": "finance", "status": "PASS", "issues": []
            }],
        }
        semantic = {"status": "PASS"}

        scorecard = build_agent_performance_scorecard(results, organization, semantic)

        self.assertEqual(scorecard["status"], "READY_FOR_HUMAN_REVIEW")
        self.assertEqual(scorecard["departments_structurally_passed"], 1)
        self.assertEqual(scorecard["departments"][0]["specialists"], {
            "completed": 1, "failed": 1, "not_run": 1, "selected": 3
        })
        self.assertTrue(scorecard["human_review_required"])
        self.assertIn("does not measure factual accuracy", " ".join(scorecard["limitations"]))

    def test_missing_or_failed_gates_fail_closed(self):
        results = [{
            "department": "pentester",
            "status": "PREPARATION_ONLY",
            "report": "Passive review only.",
            "specialist_reports": {"scope_analyst": "No scope supplied."},
            "evidence_validation": {"status": "UNVERIFIED"},
            "quality_review_passed": False,
            "written_authorization_verified": False,
            "requires_human_scope_review": True,
            "execution_authorized": False,
            "execution_performed": False,
        }]
        organization = {
            "status": "REVIEW_REQUIRED",
            "department_checks": [{
                "department": "pentester",
                "status": "REVIEW_REQUIRED",
                "issues": ["independent security review did not pass"],
            }],
        }

        scorecard = build_agent_performance_scorecard(
            results, organization, {"status": "UNAVAILABLE"}
        )

        self.assertEqual(scorecard["status"], "REVIEW_REQUIRED")
        self.assertEqual(scorecard["departments_review_required"], 1)
        self.assertEqual(scorecard["departments"][0]["gates"]["independent_review"], "FAIL")
        self.assertEqual(scorecard["semantic_audit_status"], "UNAVAILABLE")

    def test_duplicate_or_absent_detail_is_not_invented(self):
        scorecard = build_agent_performance_scorecard(
            [{"department": "technical", "status": "ERROR"}],
            {"status": "REVIEW_REQUIRED", "department_checks": []},
            {"status": "NOT_RUN"},
        )
        row = scorecard["departments"][0]
        self.assertIsNone(row["specialists"])
        self.assertFalse(row["report_present"])
        self.assertEqual(row["gates"]["organization_contract"], "MISSING")
        self.assertEqual(scorecard["status"], "REVIEW_REQUIRED")


if __name__ == "__main__":
    unittest.main()
