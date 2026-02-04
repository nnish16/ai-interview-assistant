import json
import os
import logging
import numpy as np
import glob
from sentence_transformers import SentenceTransformer, util
from src.backend.database import DatabaseManager

STORIES_FILE = "data/stories.json"
DATA_DIR = "data"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("StoryEngine")

class StoryEngine:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.model = None # Lazy load
        self.stories_cache = [] # List of dicts: {content, style, embedding}
        self.story_embeddings_matrix = None # Tensor/Array of all embeddings

    def initialize(self):
        """Initializes the model and syncs DB. Call this from a background thread."""
        logger.info("Initializing Story Engine...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.load_stories_to_db() # Smart Sync
        self.refresh_cache()
        logger.info("Story Engine Ready.")

    def load_stories_to_db(self):
        """Smart Sync: Loads stories from JSON and text files to DB."""
        # 1. Load JSON Stories
        json_stories = []
        if os.path.exists(STORIES_FILE):
            try:
                with open(STORIES_FILE, 'r') as f:
                    json_stories = json.load(f)
            except Exception as e:
                logger.error(f"Error loading stories.json: {e}")
        else:
            logger.warning(f"{STORIES_FILE} not found. Creating dummy.")
            dummy_data = [{
                "tag": "Conflict",
                "content": "Example: I resolved a conflict by listening.",
                "style": "Be brief and professional."
            }]
            with open(STORIES_FILE, 'w') as f:
                json.dump(dummy_data, f, indent=4)
                json_stories = dummy_data

        # 2. Load Text/MD Files (Deep Research)
        text_stories = []
        text_files = glob.glob(os.path.join(DATA_DIR, "*.txt")) + glob.glob(os.path.join(DATA_DIR, "*.md"))

        for filepath in text_files:
            if os.path.basename(filepath) == "stories.json": continue

            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Simple chunking (e.g., by paragraphs or 500 chars)
                # For now, let's treat double newline as separator
                chunks = [c.strip() for c in content.split('\n\n') if c.strip()]

                tag = os.path.splitext(os.path.basename(filepath))[0]

                for chunk in chunks:
                    if len(chunk) < 50: continue # Skip tiny chunks
                    text_stories.append({
                        "tag": tag,
                        "content": chunk,
                        "style": "Reference Material"
                    })
            except Exception as e:
                logger.error(f"Error reading {filepath}: {e}")

        all_stories = json_stories + text_stories

        # Check against DB count
        # Note: This simple count check implies we rebuild if ANY file added/removed changes the count.
        # Ideally we'd hash checks, but for MVP this is fine.
        rows = self.db.get_all_stories()

        if len(rows) != len(all_stories):
            logger.info(f"DB count ({len(rows)}) != Source count ({len(all_stories)}). Re-syncing...")
            self.db.clear_stories()

            logger.info(f"Embedding {len(all_stories)} items...")

            # Batch encode
            contents = [story['content'] for story in all_stories]
            embeddings = self.model.encode(contents)

            # Prepare for bulk insert
            stories_data = []
            for story, embedding in zip(all_stories, embeddings):
                emb_json = json.dumps(embedding.tolist())
                stories_data.append((
                    story.get('tag', ''),
                    story['content'],
                    story.get('style', ''),
                    emb_json
                ))

            self.db.bulk_add_stories(stories_data)
            logger.info("Stories loaded to DB.")
        else:
            logger.info("DB is in sync with Source files.")

    def refresh_cache(self):
        """Loads stories from DB into memory for fast retrieval."""
        rows = self.db.get_all_stories()

        new_stories_cache = []
        embeddings_list = []

        for r in rows:
            # r: id, tag, content, style, embedding_json
            try:
                emb = np.array(json.loads(r[4]), dtype=np.float32)
                new_stories_cache.append({
                    "content": r[2],
                    "style": r[3],
                    "embedding": emb,
                    "tag": r[1]
                })
                embeddings_list.append(emb)
            except Exception as e:
                logger.error(f"Error parsing story {r[0]}: {e}")

        # Atomic assignment
        self.stories_cache = new_stories_cache
        if embeddings_list:
            self.story_embeddings_matrix = np.stack(embeddings_list)
        else:
            self.story_embeddings_matrix = None

        logger.info(f"Story cache refreshed. {len(self.stories_cache)} stories active.")

    def find_relevant_story(self, query, threshold=0.4):
        """Finds the most relevant story for the query."""
        if not self.stories_cache or not self.model or self.story_embeddings_matrix is None:
            return None

        query_emb = self.model.encode(query)

        # Vectorized similarity calculation
        # util.cos_sim returns a tensor (1, N)
        scores = util.cos_sim(query_emb, self.story_embeddings_matrix)[0]

        # Find best match
        best_idx = scores.argmax().item()
        max_score = scores[best_idx].item()

        logger.info(f"Query: '{query}' | Best Score: {max_score:.3f}")

        if max_score >= threshold:
            return self.stories_cache[best_idx]
        return None
