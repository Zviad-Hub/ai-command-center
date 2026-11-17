import unittest

from error_diagnostics import safe_error_code
from media_agents import build_error_result


class SafeErrorDiagnosticsTests(unittest.TestCase):

    def test_provider_failures_are_classified_without_exposing_messages(self):
        cases = [
            (RuntimeError("Groq daily quota has been exhausted."), "PROVIDER_DAILY_QUOTA_EXHAUSTED"),
            (RuntimeError("Groq rate limit exceeded after retries."), "PROVIDER_RATE_LIMIT_EXHAUSTED"),
            (RuntimeError("Groq API HTTP error: 401; details withheld."), "PROVIDER_HTTP_ERROR"),
            (RuntimeError("Request timed out."), "PROVIDER_TIMEOUT"),
            (RuntimeError("Connection error while calling provider."), "PROVIDER_CONNECTION_ERROR"),
            (RuntimeError("Creative Strategist returned empty output."), "PROVIDER_EMPTY_RESPONSE"),
            (RuntimeError("Creative Strategist refused the task."), "PROVIDER_REFUSAL"),
            (RuntimeError("GROQ_API_KEY is missing!"), "PROVIDER_CONFIGURATION_ERROR"),
        ]

        for error, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(safe_error_code(error), expected)

    def test_media_stage_error_code_includes_safe_failure_category(self):
        result = build_error_result(
            "Create a historical short.",
            "Creative Strategist",
            RuntimeError("Groq daily quota has been exhausted."),
        )

        self.assertEqual(
            result["error_code"],
            "CREATIVE_STRATEGIST_PROVIDER_DAILY_QUOTA_EXHAUSTED",
        )
        self.assertIn("Groq daily quota", result["message"])
        self.assertFalse(result["publication_approved"])

    def test_unknown_runtime_failure_keeps_stage_fallback(self):
        result = build_error_result(
            "Create a historical short.",
            "Creative Strategist",
            RuntimeError("Unexpected internal failure."),
        )

        self.assertEqual(result["error_code"], "CREATIVE_STRATEGIST_FAILED")


if __name__ == "__main__":
    unittest.main()
