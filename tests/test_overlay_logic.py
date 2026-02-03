import unittest
from unittest.mock import MagicMock
import sys
import os
from PyQt6.QtWidgets import QApplication

# Ensure QApplication exists
app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.ui.overlay import OverlayWindow, ConversationItem

class TestOverlayLogic(unittest.TestCase):
    def setUp(self):
        self.overlay = OverlayWindow()

    def test_conversation_item(self):
        item = ConversationItem("You", "Hello")
        self.assertEqual(item.role_label.text(), "YOU")
        self.assertEqual(item.text_label.text(), "Hello")

        item.append_text(" World")
        self.assertEqual(item.text_label.text(), "Hello World")

    def test_add_transcription(self):
        self.overlay.add_transcription("Test Question")
        # Check if widget added to layout
        # content_layout has a stretch at 0, so item is at 1
        item = self.overlay.content_layout.itemAt(1).widget()
        self.assertIsInstance(item, ConversationItem)
        self.assertEqual(item.role_label.text(), "YOU")
        self.assertEqual(item.text_label.text(), "Test Question")

    def test_add_answer_chunk(self):
        self.overlay.add_answer_chunk("Part 1")
        item = self.overlay.current_ai_item
        self.assertIsNotNone(item)
        self.assertEqual(item.text_label.text(), "Part 1")

        self.overlay.add_answer_chunk(" Part 2")
        self.assertEqual(item.text_label.text(), "Part 1 Part 2")

if __name__ == '__main__':
    unittest.main()
