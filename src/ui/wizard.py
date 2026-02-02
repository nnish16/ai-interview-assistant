from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton,
                             QComboBox, QMessageBox, QWidget)
from PyQt6.QtCore import Qt, pyqtSignal
from src.backend.audio_stream import AudioService
from src.backend.config import load_config, save_config

class SetupWizard(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cluely Setup")
        self.setModal(True)
        self.resize(400, 300)

        self.audio_service = AudioService()
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.info_label = QLabel("Checking audio devices...")
        self.info_label.setWordWrap(True)
        self.layout.addWidget(self.info_label)

        self.device_combo = QComboBox()
        self.layout.addWidget(self.device_combo)

        self.refresh_btn = QPushButton("Refresh Devices")
        self.refresh_btn.clicked.connect(self.scan_devices)
        self.layout.addWidget(self.refresh_btn)

        self.confirm_btn = QPushButton("Use Selected Device")
        self.confirm_btn.clicked.connect(self.save_and_close)
        self.layout.addWidget(self.confirm_btn)

        # Styles
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; color: white; }
            QLabel { color: #cccccc; font-size: 14px; }
            QPushButton {
                background-color: #007acc; color: white; border: none;
                padding: 8px; border-radius: 4px;
            }
            QPushButton:hover { background-color: #0098ff; }
            QComboBox { padding: 5px; }
        """)

        self.scan_devices()

    def scan_devices(self):
        self.device_combo.clear()
        devices = self.audio_service.list_devices()

        blackhole_found = False
        blackhole_index = -1

        for dev in devices:
            self.device_combo.addItem(dev['name'], dev['index'])
            if "BlackHole" in dev['name']:
                blackhole_found = True
                blackhole_index = self.device_combo.count() - 1

        if blackhole_found:
            self.info_label.setText(
                "✅ BlackHole driver detected!\n\n"
                "This allows the app to hear your interviewer. "
                "Please ensure it is selected below."
            )
            self.device_combo.setCurrentIndex(blackhole_index)
            self.confirm_btn.setEnabled(True)
        else:
            self.info_label.setText(
                "⚠️ BlackHole driver NOT detected.\n\n"
                "To hear your interviewer perfectly, please install BlackHole 2ch.\n\n"
                "Run: brew install blackhole-2ch\n\n"
                "Then click Refresh."
            )
            # We still allow them to proceed with other devices if they want
            self.confirm_btn.setEnabled(True)

    def save_and_close(self):
        idx = self.device_combo.currentData()
        name = self.device_combo.currentText()

        if idx is None:
             QMessageBox.warning(self, "Selection Required", "Please select an audio device.")
             return

        config = load_config()
        config['audio_device'] = name
        config['audio_device_index'] = idx # Save index too, though it might change on reboot
        save_config(config)

        self.accept()
