import unittest
from unittest.mock import Mock, patch
from oao.adapters.autogen_adapter import AutoGenAdapter


class TestAutoGenAdapter(unittest.TestCase):

    @patch(
        "oao.adapters.autogen_adapter.AutoGenAdapter._ensure_autogen_installed",
        return_value=None,
    )
    def test_initiate_chat(self, mock_install):
        mock_sender = Mock()
        mock_recipient = Mock()
        mock_chat_result = Mock()
        mock_chat_result.summary = "Conversational chat summary"
        mock_chat_result.cost = {
            "usage_including_cached_inference": {"total_tokens": 200}
        }
        mock_sender.initiate_chat.return_value = mock_chat_result

        adapter = AutoGenAdapter(mock_sender)
        res = adapter.execute(
            {"recipient": mock_recipient, "message": "Start debate"}
        )

        mock_sender.initiate_chat.assert_called_once_with(
            recipient=mock_recipient, message="Start debate"
        )
        self.assertEqual(res["output"], "Conversational chat summary")
        self.assertEqual(adapter.get_token_usage(), 200)


if __name__ == "__main__":
    unittest.main()
