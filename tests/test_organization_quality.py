import unittest

from organization_quality import audit_organization_task


def _core_result(department):
    result = {
        "department": department,
        "status": "COMPLETED",
        "report": f"{department} advisory report.",
        "requires_ceo_approval": True,
        "execution_authorized": False,
        "execution_performed": False,
        "specialist_quality_validation": {"status": "PASS", "issues": []},
        "quality_review_passed": True,
    }
    if department == "pentester":
        result.update({
            "status": "PREPARATION_ONLY",
            "evidence_validation": {"status": "UNVERIFIED", "gaps": []},
            "written_authorization_verified": False,
            "requires_human_scope_review": True,
            "active_testing_available": False,
            "active_testing_performed": False,
            "external_network_activity": False,
            "exploit_code_generated": False,
        })
    return result


def _media_result():
    return {
        "department": "media",
        "status": "REVIEW_REQUIRED",
        "edited_script": "Final edited narration and scenes.",
        "fact_check": "VERIFIED: claims have supporting source review.",
        "validation": {"word_count_passed": True, "visual_scene_count_passed": True},
        "publication_approved": False,
    }


def _audit_result():
    return {
        "department": "audit",
        "status": "PASSED_WITH_LIMITATIONS",
        "summary": {"total_checks": 12, "passed_checks": 12, "failed_checks": 0},
        "failed_checks": [],
        "publication_approved": False,
        "final_decision": "CEO_APPROVAL_REQUIRED",
    }


class OrganizationQualityTests(unittest.TestCase):

    def test_all_departments_pass_structural_audit_but_require_human_alignment_review(self):
        departments = [
            "media", "audit", "finance", "business", "tenders",
            "technical", "pentester",
        ]
        results = [
            _media_result(),
            _audit_result(),
            _core_result("finance"),
            _core_result("business"),
            _core_result("tenders"),
            _core_result("technical"),
            _core_result("pentester"),
        ]

        audit = audit_organization_task(
            "Prepare the requested deliverables and report evidence gaps.",
            departments,
            results,
        )

        self.assertEqual(audit["status"], "PASS", audit["issues"])
        self.assertEqual(audit["content_alignment_status"], "HUMAN_REVIEW_REQUIRED")
        self.assertTrue(audit["human_review_required"])
        self.assertEqual(len(audit["department_checks"]), len(departments))

    def test_missing_department_result_blocks_organization_pass(self):
        audit = audit_organization_task(
            "Review finance and business.",
            ["finance", "business"],
            [_core_result("finance")],
        )

        self.assertEqual(audit["status"], "REVIEW_REQUIRED")
        self.assertTrue(any("business: expected department result is missing" in issue
                            for issue in audit["issues"]))

    def test_true_execution_flag_is_rejected(self):
        result = _core_result("technical")
        result["execution_performed"] = True
        audit = audit_organization_task("Review code.", ["technical"], [result])

        self.assertEqual(audit["status"], "REVIEW_REQUIRED")
        self.assertTrue(any("execution_performed must be explicitly false" in issue
                            for issue in audit["issues"]))

    def test_missing_specialist_gate_blocks_completed_department(self):
        result = _core_result("finance")
        result.pop("specialist_quality_validation")
        audit = audit_organization_task("Review budget.", ["finance"], [result])

        self.assertEqual(audit["status"], "REVIEW_REQUIRED")
        self.assertTrue(any("independent specialist quality validation did not pass" in issue
                            for issue in audit["issues"]))

    def test_media_requires_independent_audit_department(self):
        audit = audit_organization_task(
            "Create a video.",
            ["media"],
            [_media_result()],
        )

        self.assertEqual(audit["status"], "REVIEW_REQUIRED")
        self.assertTrue(any("independent Audit department was not included" in issue
                            for issue in audit["issues"]))


    def test_general_audit_can_review_non_media_departments(self):
        audit = audit_organization_task(
            "Review the technical delivery.",
            ["technical", "audit"],
            [_core_result("technical"), _audit_result()],
        )

        self.assertEqual(audit["status"], "PASS", audit["issues"])
        self.assertEqual(len(audit["department_checks"]), 2)


if __name__ == "__main__":
    unittest.main()
