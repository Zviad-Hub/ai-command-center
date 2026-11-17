import unittest

from error_diagnostics import safe_error_code
from department_agents import _review_is_substantive as department_review
from pentester_agents import _review_is_substantive as pentester_review
from technical_department import _review_is_substantive as technical_review


VALID_REVIEW_WITH_STANDALONE_HEADINGS = """REVIEW STATUS: PASS

ISSUES
- None identified in the supplied evidence.

REQUIRED CORRECTIONS
- No corrections are required before the advisory report is reviewed.

FINAL QUALITY SUMMARY
The review checked the available evidence, uncertainty, safety boundaries, and required deliverables. The report is suitable for human review.
"""


class SafeErrorDiagnosticsTests(unittest.TestCase):
    def test_provider_rate_limit_is_classified_without_message_disclosure(self):
        error = RuntimeError("Groq rate limit exceeded after all retries; provider details were withheld.")
        self.assertEqual(safe_error_code(error), "PROVIDER_RATE_LIMIT_EXHAUSTED")

    def test_daily_quota_is_classified(self):
        error = RuntimeError("Groq daily quota has been exhausted.")
        self.assertEqual(safe_error_code(error), "PROVIDER_DAILY_QUOTA_EXHAUSTED")

    def test_invalid_agent_response_is_classified(self):
        self.assertEqual(safe_error_code(ValueError("secret prompt must never be logged")), "INVALID_AGENT_RESPONSE")

    def test_unknown_runtime_error_does_not_expose_raw_message(self):
        self.assertEqual(safe_error_code(RuntimeError("private provider response")), "PROVIDER_REQUEST_FAILED")


class ReviewHeadingCompatibilityTests(unittest.TestCase):
    def test_department_reviewer_accepts_standalone_headings(self):
        self.assertTrue(department_review(VALID_REVIEW_WITH_STANDALONE_HEADINGS))

    def test_pentester_reviewer_accepts_standalone_headings(self):
        self.assertTrue(pentester_review(VALID_REVIEW_WITH_STANDALONE_HEADINGS))

    def test_technical_reviewer_accepts_standalone_headings(self):
        self.assertTrue(technical_review(VALID_REVIEW_WITH_STANDALONE_HEADINGS))

    def test_reviewer_still_requires_explicit_pass(self):
        invalid = VALID_REVIEW_WITH_STANDALONE_HEADINGS.replace(
            "REVIEW STATUS: PASS", "REVIEW STATUS: NEEDS_REVISION", 1
        )
        self.assertFalse(department_review(invalid))
        self.assertFalse(pentester_review(invalid))
        self.assertFalse(technical_review(invalid))


if __name__ == "__main__":
    unittest.main()
