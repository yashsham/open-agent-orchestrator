from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class PluginInterface(ABC):
    """
    Abstract Base Class that all OAO plugins must implement.
    Enforces structure and versioning for security and stability.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name of the plugin."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin version string (semver recommended)."""
        pass

    @abstractmethod
    def activate(self):
        """
        Called when the plugin is loaded.
        Register policies, schedulers, listeners, etc. here.
        """
        pass

    @abstractmethod
    def deactivate(self):
        """
        Called when the plugin is unloaded.
        Cleanup resources, unregister components, etc.
        """
        pass
