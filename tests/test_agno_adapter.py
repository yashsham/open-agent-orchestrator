import unittest
from unittest.mock import Mock, patch
from oao.adapters.agno_adapter import AgnoAdapter


class TestAgnoAdapter(unittest.TestCase):

    @patch(
        "oao.adapters.agno_adapter.AgnoAdapter._ensure_agno_installed",
        return_value=None,
    )
    def test_agent_run(self, mock_install):
        mock_agent = Mock()
        mock_run_response = Mock()
        mock_run_response.content = "Agno response content"
        mock_run_response.metrics = Mock(total_tokens=99)
        mock_agent.run.return_value = mock_run_response

        adapter = AgnoAdapter(mock_agent)
        res = adapter.execute("Run query")

        mock_agent.run.assert_called_once_with("Run query")
        self.assertEqual(res["output"], "Agno response content")
        self.assertEqual(adapter.get_token_usage(), 99)


if __name__ == "__main__":
    unittest.main()
