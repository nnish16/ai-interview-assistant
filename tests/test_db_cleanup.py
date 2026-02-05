
import unittest
from unittest.mock import MagicMock
import sqlite3
import os
import sys

# Add repo root to path
sys.path.append(os.path.abspath("."))

from src.backend.database import DatabaseManager

class TestDatabaseCleanup(unittest.TestCase):
    def setUp(self):
        # Use a path with a directory to satisfy os.makedirs logic in DatabaseManager
        self.test_db = "data/test_cleanup.db"
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        self.db_manager = DatabaseManager(self.test_db)
        self.interview_id = self.db_manager.create_interview()

    def tearDown(self):
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_delete_last_transcript(self):
        # Insert User -> AI -> User -> AI
        self.db_manager.save_transcript(self.interview_id, "user", "Q1")
        self.db_manager.save_transcript(self.interview_id, "ai", "A1")
        self.db_manager.save_transcript(self.interview_id, "user", "Q2")
        self.db_manager.save_transcript(self.interview_id, "ai", "A2")

        # Verify initial count
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM transcripts WHERE interview_id=?", (self.interview_id,))
        self.assertEqual(cursor.fetchone()[0], 4)

        # Delete last AI
        self.db_manager.delete_last_transcript(self.interview_id, "ai")

        # Verify count is 3 and A2 is gone (but A1 remains)
        cursor.execute("SELECT COUNT(*) FROM transcripts WHERE interview_id=?", (self.interview_id,))
        self.assertEqual(cursor.fetchone()[0], 3)

        cursor.execute("SELECT content FROM transcripts WHERE interview_id=? ORDER BY id DESC LIMIT 1", (self.interview_id,))
        last_content = cursor.fetchone()[0]
        self.assertEqual(last_content, "Q2") # Last item is now Q2

        conn.close()

if __name__ == "__main__":
    unittest.main()
