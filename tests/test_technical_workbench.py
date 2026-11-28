import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from technical_workbench import (
    WorkbenchError,
    list_files,
    read_file,
    run_tests,
    write_file,
)


class TechnicalWorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "tests").mkdir()
        (self.root / "sample.py").write_text("VALUE = 1\n", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_lists_only_allowed_visible_text_files(self):
        (self.root / ".env").write_text("SECRET=hidden", encoding="utf-8")
        (self.root / ".hidden").mkdir()
        (self.root / ".hidden" / "private.py").write_text("x=1", encoding="utf-8")
        (self.root / "image.png").write_bytes(b"not text")
        result = list_files(self.root)
        self.assertEqual(result["files"], ["sample.py"])
        self.assertFalse(result["truncated"])

    def test_read_returns_content_and_sha256(self):
        result = read_file("sample.py", self.root)
        self.assertEqual(result["content"], "VALUE = 1\n")
        self.assertEqual(
            result["sha256"],
            hashlib.sha256(b"VALUE = 1\n").hexdigest(),
        )

    def test_read_redacts_common_credentials_before_returning_source(self):
        source = (
            "GROQ_API_KEY = 'example-secret-value'\\n"
            "Authorization: Bearer abc.def.ghi\\n"
            "TOKEN_VALUE = 'ghp_123456789012345678901234567890123456'\\n"
            "ordinary_setting = True\\n"
        )
        (self.root / "config.py").write_text(source, encoding="utf-8")

        result = read_file("config.py", self.root)

        self.assertNotIn("example-secret-value", result["content"])
        self.assertNotIn("abc.def.ghi", result["content"])
        self.assertNotIn("ghp_123456789012345678901234567890123456", result["content"])
        self.assertIn("ordinary_setting = True", result["content"])
        self.assertEqual(result["redactions"], 3)
        self.assertEqual(
            result["sha256"],
            hashlib.sha256(source.encode("utf-8")).hexdigest(),
        )

    def test_rejects_path_traversal_hidden_and_sensitive_files(self):
        for path in ("../outside.py", "/tmp/outside.py", ".env", ".hidden/private.py", ".git/config"):
            with self.subTest(path=path):
                with self.assertRaises(WorkbenchError):
                    read_file(path, self.root)

    def test_rejects_symlink_escape(self):
        outside = self.root.parent / "outside.py"
        outside.write_text("PRIVATE = True", encoding="utf-8")
        link = self.root / "linked.py"
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks are unavailable on this platform.")
        with self.assertRaises(WorkbenchError):
            read_file("linked.py", self.root)

    def test_write_requires_valid_approval_and_current_hash(self):
        original = (self.root / "sample.py").read_text(encoding="utf-8")
        digest = hashlib.sha256(original.encode("utf-8")).hexdigest()
        with patch.dict(os.environ, {"AI_TECHNICAL_APPROVAL_TOKEN": "ceo-test-token"}):
            with self.assertRaises(WorkbenchError):
                write_file("sample.py", "VALUE = 2\n", expected_sha256=digest, approval_token="wrong", root=self.root)
            with self.assertRaises(WorkbenchError):
                write_file("sample.py", "VALUE = 2\n", expected_sha256="0" * 64, approval_token="ceo-test-token", root=self.root)
            result = write_file(
                "sample.py", "VALUE = 2\n",
                expected_sha256=digest,
                approval_token="ceo-test-token",
                root=self.root,
            )
        self.assertEqual(result["status"], "UPDATED")
        self.assertTrue(result["backup_created"])
        self.assertTrue(result["audit_recorded"])
        self.assertEqual((self.root / "sample.py").read_text(encoding="utf-8"), "VALUE = 2\n")
        backup_root = Path(tempfile.gettempdir()) / "ai-command-center-workbench-backups"
        backups = list(backup_root.rglob("*__sample.py.bak"))
        self.assertTrue(any(path.read_text(encoding="utf-8") == original for path in backups))

    def test_write_rejects_new_files_and_disallowed_targets(self):
        with patch.dict(os.environ, {"AI_TECHNICAL_APPROVAL_TOKEN": "token"}):
            with self.assertRaises(WorkbenchError):
                write_file("new.py", "x=1", expected_sha256="", approval_token="token", root=self.root)
            with self.assertRaises(WorkbenchError):
                write_file("config/.env", "SECRET=x", expected_sha256="", approval_token="token", root=self.root)

    def test_run_tests_uses_allowlisted_unittest_and_strips_provider_secrets(self):
        sample_test = self.root / "tests" / "test_sample.py"
        sample_test.write_text(
            "import os, unittest\n"
            "class SmokeTest(unittest.TestCase):\n"
            "    def test_secret_is_not_inherited(self):\n"
            "        self.assertIsNone(os.getenv('GROQ_API_KEY'))\n",
            encoding="utf-8",
        )
        with patch.dict(os.environ, {"GROQ_API_KEY": "must-not-leak"}):
            result = run_tests(test_module="tests.test_sample", root=self.root)
        self.assertEqual(result["status"], "PASS", result["stderr"])
        self.assertTrue(result["tests_executed"])
        self.assertNotIn("must-not-leak", result["stdout"] + result["stderr"])

    def test_run_tests_disables_dotenv_loading(self):
        (self.root / ".env").write_text("GROQ_API_KEY=must-not-load\n", encoding="utf-8")
        (self.root / "tests" / "test_dotenv.py").write_text(
            """import os, unittest
from dotenv import load_dotenv
class DotenvTest(unittest.TestCase):
    def test_dotenv_is_disabled(self):
        load_dotenv()
        self.assertIsNone(os.getenv('GROQ_API_KEY'))
""",
            encoding="utf-8",
        )
        result = run_tests(test_module="tests.test_dotenv", root=self.root)
        self.assertEqual(result["status"], "PASS", result["stderr"])

    def test_run_tests_rejects_arbitrary_modules_and_timeout_values(self):
        with self.assertRaises(WorkbenchError):
            run_tests(test_module="os.system", root=self.root)
        with self.assertRaises(WorkbenchError):
            run_tests(test_module="tests.test_sample;echo unsafe", root=self.root)
        with self.assertRaises(WorkbenchError):
            run_tests(timeout=0, root=self.root)

    def test_run_tests_reports_timeout(self):
        (self.root / "tests" / "test_slow.py").write_text(
            "import time, unittest\n"
            "class SlowTest(unittest.TestCase):\n"
            "    def test_slow(self):\n"
            "        time.sleep(2)\n",
            encoding="utf-8",
        )
        result = run_tests(test_module="tests.test_slow", timeout=1, root=self.root)
        self.assertEqual(result["status"], "TIMEOUT")
        self.assertTrue(result["tests_executed"])
        self.assertTrue(result["timed_out"])


if __name__ == "__main__":
    unittest.main()
