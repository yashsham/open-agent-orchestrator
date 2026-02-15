import unittest
import sys
import os
import shutil

# Ensure oao is in python path
sys.path.insert(0, os.getcwd())

from oao.plugins.loader import PluginLoader
from oao.plugins.base import PluginInterface

class TestSecurePlugins(unittest.TestCase):
    
    def test_load_valid_plugin(self):
        print("\nTesting Valid Plugin Loading...")
        # Path to our sample plugin
        plugin_path = os.path.join(os.getcwd(), "oao", "plugins", "sample_plugin.py")
        
        try:
            plugin = PluginLoader.load(plugin_path)
            
            self.assertIsNotNone(plugin)
            self.assertIsInstance(plugin, PluginInterface)
            self.assertEqual(plugin.name, "sample_plugin")
            self.assertEqual(plugin.version, "1.0.0")
            print("✅ Valid plugin loaded successfully")
        except Exception as e:
            self.fail(f"Failed to load valid plugin: {e}")

    def test_load_invalid_plugin(self):
        print("\nTesting Invalid Plugin Rejection...")
        
        # Create a dummy invalid plugin file
        invalid_path = os.path.join(os.getcwd(), "tests", "invalid_plugin.py")
        with open(invalid_path, "w") as f:
            f.write("class BadPlugin:\n    pass\n")
            
        try:
            # Should restart capture/mock since load prints to stdout? No.
            # Just check return value.
            plugin = PluginLoader.load(invalid_path)
            self.assertIsNone(plugin, "Loader should return None for invalid plugins")
            print("✅ Invalid plugin rejected (returned None)")
        finally:
            if os.path.exists(invalid_path):
                os.remove(invalid_path)

if __name__ == "__main__":
    unittest.main()
