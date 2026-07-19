import unittest
from unittest.mock import Mock, patch
from oao.adapters.crewai_adapter import CrewAIAdapter


class TestCrewAIAdapter(unittest.TestCase):

    @patch(
        "oao.adapters.crewai_adapter.CrewAIAdapter._ensure_crewai_installed",
        return_value=None,
    )
    def test_crew_kickoff(self, mock_install):
        mock_crew = Mock()
        mock_output = Mock()
        mock_output.raw = "Crew output raw"
        mock_output.token_usage = Mock(total_tokens=150)
        mock_crew.kickoff.return_value = mock_output

        adapter = CrewAIAdapter(mock_crew)
        res = adapter.execute("Test task")

        mock_crew.kickoff.assert_called_once_with(inputs={"task": "Test task"})
        self.assertEqual(res["output"], "Crew output raw")
        self.assertEqual(adapter.get_token_usage(), 150)

    @patch(
        "oao.adapters.crewai_adapter.CrewAIAdapter._ensure_crewai_installed",
        return_value=None,
    )
    def test_agent_execute(self, mock_install):
        mock_agent = Mock()
        mock_agent.execute_task.return_value = "Agent executed task successfully"
        del mock_agent.kickoff  # Simulates Agent, not Crew

        adapter = CrewAIAdapter(mock_agent)
        res = adapter.execute("Task text", context={"user": "admin"})

        mock_agent.execute_task.assert_called_once_with(
            "Task text", context={"user": "admin"}
        )
        self.assertEqual(res["output"], "Agent executed task successfully")


if __name__ == "__main__":
    unittest.main()
