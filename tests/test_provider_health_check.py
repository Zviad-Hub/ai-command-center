import unittest
from unittest.mock import Mock

import requests

from scripts import provider_health_check
from scripts.provider_health_check import check_provider, run_health_check


class ProviderHealthCheckTests(unittest.TestCase):
    def response(self, status, body=None, text=""):
        result = Mock()
        result.status_code = status
        result.json.return_value = body if body is not None else {
            "choices": [{"message": {"content": "OK"}}]
        }
        result.text = text
        return result

    def test_missing_key_does_not_send_request(self):
        post = Mock()
        result = check_provider("gemini", "https://example.invalid", "", "model", "max_tokens", post)
        self.assertEqual(result["status"], "NOT_CONFIGURED")
        post.assert_not_called()

    def test_success_uses_small_but_reasonable_token_budget(self):
        post = Mock(return_value=self.response(200))
        result = check_provider("gemini", "https://example.invalid", "secret", "model", "max_tokens", post)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(post.call_args.kwargs["json"]["max_tokens"], 64)
        self.assertEqual(post.call_args.kwargs["timeout"], 12)

    def test_groq_uses_production_reasoning_settings(self):
        post = Mock(return_value=self.response(200))
        result = check_provider("groq", "https://example.invalid", "secret", "model", "max_completion_tokens", post)
        payload = post.call_args.kwargs["json"]
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(payload["max_completion_tokens"], 64)
        self.assertEqual(payload["reasoning_effort"], "low")
        self.assertIs(payload["include_reasoning"], False)

    def test_daily_quota(self):
        post = Mock(return_value=self.response(429, text="Daily quota exceeded"))
        self.assertEqual(
            check_provider("groq", "https://example.invalid", "secret", "model", "max_tokens", post)["status"],
            "DAILY_QUOTA",
        )

    def test_rate_limit(self):
        post = Mock(return_value=self.response(429, text="Too many requests"))
        self.assertEqual(
            check_provider("groq", "https://example.invalid", "secret", "model", "max_tokens", post)["status"],
            "RATE_LIMIT",
        )

    def test_service_unavailable(self):
        post = Mock(return_value=self.response(503))
        self.assertEqual(
            check_provider("gemini", "https://example.invalid", "secret", "model", "max_tokens", post)["status"],
            "HTTP_503",
        )

    def test_auth_error(self):
        post = Mock(return_value=self.response(401))
        self.assertEqual(
            check_provider("gemini", "https://example.invalid", "secret", "model", "max_tokens", post)["status"],
            "AUTH_ERROR",
        )

    def test_timeout(self):
        post = Mock(side_effect=requests.exceptions.Timeout())
        self.assertEqual(
            check_provider("gemini", "https://example.invalid", "secret", "model", "max_tokens", post)["status"],
            "TIMEOUT",
        )

    def test_no_choices_is_classified_safely(self):
        post = Mock(return_value=self.response(200, body={"choices": []}))
        self.assertEqual(
            check_provider("gemini", "https://example.invalid", "secret", "model", "max_tokens", post)["status"],
            "NO_CHOICES",
        )

    def test_empty_content_is_classified_safely(self):
        post = Mock(return_value=self.response(200, body={"choices": [{"message": {"content": ""}}]}))
        self.assertEqual(
            check_provider("gemini", "https://example.invalid", "secret", "model", "max_tokens", post)["status"],
            "EMPTY_CONTENT",
        )

    def test_truncated_response_is_classified_safely(self):
        post = Mock(return_value=self.response(200, body={
            "choices": [{"message": {"content": ""}, "finish_reason": "length"}]
        }))
        self.assertEqual(
            check_provider("groq", "https://example.invalid", "secret", "model", "max_completion_tokens", post)["status"],
            "TRUNCATED_RESPONSE",
        )


    def test_secondary_provider_uses_safe_https_and_small_request(self):
        post = Mock(return_value=self.response(200))
        result = check_provider("openrouter", "https://openrouter.ai/api/v1/chat/completions",
                                "secret", "openrouter/auto", "max_tokens", post)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(post.call_args.kwargs["json"]["max_tokens"], 64)
        self.assertEqual(post.call_args.kwargs["timeout"], 12)

    def test_http_secondary_endpoint_is_rejected_without_sending_secret(self):
        post = Mock()
        result = check_provider("secondary", "http://example.com/chat", "secret", "model", "max_tokens", post)
        self.assertEqual(result["status"], "INVALID_CONFIGURATION")
        post.assert_not_called()

    @patch.dict("os.environ", {
        "GROQ_API_KEY": "groq-secret",
        "GEMINI_API_KEY": "gemini-secret",
        "AI_FALLBACK_API_KEY": "openrouter-secret",
        "AI_FALLBACK_API_URL": "https://openrouter.ai/api/v1/chat/completions",
        "AI_FALLBACK_MODEL": "openrouter/auto",
    }, clear=True)
    def test_run_health_check_reports_all_three_provider_statuses(self):
        groq = self.response(200)
        gemini = self.response(429, text="Daily quota exceeded")
        openrouter = self.response(402, text="Private billing detail")
        with patch.object(provider_health_check.requests, "post", side_effect=[groq, gemini, openrouter]) as post:
            result = run_health_check()
        self.assertEqual(result["overall_status"], "PARTIAL")
        self.assertEqual(
            result["providers"],
            [
                {"provider": "groq", "status": "PASS"},
                {"provider": "gemini", "status": "DAILY_QUOTA"},
                {"provider": "openrouter", "status": "HTTP_ERROR_402"},
            ],
        )
        self.assertEqual(result["requests_sent"], 3)
        self.assertEqual(post.call_count, 3)
        self.assertNotIn("Private billing detail", str(result))


if __name__ == "__main__":
    unittest.main()
