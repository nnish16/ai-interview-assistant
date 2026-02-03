import sys
import threading
from PyQt6.QtWidgets import QApplication, QMessageBox, QDialog
from PyQt6.QtCore import QObject, pyqtSignal, QThread

from src.backend.audio_stream import AudioService
from src.backend.llm_service import LLMService
from src.backend.config import load_config
from src.ui.wizard import SetupWizard
from src.ui.settings import SettingsDialog
from src.ui.overlay import OverlayWindow

class LLMWorker(QObject):
    """Worker to handle blocking LLM calls."""
    stream_chunk = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, llm_service, audio_bytes):
        super().__init__()
        self.llm_service = llm_service
        self.audio_bytes = audio_bytes

    def run(self):
        # 1. Transcribe
        transcription_obj = self.llm_service.transcribe(self.audio_bytes)
        if hasattr(transcription_obj, 'text'):
            text = transcription_obj.text
        else:
            text = str(transcription_obj) # Error string

        # 2. Generate
        self.stream_chunk.emit(f"\n[You]: {text}\n[AI]: ")

        for chunk in self.llm_service.generate_answer(text):
            self.stream_chunk.emit(chunk)

        self.finished.emit()

class ReportWorker(QObject):
    finished = pyqtSignal()

    def __init__(self, service):
        super().__init__()
        self.service = service

    def run(self):
        self.service.generate_report()
        self.finished.emit()

class MainController(QObject):
    def __init__(self):
        super().__init__()
        self.config = load_config()

        # UI
        self.overlay = OverlayWindow()
        self.overlay.request_settings.connect(self.open_settings)
        self.overlay.toggle_listening.connect(self.handle_listening_toggle)
        self.overlay.end_interview.connect(self.handle_end_interview)

        # Backend
        self.llm_service = LLMService(
            groq_key=self.config.get("groq_api_key"),
            openrouter_key=self.config.get("openrouter_api_key")
        )
        # Load context if available
        self.reload_context()

        self.audio_service = AudioService()
        self.audio_service.speaking_started.connect(self.on_speech_start)
        self.audio_service.speaking_stopped.connect(self.on_speech_stop)
        self.audio_service.audio_captured.connect(self.on_audio_captured)
        self.audio_service.audio_level.connect(self.overlay.update_audio_level)

        self.worker_thread = None

        # Apply audio device config
        self.apply_audio_config()

        self.report_thread = None

        # Show overlay
        self.overlay.show()

    def apply_audio_config(self):
        dev_idx = self.config.get("audio_device_index")
        if dev_idx is not None:
            # Verify if index is valid or find by name (omitted for brevity, trusting index or wizard)
            self.audio_service.set_device(dev_idx)

    def reload_context(self):
        resume = self.config.get("resume_path")
        jd = self.config.get("job_description")
        self.llm_service.load_context(resume, jd)
        # Also update keys in case they changed
        self.llm_service.update_keys(
            self.config.get("groq_api_key"),
            self.config.get("openrouter_api_key")
        )

    def open_settings(self):
        dlg = SettingsDialog()
        dlg.config_updated.connect(self.reload_context)
        dlg.exec()

    def handle_listening_toggle(self, should_listen):
        if should_listen:
            self.audio_service.start()
            self.overlay.set_status("listening")
        else:
            self.audio_service.stop()
            self.overlay.set_status("idle")

    def on_speech_start(self):
        self.overlay.set_status("listening")

    def on_speech_stop(self):
        self.overlay.set_status("processing")

    def handle_end_interview(self):
        # Prevent double triggering
        try:
            if self.report_thread and self.report_thread.isRunning():
                return
        except RuntimeError:
            self.report_thread = None

        self.audio_service.stop()
        self.overlay.set_status("processing")
        self.overlay.set_full_text("Generating interview report... Please wait.")

        self.report_thread = QThread()
        self.report_worker = ReportWorker(self.llm_service)
        self.report_worker.moveToThread(self.report_thread)
        self.report_thread.started.connect(self.report_worker.run)
        self.report_thread.finished.connect(self.report_thread.deleteLater)
        self.report_worker.finished.connect(self.report_thread.quit)
        self.report_worker.finished.connect(self.report_worker.deleteLater)
        self.report_worker.finished.connect(QApplication.instance().quit)
        self.report_thread.start()

    def on_audio_captured(self, audio_bytes):
        # Prevent overlapping processing
        # FIX: Check against 'worker_thread' instead of 'thread' to avoid QObject name collision
        if hasattr(self, 'worker_thread') and self.worker_thread.isRunning():
            return

        self.overlay.set_status("processing")
        self.overlay.clear_text()

        # Run LLM in separate thread
        # FIX: Renamed variable from self.thread to self.worker_thread
        self.worker_thread = QThread()
        self.worker = LLMWorker(self.llm_service, audio_bytes)
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.stream_chunk.connect(self.overlay.update_text)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.finished.connect(lambda: self.overlay.set_status("listening" if self.overlay.is_listening else "idle"))

        self.worker_thread.start()

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False) # Keep running even if overlay is hidden (though it shouldn't be)

    # Check setup
    config = load_config()
    if not config.get("audio_device"):
        wizard = SetupWizard()
        if wizard.exec() != QDialog.DialogCode.Accepted:
            sys.exit(0)
        # Reload config after wizard
        config = load_config()

    controller = MainController()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
