import unittest
import os
import sys
import json

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.backend.config import load_config, save_config, CONFIG_FILE

class TestConfig(unittest.TestCase):
    def setUp(self):
        # Backup existing config if any
        if os.path.exists(CONFIG_FILE):
            os.rename(CONFIG_FILE, CONFIG_FILE + ".bak")

    def tearDown(self):
        # Restore config
        if os.path.exists(CONFIG_FILE):
            os.remove(CONFIG_FILE)
        if os.path.exists(CONFIG_FILE + ".bak"):
            os.rename(CONFIG_FILE + ".bak", CONFIG_FILE)

    def test_save_and_load(self):
        data = {"test": 123, "foo": "bar"}
        save_config(data)

        loaded = load_config()
        self.assertEqual(loaded['test'], 123)
        self.assertEqual(loaded['foo'], "bar")

    def test_default_load(self):
        # Ensure it returns default if no file
        loaded = load_config()
        self.assertIn("audio_device", loaded)
        self.assertIn("groq_api_key", loaded)

if __name__ == '__main__':
    unittest.main()
