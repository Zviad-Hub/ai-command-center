import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from task_manager import load_tasks, save_tasks


class TaskHistoryPersistenceTests(unittest.TestCase):

    def test_missing_history_file_starts_with_empty_list(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tasks.json"
            with patch("task_manager.TASKS_FILE", path):
                self.assertEqual(load_tasks(), [])

    def test_malformed_history_is_rejected_and_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tasks.json"
            original = '{"broken": '
            path.write_text(original, encoding="utf-8")

            with patch("task_manager.TASKS_FILE", path):
                with self.assertRaisesRegex(RuntimeError, "invalid JSON"):
                    load_tasks()

            self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_non_list_history_is_rejected_and_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tasks.json"
            original = json.dumps({"task": "not a history list"})
            path.write_text(original, encoding="utf-8")

            with patch("task_manager.TASKS_FILE", path):
                with self.assertRaisesRegex(RuntimeError, "must be a list"):
                    load_tasks()

            self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_save_writes_valid_json_and_replaces_existing_history(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tasks.json"
            path.write_text('[{"id": "old"}]', encoding="utf-8")
            expected = [{"id": "new", "task": "ქართული ტექსტი"}]

            with patch("task_manager.TASKS_FILE", path):
                save_tasks(expected)
                self.assertEqual(load_tasks(), expected)

            self.assertEqual(
                sorted(item.name for item in path.parent.iterdir()),
                ["tasks.json"],
            )

    def test_failed_serialization_does_not_replace_existing_history(self):
        class NotSerializable:
            pass

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tasks.json"
            original = '[{"id": "keep-me"}]'
            path.write_text(original, encoding="utf-8")

            with patch("task_manager.TASKS_FILE", path):
                with self.assertRaisesRegex(RuntimeError, "not be saved safely"):
                    save_tasks([NotSerializable()])

            self.assertEqual(path.read_text(encoding="utf-8"), original)
            self.assertEqual(
                sorted(item.name for item in path.parent.iterdir()),
                ["tasks.json"],
            )

    def test_save_rejects_non_list_input(self):
        with self.assertRaisesRegex(ValueError, "must be a list"):
            save_tasks({"not": "a list"})


if __name__ == "__main__":
    unittest.main()
