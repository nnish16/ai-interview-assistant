
import unittest
from unittest.mock import MagicMock
import sys
import os
import sqlite3

# Add repo root
sys.path.append(os.path.abspath("."))

# Mock dependencies
sys.modules["sentence_transformers"] = MagicMock()
sys.modules["groq"] = MagicMock()
sys.modules["openai"] = MagicMock()
sys.modules["zhipuai"] = MagicMock()
sys.modules["pypdf"] = MagicMock()

from src.backend.story_engine import StoryEngine
from src.backend.database import DatabaseManager

class TestQAFeature(unittest.TestCase):
    def setUp(self):
        # Use a subfolder to satisfy os.makedirs logic
        self.test_db = "data/test_qa.db"
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

        self.db = DatabaseManager(self.test_db)
        self.engine = StoryEngine(self.db)

        # Mock the embedding model to return dummy vectors
        self.engine.model = MagicMock()
        import numpy as np
        # Return a random vector of size 384 (standard for MiniLM)
        self.engine.model.encode.return_value = np.random.rand(384).astype(np.float32)

    def tearDown(self):
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_add_and_retrieve_story(self):
        # 1. Add Story
        tag = "Challenge"
        content = "I faced a challenge and overcame it."
        style = "Heroic"

        self.engine.add_new_story(tag, content, style)

        # 2. Verify in DB
        rows = self.db.get_all_stories()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1], tag)
        self.assertEqual(rows[0][2], content)

        # 3. Verify in Cache
        self.assertEqual(len(self.engine.cache_bundle["stories"]), 1)
        self.assertEqual(self.engine.cache_bundle["stories"][0]["content"], content)

    def test_delete_story(self):
        # Add then delete
        self.engine.add_new_story("DeleteMe", "Content", "Style")
        rows = self.db.get_all_stories()
        sid = rows[0][0]

        self.engine.delete_story(sid)

        rows = self.db.get_all_stories()
        self.assertEqual(len(rows), 0)
        self.assertEqual(len(self.engine.cache_bundle["stories"]), 0)

if __name__ == "__main__":
    unittest.main()
