import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import numpy as np

# Mock sounddevice BEFORE importing the module
sys.modules['sounddevice'] = MagicMock()

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.backend.audio_stream import AudioService

class TestAudioService(unittest.TestCase):
    def setUp(self):
        self.service = AudioService()
        # Mock the signals directly on the instance to verify calls
        # Note: In PyQt, signals are descriptors on the class.
        # But we can monkeypatch the instance attribute to be a Mock.
        self.service.speaking_started = MagicMock()
        self.service.speaking_stopped = MagicMock()
        self.service.audio_captured = MagicMock()

    def test_vad_logic(self):
        # Create a frame of silence
        frame_len = 320
        silence_frame = np.zeros(frame_len, dtype='int16')

        # Mock VAD
        self.service.vad = MagicMock()

        # 1. Feed speech
        self.service.vad.is_speech.return_value = True
        self.service._process_frame(silence_frame)

        self.service.speaking_started.emit.assert_called_once()
        self.assertTrue(self.service.is_speaking)

        # 2. Feed more speech
        self.service._process_frame(silence_frame)
        self.service.speaking_started.emit.assert_called_once() # count stays 1

        # 3. Feed silence
        self.service.vad.is_speech.return_value = False
        self.service._process_frame(silence_frame)
        self.service.speaking_stopped.emit.assert_not_called()

        # 4. Feed silence until max_silence_frames is reached
        # max_silence_frames is calculated in __init__.
        # With default 500ms and 20ms frame -> 25 frames.
        # We already fed 1 silence frame.
        for _ in range(30):
            self.service._process_frame(silence_frame)

        self.service.speaking_stopped.emit.assert_called_once()
        self.service.audio_captured.emit.assert_called_once()

if __name__ == '__main__':
    unittest.main()
