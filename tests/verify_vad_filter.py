
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

class TestVADFilter(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock()
        with patch('src.backend.llm_service.StoryEngine') as MockStoryEngine:
            self.service = LLMService(self.mock_db)
            self.service.groq_client = MagicMock()

    def test_short_input_filter(self):
        # Mock transcription result object
        mock_result = MagicMock()
        mock_result.text = "Hi" # Too short

        # When create is called, return this object (but actually the method returns object directly,
        # let's look at implementation: transcription = ...create(...) -> returns Text object or string?
        # Implementation returns the object from groq.
        # But wait, in the implementation we do: `transcription = ...create(..., response_format="text")`
        # If format is text, Groq returns a string directly?
        # The code logs `f"Transcription: {transcription}"`.
        # Let's assume it returns a string for simplicity of the test logic since we filter `transcription.strip()`.

        self.service.groq_client.audio.transcriptions.create.return_value = "Hi"

        result = self.service.transcribe(b'fake_audio')
        self.assertEqual(result, "[NOISE_FILTERED]")

    def test_valid_input_pass(self):
        self.service.groq_client.audio.transcriptions.create.return_value = "Tell me about yourself."

        result = self.service.transcribe(b'fake_audio')
        self.assertEqual(result, "Tell me about yourself.")

if __name__ == "__main__":
    from unittest.mock import patch
    unittest.main()
