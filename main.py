import sys
import threading
from PyQt6.QtWidgets import QApplication, QMessageBox, QDialog
from PyQt6.QtCore import QObject, pyqtSignal, QThread

from src.backend.audio_stream import AudioService
from src.backend.llm_service import LLMService
from src.backend.database import DatabaseManager
from src.backend.config import load_config
from src.ui.wizard import SetupWizard
from src.ui.settings import SettingsDialog
from src.ui.overlay import OverlayWindow

class LLMWorker(QObject):
    """Worker to handle blocking LLM calls."""
    transcription_ready = pyqtSignal(str)
    answer_chunk = pyqtSignal(str)
    answer_complete = pyqtSignal(str) # New signal for DB saving
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

        self.transcription_ready.emit(text)

        # 2. Generate
        full_answer = ""
        for chunk in self.llm_service.generate_answer(text):
            full_answer += chunk
            self.answer_chunk.emit(chunk)

        self.answer_complete.emit(full_answer)
        self.finished.emit()

class RegenerationWorker(QObject):
    """Worker to handle regeneration of the last answer."""
    answer_chunk = pyqtSignal(str)
    answer_complete = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, llm_service, query):
        super().__init__()
        self.llm_service = llm_service
        self.query = query

    def run(self):
        full_answer = ""
        # Provide variation instruction
        instruction = "Provide a variation or alternative phrasing for this response. Keep the same core meaning but change the delivery."

        for chunk in self.llm_service.generate_answer(self.query, system_instruction=instruction):
            full_answer += chunk
            self.answer_chunk.emit(chunk)

        self.answer_complete.emit(full_answer)
        self.finished.emit()

class ReportWorker(QObject):
    finished = pyqtSignal()

    def __init__(self, service):
        super().__init__()
        self.service = service

    def run(self):
        self.service.generate_report()
        self.finished.emit()

class StartupWorker(QObject):
    finished = pyqtSignal()
    primary_connected = pyqtSignal(bool)

    def __init__(self, llm_service):
        super().__init__()
        self.llm_service = llm_service

    def run(self):
        # 1. Init Story Engine
        self.llm_service.story_engine.initialize()

        # 2. Verify Primary Connection (ZhipuAI)
        is_connected = self.llm_service.verify_primary_connection()
        self.primary_connected.emit(is_connected)

        self.finished.emit()

class MainController(QObject):
    def __init__(self):
        super().__init__()
        self.config = load_config()

        # DB
        self.db = DatabaseManager()
        self.current_interview_id = self.db.create_interview()

        # UI
        self.overlay = OverlayWindow()
        self.overlay.request_settings.connect(self.open_settings)
        self.overlay.toggle_listening.connect(self.handle_listening_toggle)
        self.overlay.end_interview.connect(self.handle_end_interview)
        self.overlay.regenerate_requested.connect(self.handle_regeneration)

        # Backend
        self.llm_service = LLMService(
            db_manager=self.db,
            groq_key=self.config.get("groq_api_key"),
            openrouter_key=self.config.get("openrouter_api_key"),
            zhipu_key=self.config.get("zhipu_api_key")
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

        # Async Startup
        self.run_startup_tasks()

    def run_startup_tasks(self):
        self.overlay.set_full_text("Loading Knowledge Base... Please wait.")
        self.startup_thread = QThread()
        self.startup_worker = StartupWorker(self.llm_service)
        self.startup_worker.moveToThread(self.startup_thread)
        self.startup_thread.started.connect(self.startup_worker.run)
        self.startup_worker.primary_connected.connect(self.on_startup_check_complete)
        self.startup_worker.finished.connect(self.startup_thread.quit)
        self.startup_worker.finished.connect(self.startup_worker.deleteLater)
        self.startup_thread.finished.connect(self.startup_thread.deleteLater)
        self.startup_thread.start()

    def on_startup_check_complete(self, is_primary_connected):
        if is_primary_connected:
            self.overlay.set_full_text("Ready. Connected to Primary Engine (GLM-4). Press 'M' to unmute.")
        else:
            self.overlay.set_full_text("Primary Unreachable. Switched to Backup Systems. Press 'M' to unmute.")

    def apply_audio_config(self):
        dev_idx = self.config.get("audio_device_index")
        if dev_idx is not None:
            # Verify if index is valid or find by name (omitted for brevity, trusting index or wizard)
            self.audio_service.set_device(dev_idx)

    def reload_context(self):
        resume = self.config.get("resume_path")
        jd = self.config.get("job_description")
        notes = self.config.get("strategic_notes", "")
        sheet = self.config.get("cheat_sheet", "")
        self.llm_service.load_context(resume, jd, notes, sheet)
        # Also update keys in case they changed
        self.llm_service.update_keys(
            self.config.get("groq_api_key"),
            self.config.get("openrouter_api_key"),
            self.config.get("zhipu_api_key")
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
        # Prevent overlapping processing and handle safe thread checks
        try:
            if self.worker_thread and self.worker_thread.isRunning():
                return
        except RuntimeError:
             # Thread object might be deleted but reference exists
             self.worker_thread = None

        self.overlay.set_status("processing")
        # Removed clear_text to keep history

        # Run LLM in separate thread
        self.worker_thread = QThread()
        self.worker = LLMWorker(self.llm_service, audio_bytes)
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.transcription_ready.connect(self.overlay.add_transcription)
        self.worker.transcription_ready.connect(self.save_user_transcript)
        self.worker.answer_chunk.connect(self.overlay.add_answer_chunk)
        self.worker.answer_complete.connect(self.save_ai_transcript)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.finished.connect(self.cleanup_thread)
        self.worker_thread.finished.connect(lambda: self.overlay.set_status("listening" if self.overlay.is_listening else "idle"))

        self.worker_thread.start()

    def save_user_transcript(self, text):
        self.db.save_transcript(self.current_interview_id, "user", text)

    def save_ai_transcript(self, text):
        self.db.save_transcript(self.current_interview_id, "ai", text)

    def cleanup_thread(self):
        self.worker_thread = None

    def handle_regeneration(self):
        """Regenerates the last AI response."""
        # Check if busy
        try:
            if self.worker_thread and self.worker_thread.isRunning():
                return
        except RuntimeError:
            self.worker_thread = None

        # Undo last turn
        last_query = self.llm_service.undo_last_turn()
        if not last_query:
            return # Nothing to regenerate

        # Update UI
        self.overlay.reset_last_ai_message()
        self.overlay.set_status("processing")

        # Start Worker
        self.worker_thread = QThread()
        self.worker = RegenerationWorker(self.llm_service, last_query)
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.answer_chunk.connect(self.overlay.add_answer_chunk)
        self.worker.answer_complete.connect(self.save_ai_transcript) # Save the new version
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.finished.connect(self.cleanup_thread)
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
