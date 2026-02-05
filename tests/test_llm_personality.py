
import unittest
from unittest.mock import MagicMock, patch, mock_open
import sys
import os

# Add repo root to path
sys.path.append(os.path.abspath("."))

# Mock dependencies before import
sys.modules["sentence_transformers"] = MagicMock()
sys.modules["groq"] = MagicMock()
sys.modules["openai"] = MagicMock()
sys.modules["zhipuai"] = MagicMock()
sys.modules["pypdf"] = MagicMock()

from src.backend.llm_service import LLMService

class TestLLMPersonality(unittest.TestCase):
    def setUp(self):
        self.mock_db_manager = MagicMock()
        # Mock StoryEngine
        with patch('src.backend.llm_service.StoryEngine') as MockStoryEngine:
            self.MockStoryEngine = MockStoryEngine
            self.mock_story_engine_instance = MockStoryEngine.return_value

    def test_default_personality(self):
        """Test that default system prompt is used when file does not exist."""
        # We need to ensure checks for personality.txt return False
        with patch('os.path.exists') as mock_exists:
             # Default fallback is False for everything
            mock_exists.return_value = False

            service = LLMService(self.mock_db_manager)

            expected_start = "You are the candidate"
            self.assertTrue(service.system_prompt_base.startswith(expected_start))

    def test_custom_personality(self):
        """Test that custom personality is loaded from file."""
        custom_prompt = "You are a pirate. Arrr!"

        with patch('os.path.exists') as mock_exists:
            # Return True for personality.txt
            def side_effect(path):
                if 'personality.txt' in str(path):
                    return True
                return False
            mock_exists.side_effect = side_effect

            with patch('builtins.open', mock_open(read_data=custom_prompt)):
                service = LLMService(self.mock_db_manager)
                # Check if it matches. Note: The current implementation DOES NOT have the feature yet,
                # so this test should FAIL.
                self.assertEqual(service.system_prompt_base, custom_prompt)

if __name__ == "__main__":
    unittest.main()
