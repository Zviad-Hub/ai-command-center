import os
import sys
import types
import unittest
from unittest.mock import patch

import department_agents
from managers import DepartmentManager


SECRET_DETAIL = "SENSITIVE_PROVIDER_EXCEPTION_TOKEN"


class ManagerErrorRedactionTests(unittest.TestCase):
    def test_manager_exceptions_are_not_returned_for_any_department(self):
        cases = {
            "pentester": ("pentester_agents", "run_pentester_department"),
            "media": ("media_agents", "run_media_department"),
            "audit": ("audit_agents", "run_audit"),
            "technical": ("technical_department", "run_technical_department"),
            "finance": ("department_agents", "run_department_workflow"),
            "business": ("department_agents", "run_department_workflow"),
            "tenders": ("department_agents", "run_department_workflow"),
        }

        for department, (module_name, function_name) in cases.items():
            with self.subTest(department=department):
                module = types.ModuleType(module_name)

                def fail(*args, **kwargs):
                    raise RuntimeError(SECRET_DETAIL)

                setattr(module, function_name, fail)
                supplied_modules = {module_name: module}
                context = {}
                if department == "audit":
                    context["previous_results"] = [{"department": "media", "report": "sample"}]

                with patch.dict(sys.modules, supplied_modules):
                    result = DepartmentManager(department).receive_task(
                        "safe test task", context=context
                    )

                self.assertNotIn(SECRET_DETAIL, repr(result))
                self.assertNotIn(SECRET_DETAIL, str(result))
                self.assertNotIn("Traceback", str(result))

    def test_specialist_exception_is_redacted_from_department_result(self):
        with patch.object(department_agents, "_research_context", return_value={
            "status": "DISABLED", "sources": [], "warning": ""
        }), patch.object(
            department_agents, "_call_specialist", side_effect=RuntimeError(SECRET_DETAIL)
        ):
            result = department_agents.run_department_workflow("finance", "test task")

        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertNotIn(SECRET_DETAIL, repr(result))
        self.assertEqual(result["specialist_failures"][0]["error"], "SPECIALIST_FAILED")

    def test_manager_exception_is_redacted_from_department_result(self):
        with patch.object(department_agents, "_research_context", return_value={
            "status": "DISABLED", "sources": [], "warning": ""
        }), patch.object(
            department_agents, "_call_specialist", return_value="specialist evidence"
        ), patch.object(
            department_agents, "ask_ai", side_effect=RuntimeError(SECRET_DETAIL)
        ):
            result = department_agents.run_department_workflow("finance", "test task")

        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertNotIn(SECRET_DETAIL, repr(result))
        self.assertEqual(result["error"], "DEPARTMENT_WORKFLOW_FAILED")

    def test_research_exception_is_redacted_from_warning(self):
        with patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"}), patch.object(
            department_agents, "run_research", side_effect=RuntimeError(SECRET_DETAIL)
        ):
            result = department_agents._research_context("test task", "finance")

        self.assertEqual(result["status"], "ERROR")
        self.assertNotIn(SECRET_DETAIL, repr(result))
        self.assertNotIn(SECRET_DETAIL, result["warning"])


if __name__ == "__main__":
    unittest.main()
