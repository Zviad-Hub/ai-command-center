import unittest
from unittest.mock import patch

from media_agents import run_media_department


class MediaDepartmentTests(unittest.TestCase):

    def _valid_script(self, word_count=130, six_scenes=True):
        narration = " ".join(f"topicword{index}" for index in range(word_count))
        timestamps = [
            "0:00 - 0:10",
            "0:10 - 0:20",
            "0:20 - 0:30",
            "0:30 - 0:40",
            "0:40 - 0:50",
            "0:50 - 1:00",
        ]
        if not six_scenes:
            timestamps = timestamps[:1]
        scenes = "\n".join(f"{stamp}: Scene {index + 1}" for index, stamp in enumerate(timestamps))
        return (
            "VIDEO TITLE: Test topic\n"
            f"SCRIPT:\n{narration}\n"
            f"VISUAL DIRECTIONS:\n{scenes}\n"
            "FACTS TO VERIFY:\nClaim 1"
        )

    def _run_with_mocks(self, script=None, research=None, fact_checks=None, strategist_error=None):
        research = research or {
            "status": "COMPLETED",
            "sources": [{
                "title": "Supplied source",
                "url": "https://example.org/source",
                "content": "Relevant supplied source content.",
                "verification_status": "VERIFIED",
            }],
        }
        script = script or self._valid_script()
        fact_checks = fact_checks or ["STATUS: VERIFIED", "STATUS: VERIFIED"]

        with (
            patch("media_agents.run_research", return_value=research),
            patch("media_agents.creative_strategist", side_effect=strategist_error or None, return_value="EXACT TOPIC: Test topic"),
            patch("media_agents.scriptwriter", return_value="Initial script"),
            patch("media_agents.quality_editor", return_value="Edited draft"),
            patch("media_agents.fact_checker", side_effect=fact_checks),
            patch("media_agents.evidence_based_editor", return_value=script),
        ):
            return run_media_department("Create a short video about the test topic.")

    def test_complete_media_pipeline_stays_review_required_and_unpublished(self):
        result = self._run_with_mocks()
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertFalse(result["publication_approved"])
        self.assertEqual(result["narration_word_count"], 130)
        self.assertTrue(result["validation"]["visual_scene_count_passed"])
        self.assertFalse(result["warnings"])

    def test_missing_research_stops_before_creative_work(self):
        with (
            patch("media_agents.run_research", return_value={"status": "NO_RESULTS", "sources": []}),
            patch("media_agents.creative_strategist") as strategist,
        ):
            result = run_media_department("Create a short video about the test topic.")
        self.assertEqual(result["status"], "ERROR")
        self.assertEqual(result["failed_stage"], "Research Agent")
        self.assertFalse(result["publication_approved"])
        strategist.assert_not_called()

    def test_unverified_research_sources_are_explicitly_flagged(self):
        research = {
            "status": "COMPLETED",
            "sources": [{
                "title": "Candidate source",
                "url": "https://example.org/candidate",
                "content": "Candidate content only.",
                "verification_status": "NOT_VERIFIED",
            }],
        }
        result = self._run_with_mocks(research=research)
        self.assertTrue(any("not marked VERIFIED or CONFIRMED" in warning for warning in result["warnings"]))
        self.assertFalse(result["publication_approved"])

    def test_final_fact_check_needs_source_adds_warning(self):
        result = self._run_with_mocks(
            fact_checks=["STATUS: VERIFIED", "Claim 2 STATUS: NEEDS SOURCE"]
        )
        self.assertTrue(any("claims needing sources" in warning for warning in result["warnings"]))
        self.assertFalse(result["publication_approved"])

    def test_invalid_script_structure_is_flagged_not_auto_approved(self):
        result = self._run_with_mocks(
            script=self._valid_script(word_count=100, six_scenes=False)
        )
        self.assertTrue(any("125-140 word requirement" in warning for warning in result["warnings"]))
        self.assertTrue(any("exactly six visual scenes" in warning for warning in result["warnings"]))
        self.assertFalse(result["publication_approved"])

    def test_specialist_failure_preserves_error_stage_and_blocks_publication(self):
        result = self._run_with_mocks(strategist_error=RuntimeError("provider failure"))
        self.assertEqual(result["status"], "ERROR")
        self.assertEqual(result["failed_stage"], "Creative Strategist")
        self.assertFalse(result["publication_approved"])
        self.assertIn("Research Agent", result["specialists"])


if __name__ == "__main__":
    unittest.main()
