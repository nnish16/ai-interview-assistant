
import unittest
from unittest.mock import MagicMock, patch
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
sys.modules["PyQt6.QtCore"] = MagicMock()
sys.modules["PyQt6.QtWidgets"] = MagicMock()
sys.modules["PyQt6.QtGui"] = MagicMock()

# Partial mock for things we need to test logic
from src.backend.llm_service import LLMService

class TestRegenerationLogic(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock()
        # Mock StoryEngine
        with patch('src.backend.llm_service.StoryEngine') as MockStoryEngine:
            self.service = LLMService(self.mock_db)
            self.service.story_engine = MockStoryEngine.return_value

    def test_undo_last_turn(self):
        # Setup history
        self.service.transcript_history = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"}
        ]

        # Action
        user_query = self.service.undo_last_turn()

        # Assertions
        self.assertEqual(user_query, "Q2")
        self.assertEqual(len(self.service.transcript_history), 2)
        self.assertEqual(self.service.transcript_history[-1]['content'], "A1")

    def test_undo_empty(self):
        self.service.transcript_history = []
        res = self.service.undo_last_turn()
        self.assertIsNone(res)

    def test_generate_with_instruction(self):
        # We need to mock the client to see what it receives
        self.service.zhipu_client = MagicMock()

        self.service.generate_answer("Q3", system_instruction="Make it pop")

        # The generator must be consumed to trigger the call
        gen = self.service.generate_answer("Q3", system_instruction="Make it pop")
        try:
            next(gen)
        except StopIteration:
            pass

        # Check calls
        calls = self.service.zhipu_client.chat.completions.create.call_args
        # args, kwargs
        _, kwargs = calls
        messages = kwargs['messages']

        # Check if instruction is in messages
        has_instruction = any(m['role'] == 'system' and m['content'] == "Make it pop" for m in messages)
        self.assertTrue(has_instruction)

if __name__ == "__main__":
    unittest.main()
