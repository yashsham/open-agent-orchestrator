from abc import ABC, abstractmethod
from typing import Any


class BaseAdapter(ABC):

    @abstractmethod
    def plan(self, task: str) -> Any:
        pass

    @abstractmethod
    async def execute_async(self, task: str, context: dict = None, policy=None) -> Any:
        pass

    @abstractmethod
    def execute(self, task: str, context: dict = None, policy=None) -> Any:
        pass

    @abstractmethod
    def get_token_usage(self) -> int:
        pass
