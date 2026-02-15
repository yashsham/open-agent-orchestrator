import importlib
import sys
import os
import inspect
from typing import List, Type
from oao.plugins.base import PluginInterface

class PluginLoader:
    """
    Securely loads external plugins to extend OAO functionality.
    Enforces PluginInterface compliance.
    """

    @staticmethod
    def load(plugin_path: str):
        """
        Load a plugin from a path (module string or file path).
        The plugin module must define a class that implements PluginInterface.
        """
        try:
            # If path ends with .py, add its dir to sys.path and import name
            if plugin_path.endswith(".py"):
                directory = os.path.dirname(os.path.abspath(plugin_path))
                if directory not in sys.path:
                    sys.path.append(directory)
                
                module_name = os.path.basename(plugin_path).replace(".py", "")
                module = importlib.import_module(module_name)
            else:
                # Assume python module path
                module = importlib.import_module(plugin_path)

            # Find the PluginInterface implementation
            plugin_class = None
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, PluginInterface) and 
                    obj is not PluginInterface):
                    plugin_class = obj
                    break
            
            if not plugin_class:
                print(f"[PLUGIN] Error: No PluginInterface implementation found in {plugin_path}")
                return

            # Instantiate and activate
            plugin_instance = plugin_class()
            plugin_instance.activate()
            print(f"[PLUGIN] Loaded: {plugin_instance.name} v{plugin_instance.version}")
            return plugin_instance

        except Exception as e:
            print(f"[PLUGIN] Error loading {plugin_path}: {e}")
            raise

    @staticmethod
    def load_directory(directory: str):
        """Load all .py plugins in a directory."""
        if not os.path.exists(directory):
            return
            
        for filename in os.listdir(directory):
            if filename.endswith(".py") and not filename.startswith("__"):
                PluginLoader.load(os.path.join(directory, filename))
