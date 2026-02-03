import os
import shutil
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit,
                             QPushButton, QTextEdit, QFileDialog, QMessageBox, QLabel)
from PyQt6.QtCore import pyqtSignal
from src.backend.config import load_config, save_config

class SettingsDialog(QDialog):
    config_updated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(500, 600)
        self.config = load_config()

        layout = QVBoxLayout()
        self.setLayout(layout)

        form = QFormLayout()

        # API Keys
        self.groq_key_edit = QLineEdit(self.config.get("groq_api_key", ""))
        self.groq_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Groq API Key:", self.groq_key_edit)

        self.or_key_edit = QLineEdit(self.config.get("openrouter_api_key", ""))
        self.or_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("OpenRouter API Key:", self.or_key_edit)

        self.zhipu_key_edit = QLineEdit(self.config.get("zhipu_api_key", ""))
        self.zhipu_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("ZhipuAI API Key:", self.zhipu_key_edit)

        layout.addLayout(form)

        # Resume Upload
        layout.addWidget(QLabel("Resume (PDF):"))
        self.resume_path_edit = QLineEdit(self.config.get("resume_path", ""))
        self.resume_path_edit.setReadOnly(True)
        layout.addWidget(self.resume_path_edit)

        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse_resume)
        layout.addWidget(self.browse_btn)

        # Job Description
        layout.addWidget(QLabel("Job Description:"))
        self.jd_edit = QTextEdit()
        self.jd_edit.setPlainText(self.config.get("job_description", ""))
        layout.addWidget(self.jd_edit)

        # Buttons
        self.save_btn = QPushButton("Save & Close")
        self.save_btn.clicked.connect(self.save_settings)
        layout.addWidget(self.save_btn)

        # Styling
        self.setStyleSheet("""
            QDialog { background-color: #2b2b2b; color: white; }
            QLabel { color: #cccccc; font-weight: bold; }
            QLineEdit, QTextEdit {
                background-color: #3b3b3b; color: white;
                border: 1px solid #555; padding: 5px;
            }
            QPushButton {
                background-color: #007acc; color: white; border: none;
                padding: 8px; border-radius: 4px;
            }
            QPushButton:hover { background-color: #0098ff; }
        """)

    def browse_resume(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Select Resume", "", "PDF Files (*.pdf)")
        if fname:
            self.resume_path_edit.setText(fname)

    def save_settings(self):
        # Update config dict
        self.config["groq_api_key"] = self.groq_key_edit.text()
        self.config["openrouter_api_key"] = self.or_key_edit.text()
        self.config["zhipu_api_key"] = self.zhipu_key_edit.text()
        self.config["job_description"] = self.jd_edit.toPlainText()

        # Handle Resume Copy
        original_path = self.resume_path_edit.text()
        if original_path and os.path.exists(original_path):
            # Only copy if it's not already in data/
            filename = os.path.basename(original_path)
            target_path = os.path.join("data", filename)

            # If the path is different from target, copy it
            if os.path.abspath(original_path) != os.path.abspath(target_path):
                try:
                    shutil.copy2(original_path, target_path)
                    self.config["resume_path"] = target_path
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Failed to copy resume: {e}")
                    return
            else:
                self.config["resume_path"] = target_path

        save_config(self.config)
        self.config_updated.emit()
        self.accept()
