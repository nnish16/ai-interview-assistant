import unittest
from unittest.mock import MagicMock
import numpy as np
import sys
import os

# Mock sounddevice/webrtcvad if needed, but webrtcvad-wheels works in sandbox
# sounddevice requires PortAudio, so we mock it.
sys.modules['sounddevice'] = MagicMock()

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.backend.audio_stream import AudioService

class TestAudioVisualizer(unittest.TestCase):
    def setUp(self):
        self.service = AudioService()
        self.service.audio_level = MagicMock()

    def test_rms_calculation(self):
        # Create a frame with known amplitude
        # Full scale sine wave is too complex to generate perfectly quickly,
        # so let's use constant values.

        # 1. Silence
        silence = np.zeros(320, dtype='int16')
        self.service._process_frame(silence)
        # RMS should be 0
        self.service.audio_level.emit.assert_called_with(0.0)

        # 2. Max Volume
        # int16 max is 32767.
        # RMS of constant 32767 is 32767.
        # Our logic: level = min(rms / 10000.0, 1.0)
        # 32767 / 10000 > 1.0 -> should be 1.0
        loud = np.full(320, 32767, dtype='int16')
        self.service._process_frame(loud)
        self.service.audio_level.emit.assert_called_with(1.0)

        # 3. Mid Volume (approx 5000)
        # 5000 / 10000 = 0.5
        mid = np.full(320, 5000, dtype='int16')
        self.service._process_frame(mid)
        self.service.audio_level.emit.assert_called_with(0.5)

if __name__ == '__main__':
    unittest.main()
