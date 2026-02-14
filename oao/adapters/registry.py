from typing import Type, Dict

from oao.adapters.base_adapter import BaseAdapter


class AdapterRegistry:
    """
    Central registry for all framework adapters.
    """

    _registry: Dict[str, Type[BaseAdapter]] = {}

    @classmethod
    def register(cls, name: str, adapter_cls: Type[BaseAdapter]):
        cls._registry[name] = adapter_cls

    @classmethod
    def get_adapter(cls, name: str) -> Type[BaseAdapter]:
        if name not in cls._registry:
            raise ValueError(f"No adapter registered under name '{name}'")
        return cls._registry[name]

    @classmethod
    def list_adapters(cls):
        return list(cls._registry.keys())
