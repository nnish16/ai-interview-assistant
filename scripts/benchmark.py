import sys
import os
import time
import json
import sqlite3
import numpy as np
import logging

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Suppress logging for benchmark
logging.getLogger("StoryEngine").setLevel(logging.WARNING)
logging.getLogger("DatabaseManager").setLevel(logging.WARNING)

from src.backend.database import DatabaseManager
from src.backend.story_engine import StoryEngine

DB_PATH = "data/benchmark.db"
NUM_STORIES = 5000
EMBEDDING_DIM = 384

def setup_data_blob(db_manager):
    print(f"Generating {NUM_STORIES} stories with BLOB embeddings...")
    data = []
    # Generate random matrix
    matrix = np.random.rand(NUM_STORIES, EMBEDDING_DIM).astype(np.float32)

    for i in range(NUM_STORIES):
        emb_blob = matrix[i].tobytes()
        data.append((f"tag_{i}", f"content_{i}", "style", emb_blob))

    db_manager.bulk_add_stories(data)

def benchmark():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    db = DatabaseManager(DB_PATH)
    engine = StoryEngine(db)

    # Pre-populate DB with optimized data
    setup_data_blob(db)

    print("Starting benchmark for refresh_cache (Optimized)...")
    start_time = time.time()
    engine.refresh_cache()
    end_time = time.time()

    duration = end_time - start_time
    print(f"Time taken: {duration:.4f} seconds")
    print(f"Stories loaded: {len(engine.cache_bundle['stories'])}")

    # Cleanup
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

if __name__ == "__main__":
    benchmark()
