import unittest
from unittest.mock import MagicMock
import sys
import os
from PyQt6.QtWidgets import QApplication, QWidget

# Ensure QApplication exists
app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.ui.overlay import OverlayWindow

class TestOverlayOptimization(unittest.TestCase):
    def setUp(self):
        self.overlay = OverlayWindow()
        # Mock the audio_bar_fill widget to track setStyleSheet calls
        self.overlay.audio_bar_fill = MagicMock(spec=QWidget)
        # We also need to mock width() since update_audio_level uses it
        self.overlay.audio_bar = MagicMock(spec=QWidget)
        self.overlay.audio_bar.width.return_value = 100

    def test_update_audio_level_optimization(self):
        # 1. Initial call (Tier 0: < 0.5)
        self.overlay.update_audio_level(0.1)
        # Should set width and style
        self.overlay.audio_bar_fill.setFixedWidth.assert_called()
        self.overlay.audio_bar_fill.setStyleSheet.assert_called_once()
        self.overlay.audio_bar_fill.setStyleSheet.reset_mock()

        # 2. Same Tier call (Tier 0: < 0.5)
        self.overlay.update_audio_level(0.2)
        # Should set width
        self.overlay.audio_bar_fill.setFixedWidth.assert_called()
        # BUT should NOT set style again (optimization target)
        # Note: Currently the code IS calling it, so this test will FAIL until I implement the fix.
        # This confirms TDD approach.

        # For now, I'll assert that it IS called to match current behavior,
        # then I will update the test to assert NOT called after I fix it?
        # No, I should write the test for the DESIRED behavior (optimization) and let it fail.
        # But wait, if I run it now it will fail. That's good.

        pass

    def test_optimization_logic(self):
        """
        This test expects the OPTIMIZED behavior.
        """
        # Reset state if any (though initialized fresh in setUp)

        # 1. Low level (Green)
        self.overlay.update_audio_level(0.1)
        self.overlay.audio_bar_fill.setStyleSheet.assert_called()
        call_args_1 = self.overlay.audio_bar_fill.setStyleSheet.call_args[0][0]
        self.assertIn("#4CAF50", call_args_1) # Check for green color code
        self.overlay.audio_bar_fill.setStyleSheet.reset_mock()

        # 2. Another low level -> Should NOT call setStyleSheet
        self.overlay.update_audio_level(0.2)
        self.overlay.audio_bar_fill.setStyleSheet.assert_not_called()

        # 3. Medium level (Orange) -> Should call
        self.overlay.update_audio_level(0.6)
        self.overlay.audio_bar_fill.setStyleSheet.assert_called_once()
        call_args_3 = self.overlay.audio_bar_fill.setStyleSheet.call_args[0][0]
        self.assertIn("#FFC107", call_args_3) # Orange
        self.overlay.audio_bar_fill.setStyleSheet.reset_mock()

        # 4. Another medium level -> Should NOT call
        self.overlay.update_audio_level(0.7)
        self.overlay.audio_bar_fill.setStyleSheet.assert_not_called()

        # 5. High level (Red) -> Should call
        self.overlay.update_audio_level(0.9)
        self.overlay.audio_bar_fill.setStyleSheet.assert_called_once()
        call_args_5 = self.overlay.audio_bar_fill.setStyleSheet.call_args[0][0]
        self.assertIn("#FF5722", call_args_5) # Red
        self.overlay.audio_bar_fill.setStyleSheet.reset_mock()

        # 6. Another high level -> Should NOT call
        self.overlay.update_audio_level(0.85)
        self.overlay.audio_bar_fill.setStyleSheet.assert_not_called()

        # 7. Back to Low -> Should call
        self.overlay.update_audio_level(0.1)
        self.overlay.audio_bar_fill.setStyleSheet.assert_called_once()
        call_args_7 = self.overlay.audio_bar_fill.setStyleSheet.call_args[0][0]
        self.assertIn("#4CAF50", call_args_7)

if __name__ == '__main__':
    unittest.main()
