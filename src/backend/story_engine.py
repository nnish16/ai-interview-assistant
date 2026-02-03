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
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.stories_cache = [] # List of dicts: {content, embedding}

        self.load_stories_to_db()
        self.refresh_cache()

    def load_stories_to_db(self):
        """Loads stories from JSON to DB if DB is empty."""
        rows = self.db.get_all_stories()
        if rows:
            logger.info(f"DB already has {len(rows)} stories. Skipping initial load.")
            return

        if not os.path.exists(STORIES_FILE):
            logger.warning(f"{STORIES_FILE} not found. Creating dummy.")
            dummy_data = [{
                "tag": "Conflict",
                "content": "Example: I resolved a conflict by listening."
            }]
            with open(STORIES_FILE, 'w') as f:
                json.dump(dummy_data, f, indent=4)

        try:
            with open(STORIES_FILE, 'r') as f:
                stories = json.load(f)

            logger.info(f"Embedding {len(stories)} stories...")
            for story in stories:
                embedding = self.model.encode(story['content'])
                # Store as list/json string
                emb_json = json.dumps(embedding.tolist())
                self.db.add_story(story.get('tag', ''), story['content'], emb_json)

            logger.info("Stories loaded to DB.")
        except Exception as e:
            logger.error(f"Error loading stories: {e}")

    def refresh_cache(self):
        """Loads stories from DB into memory for fast retrieval."""
        rows = self.db.get_all_stories()
        self.stories_cache = []
        for r in rows:
            # r: id, tag, content, embedding_json
            try:
                emb = np.array(json.loads(r[3]), dtype=np.float32)
                self.stories_cache.append({
                    "content": r[2],
                    "embedding": emb,
                    "tag": r[1]
                })
            except Exception as e:
                logger.error(f"Error parsing story {r[0]}: {e}")
        logger.info(f"Story cache refreshed. {len(self.stories_cache)} stories active.")

    def find_relevant_story(self, query, threshold=0.4):
        """Finds the most relevant story for the query."""
        if not self.stories_cache:
            return None

        query_emb = self.model.encode(query)

        best_story = None
        max_score = -1

        for story in self.stories_cache:
            score = util.cos_sim(query_emb, story['embedding']).item()
            if score > max_score:
                max_score = score
                best_story = story['content']

        logger.info(f"Query: '{query}' | Best Score: {max_score:.3f}")

        if max_score >= threshold:
            return best_story
        return None
