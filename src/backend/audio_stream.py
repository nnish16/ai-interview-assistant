import sounddevice as sd
import numpy as np
import webrtcvad
import threading
import queue
import logging
import sys
from PyQt6.QtCore import QObject, pyqtSignal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AudioStream")

class AudioService(QObject):
    """
    Handles audio recording, VAD (Voice Activity Detection), and emits audio chunks for transcription.
    """
    audio_captured = pyqtSignal(bytes)  # Signal emitting raw WAV data or PCM bytes
    speaking_started = pyqtSignal()
    speaking_stopped = pyqtSignal()

    def __init__(self, sample_rate=16000, frame_duration_ms=20, vad_aggressiveness=3):
        super().__init__()
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.vad = webrtcvad.Vad(vad_aggressiveness)
        self.device_index = None
        self.running = False
        self.stream = None
        self.buffer = queue.Queue()
        self.frame_size = int(sample_rate * frame_duration_ms / 1000)

        # VAD state
        self.is_speaking = False
        self.silence_frames = 0
        self.speech_frames = []
        self.max_silence_duration_ms = 500  # 500ms silence to consider utterance done
        self.min_speech_duration_ms = 300   # Minimum 300ms to consider it speech (avoid clicks)

        # Calculate silence threshold in frames
        self.max_silence_frames = int(self.max_silence_duration_ms / frame_duration_ms)
        self.min_speech_frames = int(self.min_speech_duration_ms / frame_duration_ms)

    def list_devices(self):
        """Returns a list of input devices."""
        try:
            devices = sd.query_devices()
            input_devices = []
            for i, dev in enumerate(devices):
                if dev['max_input_channels'] > 0:
                    input_devices.append({'index': i, 'name': dev['name']})
            return input_devices
        except Exception as e:
            logger.error(f"Error listing devices: {e}")
            return []

    def set_device(self, device_index):
        """Sets the input device index."""
        self.device_index = device_index
        logger.info(f"Audio device set to index: {device_index}")

    def _audio_callback(self, indata, frames, time, status):
        """Callback for sounddevice."""
        if status:
            logger.warning(f"Audio callback status: {status}")
        self.buffer.put(indata.copy())

    def start(self):
        """Starts the audio stream."""
        if self.running:
            return

        if self.device_index is None:
            # Try to find a default or BlackHole
            devices = self.list_devices()
            blackhole = next((d for d in devices if "BlackHole" in d['name']), None)
            if blackhole:
                self.device_index = blackhole['index']
            else:
                # Default to system default if available, else 0
                self.device_index = sd.default.device[0]

        self.running = True
        self.thread = threading.Thread(target=self._process_loop)
        self.thread.start()
        logger.info("Audio service started.")

    def stop(self):
        """Stops the audio stream."""
        self.running = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
        if hasattr(self, 'thread') and self.thread.is_alive():
            self.thread.join()
        logger.info("Audio service stopped.")

    def _process_loop(self):
        """Loop to read buffer, process VAD, and manage state."""
        # Open stream
        try:
            with sd.InputStream(device=self.device_index,
                                channels=1,
                                samplerate=self.sample_rate,
                                dtype='int16',
                                blocksize=self.frame_size,
                                callback=self._audio_callback):
                logger.info(f"Stream opened on device {self.device_index}")

                while self.running:
                    try:
                        # sounddevice callback puts data in queue.
                        # We assume blocksize matches frame_size so we get exact frames.
                        frame = self.buffer.get(timeout=1.0)
                        self._process_frame(frame)
                    except queue.Empty:
                        continue
        except Exception as e:
            logger.error(f"Error in audio stream: {e}")
            # If we can't open the stream (e.g. sandbox), we might simulate or just log
            pass

    def _process_frame(self, frame):
        """Process a single audio frame with VAD."""
        # webrtcvad expects bytes
        frame_bytes = frame.tobytes()

        try:
            is_speech = self.vad.is_speech(frame_bytes, self.sample_rate)
        except Exception as e:
            logger.error(f"VAD error: {e}")
            return

        if is_speech:
            if not self.is_speaking:
                # Potential start of speech
                self.is_speaking = True
                self.speaking_started.emit()
                logger.debug("Speech started")

            self.speech_frames.append(frame_bytes)
            self.silence_frames = 0
        else:
            if self.is_speaking:
                self.speech_frames.append(frame_bytes)
                self.silence_frames += 1

                if self.silence_frames > self.max_silence_frames:
                    # Speech ended
                    self.is_speaking = False
                    self.speaking_stopped.emit()
                    logger.debug("Speech ended")

                    # Check if utterance was long enough
                    if len(self.speech_frames) >= self.min_speech_frames:
                        full_audio = b''.join(self.speech_frames)
                        self.audio_captured.emit(full_audio)
                        logger.info(f"Captured utterance: {len(full_audio)} bytes")

                    self.speech_frames = []
                    self.silence_frames = 0

if __name__ == "__main__":
    # Simple test if run directly
    import time

    def on_audio(data):
        print(f"Received audio chunk: {len(data)} bytes")

    service = AudioService()
    print("Devices:", service.list_devices())
    service.audio_captured.connect(on_audio)

    # Mocking start for sandbox if no device
    # service.start()
    # time.sleep(5)
    # service.stop()
