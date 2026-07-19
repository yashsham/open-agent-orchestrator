import unittest
from unittest.mock import Mock, patch
from oao.adapters.llamaindex_adapter import LlamaIndexAdapter


class TestLlamaIndexAdapter(unittest.TestCase):

    @patch(
        "oao.adapters.llamaindex_adapter.LlamaIndexAdapter._ensure_llamaindex_installed",
        return_value=None,
    )
    def test_agent_chat(self, mock_install):
        mock_agent = Mock()
        mock_response = Mock()
        mock_response.response = "LlamaIndex chat response"
        mock_agent.chat.return_value = mock_response

        adapter = LlamaIndexAdapter(mock_agent)
        res = adapter.execute("Hello Llama")

        mock_agent.chat.assert_called_once_with("Hello Llama")
        self.assertEqual(res["output"], "LlamaIndex chat response")


if __name__ == "__main__":
    unittest.main()
