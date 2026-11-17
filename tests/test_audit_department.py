import unittest

from audit_agents import compliance_auditor, run_audit


class AuditDepartmentTests(unittest.TestCase):

    def _topic_check(self, task, concept, final_script):
        result = compliance_auditor(
            task,
            {
                "concept": concept,
                "edited_script": final_script,
            },
        )
        return next(
            check for check in result["checks"]
            if check["check"] == "Topic preservation"
        )

    def test_topic_preservation_accepts_the_actual_task_topic(self):
        check = self._topic_check(
            "Create a short video about the Library of Alexandria.",
            "EXACT TOPIC: Library of Alexandria\nVIDEO CONCEPT: A history explainer.",
            "VIDEO TITLE: The Library of Alexandria\nSCRIPT: The Library of Alexandria "
            "was a major center of learning in the ancient world.",
        )
        self.assertTrue(check["passed"], check["details"])

    def test_topic_preservation_rejects_a_changed_topic(self):
        check = self._topic_check(
            "Create a short video about the Library of Alexandria.",
            "EXACT TOPIC: The Great Fire of Rome\nVIDEO CONCEPT: A history explainer.",
            "VIDEO TITLE: The Great Fire of Rome\nSCRIPT: The Great Fire of Rome changed the city.",
        )
        self.assertFalse(check["passed"])

    def test_topic_preservation_fails_closed_when_exact_topic_is_missing(self):
        check = self._topic_check(
            "Create a short video about the Library of Alexandria.",
            "VIDEO CONCEPT: A history explainer.",
            "VIDEO TITLE: The Library of Alexandria\nSCRIPT: The Library of Alexandria was important.",
        )
        self.assertFalse(check["passed"])
        self.assertIn("EXACT TOPIC", check["details"])

    def test_audit_never_approves_publication_automatically(self):
        result = run_audit(
            "Review the media package.",
            {
                "department": "media",
                "status": "REVIEW_REQUIRED",
                "publication_approved": False,
                "research": {"sources": []},
                "specialists": ["Research Agent"],
                "edited_script": "",
                "fact_check": "",
            },
        )
        self.assertFalse(result["publication_approved"])
        self.assertEqual(result["final_decision"], "CEO_APPROVAL_REQUIRED")


if __name__ == "__main__":
    unittest.main()
