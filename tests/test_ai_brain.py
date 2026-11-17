"""Offline regression tests for adaptive Groq completion handling."""
import os
import unittest
from unittest.mock import Mock, patch

import ai_brain


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

    def test_token_limit_detection_for_director(self):
        self.assertEqual(
            ai_brain.detect_token_limit("Chief AI Director"),
            1200,
        )


if __name__ == "__main__":
    unittest.main()
