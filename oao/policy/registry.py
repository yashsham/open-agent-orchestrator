from typing import Type, Dict, Any, Optional

class PolicyRegistry:
    """
    Registry for custom Policies.
    """
    _registry: Dict[str, Type] = {}

    @classmethod
    def register(cls, name: str, policy_cls: Type):
        cls._registry[name] = policy_cls

    @classmethod
    def get(cls, name: str) -> Optional[Type]:
        return cls._registry.get(name)

    @classmethod
    def list_policies(cls):
        return list(cls._registry.keys())
