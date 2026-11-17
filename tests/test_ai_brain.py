"""Offline regression tests for adaptive Groq completion handling."""
import os
import unittest
from unittest.mock import Mock, patch

import ai_brain
from error_diagnostics import safe_error_code


def _response(content, finish_reason="stop"):
    response = Mock()
    response.ok = True
    response.status_code = 200
    response.json.return_value = {
        "choices": [{
            "message": {"content": content},
            "finish_reason": finish_reason,
        }],
        "usage": {"completion_tokens": 42},
    }
    return response


class AskAITests(unittest.TestCase):
    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key"})
    @patch("ai_brain.requests.post")
    def test_retries_once_with_doubled_limit_after_truncation(self, post):
        post.side_effect = [
            _response("partial", "length"),
            _response("complete", "stop"),
        ]

        result = ai_brain.ask_ai(
            "You are a Chief AI Director.",
            "Return a short test result.",
        )

        self.assertEqual(result, "complete")
        self.assertEqual(post.call_count, 2)
        first_payload = post.call_args_list[0].kwargs["json"]
        second_payload = post.call_args_list[1].kwargs["json"]
        self.assertEqual(first_payload["max_completion_tokens"], 1200)
        self.assertEqual(second_payload["max_completion_tokens"], 2400)

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key"})
    @patch("ai_brain.requests.post")
    def test_stops_after_bounded_length_retries(self, post):
        post.side_effect = [
            _response("partial one", "length"),
            _response("partial two", "length"),
            _response("partial three", "length"),
        ]

        with self.assertRaisesRegex(RuntimeError, "remained truncated"):
            ai_brain.ask_ai("You are a Chief AI Director.", "Test task.")

        self.assertEqual(post.call_count, 3)
        limits = [
            call.kwargs["json"]["max_completion_tokens"]
            for call in post.call_args_list
        ]
        self.assertEqual(limits, [1200, 2400, 4800])

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_api_key_fails_before_network_request(self):
        with patch("ai_brain.requests.post") as post:
            with self.assertRaisesRegex(RuntimeError, "GROQ_API_KEY is missing"):
                ai_brain.ask_ai("system", "task")
            post.assert_not_called()


    @patch.dict(os.environ, {
        "GROQ_API_KEY": "primary-key",
        "GEMINI_API_KEY": "gemini-test-key",
        "AI_FALLBACK_API_URL": "https://legacy.example/v1/chat/completions",
        "AI_FALLBACK_API_KEY": "legacy-key",
        "AI_FALLBACK_MODEL": "legacy-model",
    })
    @patch("ai_brain.requests.post")
    def test_gemini_free_fallback_takes_precedence_over_legacy_provider(self, post):
        quota = Mock()
        quota.status_code = 429
        quota.ok = False
        quota.text = '{"error":"daily quota exhausted"}'
        post.side_effect = [quota, _response("Gemini fallback result")]

        result = ai_brain.ask_ai("system prompt", "user prompt")

        self.assertEqual(result, "Gemini fallback result")
        self.assertEqual(post.call_count, 2)
        fallback_call = post.call_args_list[1]
        self.assertEqual(
            fallback_call.args[0],
            "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        )
        self.assertEqual(
            fallback_call.kwargs["headers"]["Authorization"],
            "Bearer gemini-test-key",
        )
        self.assertEqual(fallback_call.kwargs["json"]["model"], "gemini-3.8-flash")
        self.assertIn("max_tokens", fallback_call.kwargs["json"])
        self.assertNotIn("reasoning_effort", fallback_call.kwargs["json"])

    @patch.dict(os.environ, {
        "GROQ_API_KEY": "primary-key",
        "AI_FALLBACK_API_URL": "https://fallback.example/v1/chat/completions",
        "AI_FALLBACK_API_KEY": "fallback-key",
        "AI_FALLBACK_MODEL": "fallback-model",
    })
    @patch("ai_brain.requests.post")
    def test_daily_quota_uses_configured_fallback_provider(self, post):
        quota = Mock()
        quota.status_code = 429
        quota.ok = False
        quota.text = '{"error":"daily quota exhausted"}'
        fallback = _response("fallback result")
        post.side_effect = [quota, fallback]

        result = ai_brain.ask_ai("system prompt", "user prompt")

        self.assertEqual(result, "fallback result")
        self.assertEqual(post.call_count, 2)
        primary_call, fallback_call = post.call_args_list
        self.assertIn("api.groq.com", primary_call.args[0])
        self.assertEqual(fallback_call.args[0], "https://fallback.example/v1/chat/completions")
        self.assertEqual(fallback_call.kwargs["headers"]["Authorization"], "Bearer fallback-key")
        self.assertEqual(fallback_call.kwargs["json"]["model"], "fallback-model")
        self.assertIn("max_tokens", fallback_call.kwargs["json"])

    @patch.dict(os.environ, {
        "GROQ_API_KEY": "primary-key",
        "AI_FALLBACK_API_URL": "https://fallback.example/v1/chat/completions",
        "AI_FALLBACK_API_KEY": "fallback-key",
        "AI_FALLBACK_MODEL": "fallback-model",
    })
    @patch("ai_brain.requests.post")
    def test_fallback_is_not_used_for_non_daily_http_errors(self, post):
        response = Mock()
        response.status_code = 401
        response.ok = False
        response.text = '{"error":"unauthorized"}'
        post.return_value = response

        with self.assertRaisesRegex(RuntimeError, "HTTP error: 401"):
            ai_brain.ask_ai("system prompt", "user prompt")
        self.assertEqual(post.call_count, 1)

    @patch.dict(os.environ, {
        "AI_FALLBACK_API_URL": "https://fallback.example/v1/chat/completions",
        "AI_FALLBACK_API_KEY": "fallback-key",
        "AI_FALLBACK_MODEL": "fallback-model",
    }, clear=True)
    @patch("ai_brain.requests.post")
    def test_fallback_can_run_when_primary_key_is_missing(self, post):
        post.return_value = _response("fallback only result")
        result = ai_brain.ask_ai("system prompt", "user prompt")
        self.assertEqual(result, "fallback only result")
        self.assertEqual(post.call_count, 1)
        self.assertEqual(post.call_args.args[0], "https://fallback.example/v1/chat/completions")

    def test_safe_error_code_identifies_fallback_http_status_without_details(self):
        self.assertEqual(
            safe_error_code("Fallback AI provider HTTP error: 401; provider details were withheld."),
            "FALLBACK_PROVIDER_HTTP_401",
        )

    def test_safe_error_code_identifies_primary_http_status_without_details(self):
        self.assertEqual(
            safe_error_code("Groq API HTTP error: 503; provider details were withheld."),
            "PRIMARY_PROVIDER_HTTP_503",
        )

    def test_safe_error_code_identifies_groq_server_error(self):
        self.assertEqual(
            safe_error_code("Groq server error: HTTP 502; provider details were withheld."),
            "PRIMARY_PROVIDER_HTTP_502",
        )

    def test_token_limit_detection_for_director(self):
        self.assertEqual(
            ai_brain.detect_token_limit("Chief AI Director"),
            1200,
        )


if __name__ == "__main__":
    unittest.main()
