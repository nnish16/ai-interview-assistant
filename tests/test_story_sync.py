import unittest
from unittest.mock import MagicMock, patch
import os
import json
import sqlite3
import sys
import numpy as np

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.backend.story_engine import StoryEngine
from src.backend.database import DatabaseManager

class TestStorySync(unittest.TestCase):
    def setUp(self):
        self.db_path = "data/test_sync.db"
        self.json_path = "data/stories.json"

        # Setup clean state
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

        # Mock stories.json existence/content
        self.patcher = patch('src.backend.story_engine.STORIES_FILE', self.json_path)
        self.patcher.start()

        self.db = DatabaseManager(self.db_path)

        # Create dummy json
        with open(self.json_path, 'w') as f:
            json.dump([{"tag": "T1", "content": "C1", "style": "S1"}], f)

    def tearDown(self):
        self.db.get_connection().close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        if os.path.exists(self.json_path):
            os.remove(self.json_path)
        self.patcher.stop()

    def test_smart_sync(self):
        # 1. Initial Load
        engine = StoryEngine(self.db)
        # Mock model
        engine.model = MagicMock()
        # Return numpy array
        engine.model.encode.return_value = np.array([0.1]*384, dtype=np.float32)

        engine.load_stories_to_db()

        rows = self.db.get_all_stories()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][2], "C1")
        self.assertEqual(rows[0][3], "S1")

        # 2. Update JSON (Add story)
        with open(self.json_path, 'w') as f:
            json.dump([
                {"tag": "T1", "content": "C1", "style": "S1"},
                {"tag": "T2", "content": "C2", "style": "S2"}
            ], f)

        # 3. Trigger Sync
        engine.load_stories_to_db()

        rows = self.db.get_all_stories()
        self.assertEqual(len(rows), 2)
        # Verify content of second story
        tags = [r[1] for r in rows]
        self.assertIn("T2", tags)

if __name__ == '__main__':
    unittest.main()
