import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from task_manager import (
    _default_tasks_file,
    load_tasks,
    save_tasks,
)


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

    def test_explicit_environment_path_overrides_default(self):
        with tempfile.TemporaryDirectory() as directory:
            expected = Path(directory) / "private" / "tasks.json"
            with patch.dict(os.environ, {
                "AI_COMMAND_CENTER_TASKS_FILE": str(expected)
            }):
                self.assertEqual(_default_tasks_file(), expected)

    def test_windows_default_uses_local_app_data(self):
        with patch("task_manager.sys.platform", "win32"), patch.dict(
            os.environ,
            {"LOCALAPPDATA": "/tmp/windows-local"},
            clear=True,
        ):
            path = _default_tasks_file()
        self.assertEqual(path, Path("/tmp/windows-local") / "AI Command Center" / "tasks.json")

    def test_macos_default_uses_application_support(self):
        with patch("task_manager.sys.platform", "darwin"), patch(
            "task_manager.Path.home", return_value=Path("/tmp/home")
        ), patch.dict(os.environ, {}, clear=True):
            path = _default_tasks_file()
        self.assertEqual(
            path,
            Path("/tmp/home/Library/Application Support/AI Command Center/tasks.json"),
        )

    def test_linux_default_respects_xdg_state_home(self):
        with patch("task_manager.sys.platform", "linux"), patch.dict(
            os.environ,
            {"XDG_STATE_HOME": "/tmp/xdg-state"},
            clear=True,
        ):
            path = _default_tasks_file()
        self.assertEqual(path, Path("/tmp/xdg-state/ai-command-center/tasks.json"))

    def test_legacy_history_is_migrated_without_deleting_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            legacy = root / "legacy-tasks.json"
            destination = root / "private" / "tasks.json"
            expected = [{"id": "legacy", "task": "keep this history"}]
            legacy.write_text(json.dumps(expected), encoding="utf-8")

            with patch("task_manager.LEGACY_TASKS_FILE", legacy), patch(
                "task_manager.TASKS_FILE", destination
            ):
                self.assertEqual(load_tasks(), expected)
                self.assertEqual(load_tasks(), expected)

            self.assertEqual(json.loads(destination.read_text(encoding="utf-8")), expected)
            self.assertTrue(legacy.exists())

    def test_invalid_legacy_history_is_preserved_and_not_migrated(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            legacy = root / "legacy-tasks.json"
            destination = root / "private" / "tasks.json"
            original = '{"invalid": '
            legacy.write_text(original, encoding="utf-8")

            with patch("task_manager.LEGACY_TASKS_FILE", legacy), patch(
                "task_manager.TASKS_FILE", destination
            ):
                with self.assertRaisesRegex(RuntimeError, "invalid JSON"):
                    load_tasks()

            self.assertEqual(legacy.read_text(encoding="utf-8"), original)
            self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
