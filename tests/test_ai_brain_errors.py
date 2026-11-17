import os
import unittest
from unittest.mock import patch

import requests

import ai_brain


SECRET_DETAIL = "SENSITIVE_GROQ_RESPONSE_BODY"


def make_response(status_code, body):
    response = requests.Response()
    response.status_code = status_code
    response._content = body.encode("utf-8")
    response.headers["Content-Type"] = "application/json"
    return response


class GroqProviderErrorRedactionTests(unittest.TestCase):
    def _ask_with_response(self, status_code, body):
        response = make_response(status_code, body)
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-secret-key"}), patch.object(
            ai_brain, "MAX_RETRIES", 0
        ), patch.object(ai_brain.requests, "post", return_value=response):
            with self.assertRaises(RuntimeError) as caught:
                ai_brain.ask_ai("system prompt", "user prompt")
        message = str(caught.exception)
        self.assertNotIn(SECRET_DETAIL, message)
        self.assertNotIn("test-secret-key", message)
        self.assertIn("withheld", message)
        return message

    def test_non_daily_rate_limit_body_is_redacted(self):
        message = self._ask_with_response(
            429, '{"error":"' + SECRET_DETAIL + '","message":"temporary limit"}'
        )
        self.assertIn("rate limit", message.lower())

    def test_server_error_body_is_redacted(self):
        message = self._ask_with_response(
            503, '{"error":"' + SECRET_DETAIL + '"}'
        )
        self.assertIn("503", message)

    def test_other_http_error_body_is_redacted(self):
        message = self._ask_with_response(
            400, '{"error":"' + SECRET_DETAIL + '"}'
        )
        self.assertIn("400", message)

    def test_daily_quota_classification_is_preserved_without_body_leak(self):
        message = self._ask_with_response(
            429,
            '{"error":"' + SECRET_DETAIL + '","message":"daily quota has been exhausted"}'
        )
        self.assertIn("daily quota", message.lower())

    def test_connection_exception_details_are_redacted(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-secret-key"}), patch.object(
            ai_brain, "MAX_RETRIES", 0
        ), patch.object(
            ai_brain.requests, "post",
            side_effect=requests.ConnectionError(SECRET_DETAIL)
        ):
            with self.assertRaises(RuntimeError) as caught:
                ai_brain.ask_ai("system prompt", "user prompt")

        self.assertNotIn(SECRET_DETAIL, str(caught.exception))
        self.assertNotIn("test-secret-key", str(caught.exception))
        self.assertIn("withheld", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
