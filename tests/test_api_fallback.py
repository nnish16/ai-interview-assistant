import unittest
from unittest.mock import MagicMock, patch
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.backend.llm_service import LLMService

class TestAPIKeyFallback(unittest.TestCase):
    def test_fallback_to_env(self):
        # Mock os.getenv to return a dummy key
        with patch.dict(os.environ, {"GROQ_API_KEY": "env_key"}):
            # Pass empty string as key (simulating config.json default)
            service = LLMService(db_manager=None, groq_key="")
            self.assertEqual(service.groq_key, "env_key")
            self.assertIsNotNone(service.groq_client)

    def test_priority_of_arg(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": "env_key"}):
            service = LLMService(db_manager=None, groq_key="arg_key")
            self.assertEqual(service.groq_key, "arg_key")

if __name__ == '__main__':
    unittest.main()
