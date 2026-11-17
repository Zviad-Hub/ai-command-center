import unittest
from unittest.mock import patch

import media_agents


class ScriptNarrationParsingTests(unittest.TestCase):
    def test_extracts_colon_heading(self):
        text = """SCRIPT:
The old mystery remains unresolved.
VISUAL DIRECTIONS:
0:00-0:10 A map.
"""
        self.assertEqual(
            media_agents.extract_narration(text),
            "The old mystery remains unresolved."
        )

    def test_extracts_markdown_heading_without_colon(self):
        text = """### SCRIPT
The old mystery remains unresolved.
### VISUAL DIRECTIONS
0:00-0:10 A map.
"""
        self.assertEqual(
            media_agents.extract_narration(text),
            "The old mystery remains unresolved."
        )

    def test_extracts_bold_heading(self):
        text = """**SCRIPT:**
The old mystery remains unresolved.
**VISUAL DIRECTIONS:**
0:00-0:10 A map.
"""
        self.assertEqual(
            media_agents.extract_narration(text),
            "The old mystery remains unresolved."
        )

    def test_scriptwriter_retries_format_once(self):
        original = """VIDEO TITLE:
A Historical Mystery
This response forgot its section labels.
"""
        repaired = """VIDEO TITLE:
A Historical Mystery
SCRIPT:
The mystery remains unresolved because the available evidence does not establish one answer.
VISUAL DIRECTIONS:
0:00-0:10 A historical map.
FACTS TO VERIFY:
The origin of the story.
"""
        with patch.object(
            media_agents, "ask_ai", side_effect=[original, repaired]
        ) as mocked:
            result = media_agents.scriptwriter(
                "Create a historical mystery script",
                "Approved concept",
                {"status": "COMPLETED", "sources": []}
            )
        self.assertIn("SCRIPT:", result)
        self.assertEqual(mocked.call_count, 2)

    def test_scriptwriter_does_not_retry_more_than_once(self):
        invalid = "No script section was returned."
        with patch.object(
            media_agents, "ask_ai", return_value=invalid
        ) as mocked:
            with self.assertRaisesRegex(RuntimeError, "format-repair attempt"):
                media_agents.scriptwriter(
                    "Create a historical mystery script",
                    "Approved concept",
                    {"status": "COMPLETED", "sources": []}
                )
        self.assertEqual(mocked.call_count, 2)


if __name__ == "__main__":
    unittest.main()
