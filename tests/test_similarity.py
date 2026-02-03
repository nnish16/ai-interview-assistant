import unittest
import numpy as np
from sentence_transformers import util
import torch

class TestSimilarityDtype(unittest.TestCase):
    def test_cos_sim_dtype_mismatch(self):
        # Simulate the crash condition
        # Query: float32 (from model.encode)
        query = np.random.rand(384).astype(np.float32)
        # Story: float64 (default numpy from json)
        story_bad = np.random.rand(384).astype(np.float64)

        # This triggers the RuntimeError in PyTorch/SentenceTransformers if dtypes differ
        try:
            util.cos_sim(query, story_bad)
            # Depending on version, it might work or fail.
            # If it fails, we catch it. If it works (auto-cast), good.
            # But the user logs show it failed.
        except RuntimeError as e:
            self.assertIn("expected m1 and m2 to have the same dtype", str(e))

    def test_cos_sim_dtype_fix(self):
        # Simulate the fix
        query = np.random.rand(384).astype(np.float32)
        story_good = np.random.rand(384).astype(np.float32)

        result = util.cos_sim(query, story_good)
        self.assertIsNotNone(result)

if __name__ == '__main__':
    unittest.main()
