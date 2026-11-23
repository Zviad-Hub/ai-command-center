import unittest

from report_context import bounded_text, build_bounded_report_context


class ReportContextTests(unittest.TestCase):
    def test_bounded_text_preserves_short_text(self):
        self.assertEqual(bounded_text("short report", 100), "short report")

    def test_bounded_text_keeps_start_and_end_when_truncated(self):
        source = "START " + ("middle " * 100) + " END"
        result = bounded_text(source, 80)
        self.assertLessEqual(len(result), 80)
        self.assertTrue(result.startswith("START"))
        self.assertTrue(result.endswith("END"))
        self.assertIn("TRIMMED", result)

    def test_report_context_obeys_total_budget_and_keeps_labels(self):
        result = build_bounded_report_context(
            [("Analyst A", "A" * 5000), ("Analyst B", "B" * 5000)],
            max_chars_per_report=1000,
            max_total_chars=2200,
        )
        self.assertLessEqual(len(result), 2200)
        self.assertIn("Analyst A", result)
        self.assertIn("Analyst B", result)

    def test_report_context_notes_omitted_reports(self):
        result = build_bounded_report_context(
            [(f"Analyst {i}", "x" * 500) for i in range(10)],
            max_chars_per_report=500,
            max_total_chars=1300,
        )
        self.assertIn("additional specialist report(s) omitted", result)


if __name__ == "__main__":
    unittest.main()
