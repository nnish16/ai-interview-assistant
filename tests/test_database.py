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

if __name__ == '__main__':
    unittest.main()
