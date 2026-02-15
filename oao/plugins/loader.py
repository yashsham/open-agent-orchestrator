import importlib
import sys
import os
from typing import List

class PluginLoader:
    """
    Loads external plugins to extend OAO functionality.
    """

    @staticmethod
    def load(plugin_path: str):
        """
        Load a plugin from a path (module string or file path).
        The plugin module must have a `register()` function.
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

            if hasattr(module, "register"):
                module.register()
                print(f"[PLUGIN] Loaded: {plugin_path}")
            else:
                print(f"[PLUGIN] Warning: {plugin_path} has no register() function")
                
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
