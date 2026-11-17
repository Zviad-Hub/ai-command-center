import unittest
from unittest.mock import patch

from director import detect_departments, route_task


class DirectorRoutingTests(unittest.TestCase):

    def test_code_review_routes_only_to_technical(self):
        departments = detect_departments("შეამოწმე ეს კოდი და იპოვე შეცდომები")
        self.assertEqual(departments, ["technical"])

    def test_explicit_audit_routes_to_audit(self):
        departments = detect_departments("ჩაატარე დამოუკიდებელი აუდიტი")
        self.assertEqual(departments, ["audit"])

    def test_media_task_also_routes_to_audit(self):
        departments = detect_departments("Create a YouTube video script")
        self.assertEqual(departments, ["media", "audit"])

    def test_explicitly_excluded_media_is_not_routed(self):
        departments = detect_departments(
            "Finance Business Technical Pentester Audit. Media არ გაუშვა."
        )
        self.assertNotIn("media", departments)
        self.assertEqual(
            set(departments),
            {"finance", "business", "technical", "pentester", "audit"},
        )

    def test_business_department_name_routes_to_business(self):
        self.assertEqual(detect_departments("Business"), ["business"])

    @patch("director.ai_route_task")
    def test_keyword_routing_does_not_call_ai(self, ai_route_mock):
        result = route_task("შეამოწმე ეს კოდი")
        ai_route_mock.assert_not_called()
        self.assertEqual(result["departments"], ["technical"])
        self.assertEqual(result["routing_method"], "RULE_BASED")


if __name__ == "__main__":
    unittest.main()
