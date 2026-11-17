import contextlib
import io
import os
import sys
import types
import unittest
from unittest.mock import patch

import department_agents
from managers import DepartmentManager
import director
import main as command_center_main
import stress_test_suite
import technical_agents
import technical_manager
import pentester_agents
import research_agent
import requests
import technical_department


SECRET_DETAIL = "SENSITIVE_PROVIDER_EXCEPTION_TOKEN"


class ManagerErrorRedactionTests(unittest.TestCase):
    def test_manager_console_does_not_log_raw_user_mission(self):
        output = io.StringIO()
        private_mission = "CONFIDENTIAL_CUSTOMER_PLAN_91f3"
        department_module = types.ModuleType("department_agents")
        department_module.run_department_workflow = lambda department, task, context=None: {
            "department": department, "status": "COMPLETED"
        }
        with patch.dict(sys.modules, {"department_agents": department_module}), contextlib.redirect_stdout(output):
            result = DepartmentManager("finance").receive_task(private_mission)

        self.assertNotIn(private_mission, output.getvalue())
        self.assertIn("MISSION RECEIVED (details withheld).", output.getvalue())
        self.assertEqual(result["department"], "finance")

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

    def test_technical_specialist_exception_is_redacted(self):
        plan = {
            "status": "PLANNED",
            "selected_specialists": [{"id": "backend_developer", "name": "Backend Developer", "mission": "Review supplied code"}],
            "execution_plan": ["Review supplied code"],
            "testing_strategy": ["Propose tests only"],
        }
        with patch.object(technical_department, "run_technical_manager", return_value=plan), patch.object(
            technical_department, "run_specialist", side_effect=RuntimeError(SECRET_DETAIL)
        ):
            result = technical_department.run_technical_department("Review this code")

        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertNotIn(SECRET_DETAIL, repr(result))
        self.assertEqual(result["specialist_results"][0]["error"], "SPECIALIST_FAILED")

    def test_technical_manager_exception_is_redacted(self):
        plan = {
            "status": "PLANNED",
            "selected_specialists": [{"id": "backend_developer", "name": "Backend Developer", "mission": "Review supplied code"}],
            "execution_plan": ["Review supplied code"],
            "testing_strategy": ["Propose tests only"],
        }
        specialist = {
            "specialist": "backend_developer",
            "specialist_name": "Backend Developer",
            "status": "COMPLETED",
            "report": "Evidence-based findings",
            "execution_performed": False,
        }
        with patch.object(technical_department, "run_technical_manager", return_value=plan), patch.object(
            technical_department, "run_specialist", return_value=specialist
        ), patch.object(
            technical_department, "ask_ai", side_effect=RuntimeError(SECRET_DETAIL)
        ):
            result = technical_department.run_technical_department("Review this code")

        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertNotIn(SECRET_DETAIL, repr(result))
        self.assertEqual(result["error"], "TECHNICAL_WORKFLOW_FAILED")

    def test_pentester_specialist_exception_is_redacted(self):
        with patch.object(
            pentester_agents, "_call_specialist", side_effect=RuntimeError(SECRET_DETAIL)
        ):
            result = pentester_agents.run_pentester_department("Review supplied security evidence")

        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertNotIn(SECRET_DETAIL, repr(result))
        self.assertEqual(result["specialist_failures"][0]["error"], "SPECIALIST_FAILED")

    def test_pentester_manager_exception_is_redacted(self):
        with patch.object(
            pentester_agents, "_call_specialist", return_value="Evidence-based security review"
        ), patch.object(
            pentester_agents, "ask_ai", side_effect=RuntimeError(SECRET_DETAIL)
        ):
            result = pentester_agents.run_pentester_department("Review supplied security evidence")

        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertNotIn(SECRET_DETAIL, repr(result))
        self.assertEqual(result["error"], "PENTESTER_WORKFLOW_FAILED")

    def test_director_routing_exception_is_redacted_from_result_and_console(self):
        output = io.StringIO()
        with patch.object(
            director, "ai_route_task", side_effect=RuntimeError(SECRET_DETAIL)
        ), contextlib.redirect_stdout(output):
            result = director.route_task("Please coordinate an orchid taxonomy research project")

        self.assertEqual(result["routing_error"], "AI_ROUTING_FAILED")
        self.assertNotIn(SECRET_DETAIL, repr(result))
        self.assertNotIn(SECRET_DETAIL, output.getvalue())

    def test_research_http_response_body_is_not_exposed(self):
        response = requests.Response()
        response.status_code = 403
        response.url = research_agent.TAVILY_URL
        response._content = SECRET_DETAIL.encode("utf-8")

        def fail_http():
            error = requests.HTTPError("provider error " + SECRET_DETAIL)
            error.response = response
            raise error

        response.raise_for_status = fail_http
        with patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"}), patch.object(
            research_agent.requests, "post", return_value=response
        ), contextlib.redirect_stdout(io.StringIO()):
            result = research_agent.run_research("TOPIC: test")

        self.assertEqual(result["status"], "ERROR")
        self.assertNotIn(SECRET_DETAIL, repr(result))
        self.assertIn("provider details were withheld", result["message"])

    def test_technical_manager_provider_exception_is_redacted(self):
        with patch.object(technical_manager, "ask_ai", side_effect=RuntimeError(SECRET_DETAIL)):
            result = technical_manager.run_technical_manager("Plan a code review")
        self.assertEqual(result["status"], "ERROR")
        self.assertNotIn(SECRET_DETAIL, repr(result))
        self.assertEqual(result["error"], "TECHNICAL_PLANNING_FAILED")

    def test_technical_agent_provider_exception_is_redacted(self):
        with patch.object(technical_agents, "ask_ai", side_effect=RuntimeError(SECRET_DETAIL)):
            result = technical_agents.run_specialist(
                "backend_developer", mission="Review supplied backend code"
            )
        self.assertEqual(result["status"], "ERROR")
        self.assertNotIn(SECRET_DETAIL, repr(result))
        self.assertEqual(result["error"], "SPECIALIST_FAILED")

    def test_cli_does_not_print_raw_system_exception(self):
        output = io.StringIO()
        with patch("builtins.input", side_effect=["safe task", "exit"]), patch.object(
            command_center_main, "submit_task", side_effect=RuntimeError(SECRET_DETAIL)
        ), contextlib.redirect_stdout(output):
            command_center_main.start()
        self.assertNotIn(SECRET_DETAIL, output.getvalue())
        self.assertIn("internal details withheld", output.getvalue())

    def test_routing_stress_report_does_not_store_raw_exception(self):
        with patch.object(
            stress_test_suite, "route_task", side_effect=RuntimeError(SECRET_DETAIL)
        ):
            report = stress_test_suite.run_routing_stress_tests()
        self.assertEqual(report["failed"], report["total"])
        self.assertNotIn(SECRET_DETAIL, repr(report))
        self.assertTrue(all(
            item["error"] == "ROUTING_SCENARIO_FAILED"
            for item in report["results"]
        ))


if __name__ == "__main__":
    unittest.main()
