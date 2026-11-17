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

    def test_detects_georgian_request_language(self):
        task = "შექმენი ვიდეო ქართულ ენაზე მაიას ცივილიზაციაზე."
        self.assertTrue(
            media_agents.narration_matches_requested_language(
                task, "მაიას ცივილიზაცია საუკუნეების განმავლობაში ვითარდებოდა."
            )
        )
        self.assertFalse(
            media_agents.narration_matches_requested_language(
                task, "The Maya civilization developed over centuries."
            )
        )
        self.assertIn(
            "Georgian",
            media_agents.requested_language_instruction(task)
        )

    def test_explicit_english_instruction_can_request_georgian_output(self):
        task = "Write a YouTube Shorts script in Georgian about the Maya."
        self.assertTrue(media_agents.is_georgian_request(task))
        self.assertFalse(
            media_agents.narration_matches_requested_language(
                task, "The Maya civilization developed over centuries."
            )
        )

    def test_scriptwriter_includes_language_requirement_in_provider_prompt(self):
        script = """VIDEO TITLE:
მაიას ცივილიზაციის საიდუმლო
EXACT TOPIC:
მაიას ცივილიზაცია
HOOK:
რა მოხდა სინამდვილეში?
SCRIPT:
მაიას ცივილიზაცია ცენტრალურ ამერიკაში განვითარდა.
VISUAL DIRECTIONS:
0:00-0:10 რუკა
0:10-0:20 ქალაქი
0:20-0:30 წარწერები
0:30-0:40 ტყე
0:40-0:50 არქეოლოგები
0:50-1:00 ნანგრევები
FACTS TO VERIFY:
წყაროები
"""
        with patch.object(media_agents, "ask_ai", return_value=script) as mocked:
            media_agents.scriptwriter(
                "შექმენი ქართულენოვანი ვიდეო მაიას ცივილიზაციაზე",
                "კონცეფცია",
                {"status": "COMPLETED", "sources": []}
            )
        self.assertIn("Georgian", mocked.call_args.args[0])
        self.assertIn("Do not translate the narration into English", mocked.call_args.args[0])

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
