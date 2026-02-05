
import unittest
from unittest.mock import MagicMock
import sys
import os

# Add repo root to path
sys.path.append(os.path.abspath("."))

# Mock dependencies
sys.modules["sentence_transformers"] = MagicMock()
sys.modules["groq"] = MagicMock()
sys.modules["openai"] = MagicMock()
sys.modules["zhipuai"] = MagicMock()
sys.modules["pypdf"] = MagicMock()

from src.backend.llm_service import LLMService

class TestPersona(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock()
        # Mock StoryEngine
        with patch('src.backend.llm_service.StoryEngine') as MockStoryEngine:
            self.service = LLMService(self.mock_db)
            self.service.story_engine = MockStoryEngine.return_value

    def test_default_prompt_contains_candidate_instruction(self):
        # We can't easily test the LLM output without a real API call or a very complex mock of the LLM logic.
        # But we CAN verify that the system prompt loaded into the service contains our critical instructions.

        prompt = self.service.system_prompt_base

        # Assert key phrases
        self.assertIn("You are the candidate", prompt)
        self.assertIn("Speak in the first person", prompt)
        self.assertIn("Do not give advice", prompt)
        self.assertIn("I have...", prompt)

if __name__ == "__main__":
    from unittest.mock import patch
    unittest.main()
