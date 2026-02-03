import unittest
from unittest.mock import MagicMock, patch
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.backend.llm_service import LLMService

class TestLLMFallback(unittest.TestCase):
    def setUp(self):
        # Mock dependencies
        self.mock_db = MagicMock()
        self.service = LLMService(self.mock_db, groq_key="test", openrouter_key="test")
        self.service.or_client = MagicMock()
        self.service.story_engine = MagicMock()
        self.service.story_engine.find_relevant_story.return_value = None

    def test_fallback_success_first_try(self):
        # Setup mock to succeed immediately
        mock_chunk = MagicMock()
        mock_chunk.choices = [MagicMock()]
        mock_chunk.choices[0].delta.content = "Success"
        self.service.or_client.chat.completions.create.return_value = [mock_chunk]

        gen = self.service.generate_answer("test")
        result = list(gen)

        self.assertEqual(result, ["Success"])
        # Should be called once
        self.assertEqual(self.service.or_client.chat.completions.create.call_count, 1)

    def test_fallback_failure_then_success(self):
        # Setup mock to fail once then succeed
        mock_chunk = MagicMock()
        mock_chunk.choices = [MagicMock()]
        mock_chunk.choices[0].delta.content = "Success on second"

        # Side effect: First call raises Exception, Second returns iterator
        self.service.or_client.chat.completions.create.side_effect = [
            Exception("404 Not Found"),
            [mock_chunk]
        ]

        gen = self.service.generate_answer("test")
        result = list(gen)

        self.assertEqual(result, ["Success on second"])
        # Should be called twice
        self.assertEqual(self.service.or_client.chat.completions.create.call_count, 2)

    def test_all_fail(self):
        # Setup mock to always fail
        self.service.or_client.chat.completions.create.side_effect = Exception("Error")

        gen = self.service.generate_answer("test")
        result = list(gen)

        self.assertIn("Connection unstable", result[0])
        # Called 5 times (length of FREE_MODELS)
        self.assertEqual(self.service.or_client.chat.completions.create.call_count, 5)

if __name__ == '__main__':
    unittest.main()
