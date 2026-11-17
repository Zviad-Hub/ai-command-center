import unittest
from unittest.mock import Mock

import requests

from scripts.provider_health_check import check_provider


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

    def test_success(self):
        post = Mock(return_value=self.response(200))
        result = check_provider("gemini", "https://example.invalid", "secret", "model", "max_tokens", post)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(post.call_args.kwargs["json"]["max_tokens"], 8)
        self.assertEqual(post.call_args.kwargs["timeout"], 12)

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

    def test_invalid_success_payload(self):
        post = Mock(return_value=self.response(200, body={"choices": []}))
        self.assertEqual(
            check_provider("gemini", "https://example.invalid", "secret", "model", "max_tokens", post)["status"],
            "INVALID_RESPONSE",
        )


if __name__ == "__main__":
    unittest.main()
