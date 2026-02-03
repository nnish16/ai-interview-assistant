import json
import os
import logging
import numpy as np
from sentence_transformers import SentenceTransformer, util
from src.backend.database import DatabaseManager

STORIES_FILE = "data/stories.json"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("StoryEngine")

class StoryEngine:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.model = None # Lazy load
        self.stories_cache = [] # List of dicts: {content, style, embedding}

    def initialize(self):
        """Initializes the model and syncs DB. Call this from a background thread."""
        logger.info("Initializing Story Engine...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.load_stories_to_db() # Smart Sync
        self.refresh_cache()
        logger.info("Story Engine Ready.")

    def load_stories_to_db(self):
        """Smart Sync: Loads stories from JSON to DB if counts differ."""
        rows = self.db.get_all_stories()

        if not os.path.exists(STORIES_FILE):
            logger.warning(f"{STORIES_FILE} not found. Creating dummy.")
            dummy_data = [{
                "tag": "Conflict",
                "content": "Example: I resolved a conflict by listening.",
                "style": "Be brief and professional."
            }]
            with open(STORIES_FILE, 'w') as f:
                json.dump(dummy_data, f, indent=4)

        try:
            with open(STORIES_FILE, 'r') as f:
                stories = json.load(f)

            # Check if sync needed
            if len(rows) != len(stories):
                logger.info(f"DB count ({len(rows)}) != JSON count ({len(stories)}). Re-syncing...")
                self.db.clear_stories()

                logger.info(f"Embedding {len(stories)} stories...")
                for story in stories:
                    embedding = self.model.encode(story['content'])
                    emb_json = json.dumps(embedding.tolist())
                    self.db.add_story(
                        story.get('tag', ''),
                        story['content'],
                        story.get('style', ''),
                        emb_json
                    )
                logger.info("Stories loaded to DB.")
            else:
                logger.info("DB is in sync with JSON.")

        except Exception as e:
            logger.error(f"Error loading stories: {e}")

    def refresh_cache(self):
        """Loads stories from DB into memory for fast retrieval."""
        rows = self.db.get_all_stories()
        self.stories_cache = []
        for r in rows:
            # r: id, tag, content, style, embedding_json
            try:
                emb = np.array(json.loads(r[4]), dtype=np.float32)
                self.stories_cache.append({
                    "content": r[2],
                    "style": r[3],
                    "embedding": emb,
                    "tag": r[1]
                })
            except Exception as e:
                logger.error(f"Error parsing story {r[0]}: {e}")
        logger.info(f"Story cache refreshed. {len(self.stories_cache)} stories active.")

    def find_relevant_story(self, query, threshold=0.4):
        """Finds the most relevant story for the query."""
        if not self.stories_cache or not self.model:
            return None

        query_emb = self.model.encode(query)

        best_match = None
        max_score = -1

        for story in self.stories_cache:
            score = util.cos_sim(query_emb, story['embedding']).item()
            if score > max_score:
                max_score = score
                best_match = story # Return whole dict (content + style)

        logger.info(f"Query: '{query}' | Best Score: {max_score:.3f}")

        if max_score >= threshold:
            return best_match
        return None
