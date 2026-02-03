from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton,
                             QComboBox, QMessageBox, QWidget)
from PyQt6.QtCore import Qt, pyqtSignal
from src.backend.audio_stream import AudioService
from src.backend.config import load_config, save_config

class SetupWizard(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Setup Assistant")
        self.setModal(True)
        self.resize(500, 400)

        self.audio_service = AudioService()
        self.layout = QVBoxLayout()
        self.layout.setSpacing(15)
        self.layout.setContentsMargins(30, 30, 30, 30)
        self.setLayout(self.layout)

        # Add title
        title = QLabel("🎙️ Audio Setup")
        title.setStyleSheet("""
            font-size: 22px;
            font-weight: 600;
            color: #FFFFFF;
            margin-bottom: 10px;
        """)
        self.layout.addWidget(title)

        self.info_label = QLabel("Checking audio devices...")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("""
            color: #E8E8E8;
            font-size: 13px;
            line-height: 1.5;
            padding: 15px;
            background-color: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            border-left: 3px solid #2196F3;
        """)
        self.layout.addWidget(self.info_label)

        # Device selection label
        device_label = QLabel("Select Audio Input Device:")
        device_label.setStyleSheet("""
            color: #B0B0B0;
            font-size: 12px;
            font-weight: 500;
            margin-top: 10px;
        """)
        self.layout.addWidget(device_label)

        self.device_combo = QComboBox()
        self.device_combo.setMinimumHeight(40)
        self.layout.addWidget(self.device_combo)

        # Button container
        self.layout.addStretch()
        
        self.refresh_btn = QPushButton("🔄  Refresh Devices")
        self.refresh_btn.setMinimumHeight(40)
        self.refresh_btn.clicked.connect(self.scan_devices)
        self.layout.addWidget(self.refresh_btn)

        self.confirm_btn = QPushButton("✓  Use Selected Device")
        self.confirm_btn.setMinimumHeight(45)
        self.confirm_btn.clicked.connect(self.save_and_close)
        self.layout.addWidget(self.confirm_btn)

        # Styles
        self.setStyleSheet("""
            QDialog {
                background-color: #202124;
                color: white;
            }
            QLabel {
                color: #E8E8E8;
                font-size: 13px;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #1E88E5;
            }
            QPushButton:pressed {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #424242;
                color: #888888;
            }
            QComboBox {
                background-color: #2D2F33;
                color: #FFFFFF;
                border: 1px solid #404040;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QComboBox:hover {
                border: 1px solid #2196F3;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #FFFFFF;
                margin-right: 10px;
            }
            QComboBox QAbstractItemView {
                background-color: #2D2F33;
                color: #FFFFFF;
                selection-background-color: #2196F3;
                border: 1px solid #404040;
                outline: none;
            }
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
                "<b>✅ BlackHole driver detected!</b><br><br>"
                "This virtual audio device allows the assistant to hear your interviewer's audio. "
                "The device is selected below. Click 'Use Selected Device' to continue."
            )
            self.info_label.setStyleSheet("""
                color: #E8E8E8;
                font-size: 13px;
                line-height: 1.5;
                padding: 15px;
                background-color: rgba(76, 175, 80, 0.1);
                border-radius: 8px;
                border-left: 3px solid #4CAF50;
            """)
            self.device_combo.setCurrentIndex(blackhole_index)
            self.confirm_btn.setEnabled(True)
        else:
            self.info_label.setText(
                "<b>⚠️ BlackHole driver not detected</b><br><br>"
                "For optimal audio capture, please install <b>BlackHole 2ch</b>.<br><br>"
                "<b>Installation:</b><br>"
                "<code style='background: rgba(255,255,255,0.1); padding: 4px 8px; border-radius: 4px;'>"
                "brew install blackhole-2ch</code><br><br>"
                "Then click 'Refresh Devices' to scan again.<br><br>"
                "<i>You can proceed with another device, but audio quality may be affected.</i>"
            )
            self.info_label.setStyleSheet("""
                color: #E8E8E8;
                font-size: 13px;
                line-height: 1.5;
                padding: 15px;
                background-color: rgba(255, 152, 0, 0.1);
                border-radius: 8px;
                border-left: 3px solid #FF9800;
            """)
            # Still allow them to proceed with other devices
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
