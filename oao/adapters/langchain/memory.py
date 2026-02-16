import json
from typing import List

try:
    from langchain_core.chat_history import BaseChatMessageHistory
    from langchain_core.messages import BaseMessage, messages_from_dict, messages_to_dict
except ImportError:
    class BaseChatMessageHistory:
        pass
    BaseMessage = Any

from oao.runtime.persistence import RedisPersistenceAdapter

class OAORedisChatMessageHistory(BaseChatMessageHistory):
    """
    Chat message history that stores history in Redis using OAO persistence adapter.
    """

    def __init__(self, session_id: str, ttl: int = 604800):
        self.session_id = session_id
        self.key = f"oao:memory:{session_id}"
        self.ttl = ttl
        self.persistence = RedisPersistenceAdapter()
        self.redis = self.persistence.redis

    @property
    def messages(self) -> List[BaseMessage]:  # type: ignore
        """Retrieve the messages from Redis"""
        items = self.redis.lrange(self.key, 0, -1)
        if not items:
            return []
            
        # Decode utf-8 and parse JSON
        messages = [json.loads(m.decode("utf-8")) for m in items]
        return messages_from_dict(messages)

    def add_message(self, message: BaseMessage) -> None:
        """Append the message to the record in Redis"""
        message_json = json.dumps(messages_to_dict([message])[0])
        self.redis.rpush(self.key, message_json)
        if self.ttl:
            self.redis.expire(self.key, self.ttl)

    def clear(self) -> None:
        """Clear session memory from Redis"""
        self.redis.delete(self.key)
