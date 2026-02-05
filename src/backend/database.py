import sqlite3
import datetime
import os
import logging

DB_FILE = "data/cluely.db"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DatabaseManager")

class DatabaseManager:
    def __init__(self, db_path=DB_FILE):
        self.db_path = db_path
        # Ensure data dir exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        """Initialize database tables."""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Interviews table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS interviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                duration TEXT
            )
        ''')

        # Transcripts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transcripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                interview_id INTEGER,
                role TEXT,
                content TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(interview_id) REFERENCES interviews(id)
            )
        ''')

        # Stories table
        # We handle migration naively for MVP by checking if style column exists or recreating
        # But simpler: rely on StoryEngine to clear table if sync needed.
        # Here we just ensure the CREATE statement has the column.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tag TEXT,
                content TEXT,
                style TEXT,
                embedding BLOB
            )
        ''')
        # Note: Embedding stored as BLOB for performance.

        conn.commit()
        conn.close()
        logger.info("Database initialized.")

    def create_interview(self):
        """Creates a new interview session and returns its ID."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO interviews (date) VALUES (CURRENT_TIMESTAMP)')
        interview_id = cursor.lastrowid
        conn.commit()
        conn.close()
        logger.info(f"Created interview session: {interview_id}")
        return interview_id

    def save_transcript(self, interview_id, role, content):
        """Saves a message to the transcript."""
        if not interview_id:
            logger.warning("No interview ID provided, skipping save.")
            return

        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO transcripts (interview_id, role, content)
            VALUES (?, ?, ?)
        ''', (interview_id, role, content))
        conn.commit()
        conn.close()
        logger.debug(f"Saved transcript for {role}")

    def delete_last_transcript(self, interview_id, role):
        """Deletes the most recent transcript entry for a specific role and interview."""
        if not interview_id:
            return

        conn = self.get_connection()
        cursor = conn.cursor()
        # Find the max ID for this interview and role
        cursor.execute('''
            DELETE FROM transcripts
            WHERE id = (
                SELECT MAX(id) FROM transcripts
                WHERE interview_id = ? AND role = ?
            )
        ''', (interview_id, role))

        if cursor.rowcount > 0:
            logger.info(f"Deleted last transcript for {role} (Interview {interview_id})")
        else:
            logger.warning(f"No transcript found to delete for {role} (Interview {interview_id})")

        conn.commit()
        conn.close()

    def add_story(self, tag, content, style, embedding_json):
        """Adds a story with its embedding."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO stories (tag, content, style, embedding)
            VALUES (?, ?, ?, ?)
        ''', (tag, content, style, embedding_json))
        conn.commit()
        conn.close()

    def bulk_add_stories(self, stories_data):
        """
        Adds multiple stories in a single transaction.
        stories_data: List of tuples (tag, content, style, embedding_json)
        """
        if not stories_data:
            return

        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.executemany('''
                INSERT INTO stories (tag, content, style, embedding)
                VALUES (?, ?, ?, ?)
            ''', stories_data)
            conn.commit()
            logger.info(f"Bulk added {len(stories_data)} stories.")
        except Exception as e:
            logger.error(f"Error in bulk_add_stories: {e}")
            conn.rollback()
        finally:
            conn.close()

    def get_story_count(self):
        """Returns the number of stories in the database."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT COUNT(*) FROM stories')
            count = cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Error getting story count: {e}")
            count = 0
        finally:
            conn.close()
        return count

    def get_all_stories(self):
        """Returns list of (id, tag, content, style, embedding)."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT id, tag, content, style, embedding FROM stories')
        except sqlite3.OperationalError:
            # Fallback for old schema if migration didn't run (or handle migration here)
            # For MVP, we will rely on StoryEngine clearing the table if needed
            # But query might fail. Let's return minimal columns if style missing?
            # Or just fail. Main plan says StoryEngine handles sync.
            # If table exists but misses column, query fails.
            # We should probably force recreation if needed or use * and parse.
            # Let's assume we will drop/create in StoryEngine logic or manual intervention.
            # Or better: alter table.
            try:
                cursor.execute('ALTER TABLE stories ADD COLUMN style TEXT')
                cursor.execute('SELECT id, tag, content, style, embedding FROM stories')
            except Exception:
                # If alter fails (maybe already exists?), try select again or re-raise
                cursor.execute('SELECT id, tag, content, style, embedding FROM stories')

        rows = cursor.fetchall()
        conn.close()
        return rows

    def clear_stories(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM stories')
        conn.commit()
        conn.close()

    def recreate_stories_table(self):
        """Drops and recreates the stories table to ensure correct schema."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DROP TABLE IF EXISTS stories')
        cursor.execute('''
            CREATE TABLE stories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tag TEXT,
                content TEXT,
                style TEXT,
                embedding BLOB
            )
        ''')
        conn.commit()
        conn.close()
        logger.info("Recreated stories table.")
