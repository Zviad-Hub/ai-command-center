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

    def test_technical_only_prompt_excludes_all_other_departments(self):
        task = (
            "TECHNICAL DEPARTMENT — CONTROLLED LIVE QUALITY TEST. "
            "Analyze the AI Command Center provider reliability and fallback architecture. "
            "Restrictions: Do not run Media, Audit, Pentester, Finance, Business or Tenders. "
            "Do not modify files, execute commands or perform external actions."
        )
        self.assertEqual(detect_departments(task), ["technical"])

    def test_exclusions_do_not_hide_positive_department_outside_restriction_clause(self):
        task = (
            "Review the finance budget. "
            "Restrictions: Do not run Media, Audit, Pentester, Business or Tenders."
        )
        self.assertEqual(detect_departments(task), ["finance"])

    @patch("director.ai_route_task")
    def test_keyword_routing_does_not_call_ai(self, ai_route_mock):
        result = route_task("შეამოწმე ეს კოდი")
        ai_route_mock.assert_not_called()
        self.assertEqual(result["departments"], ["technical"])
        self.assertEqual(result["routing_method"], "RULE_BASED")


    def test_georgian_exclusion_before_department_names(self):
        departments = detect_departments(
            "მომეცი მოკლე პასუხი ქართულად: დაადასტურე, რომ AI პროვაიდერი მუშაობს. "
            "არ გაუშვა Media და Pentester."
        )
        self.assertNotIn("media", departments)
        self.assertNotIn("pentester", departments)

    def test_georgian_exclusion_after_department_names(self):
        departments = detect_departments("Media და Pentester არ გაუშვა")
        self.assertNotIn("media", departments)
        self.assertNotIn("pentester", departments)

    def test_english_exclusions_override_keyword_matches(self):
        departments = detect_departments("Media and Pentester: do not run either.")
        self.assertNotIn("media", departments)
        self.assertNotIn("pentester", departments)



if __name__ == "__main__":
    unittest.main()
