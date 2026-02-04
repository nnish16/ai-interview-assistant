import unittest
import os
import sqlite3
import shutil
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.backend.database import DatabaseManager

class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.test_db = "data/test_cluely.db"
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        self.db = DatabaseManager(self.test_db)

    def tearDown(self):
        self.db.get_connection().close()
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_tables_created(self):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        self.assertIn('interviews', tables)
        self.assertIn('transcripts', tables)
        self.assertIn('stories', tables)

    def test_create_interview(self):
        id = self.db.create_interview()
        self.assertIsNotNone(id)

        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM interviews WHERE id=?", (id,))
        self.assertIsNotNone(cursor.fetchone())

    def test_save_transcript(self):
        id = self.db.create_interview()
        self.db.save_transcript(id, "user", "Hello")

        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT content FROM transcripts WHERE interview_id=?", (id,))
        row = cursor.fetchone()
        self.assertEqual(row[0], "Hello")

    def test_get_story_count(self):
        # Initial count should be 0
        self.assertEqual(self.db.get_story_count(), 0)

        # Add stories
        self.db.add_story("tag1", "content1", "style1", "[]")
        self.db.add_story("tag2", "content2", "style2", "[]")

        self.assertEqual(self.db.get_story_count(), 2)

        # Clear
        self.db.clear_stories()
        self.assertEqual(self.db.get_story_count(), 0)

if __name__ == '__main__':
    unittest.main()
