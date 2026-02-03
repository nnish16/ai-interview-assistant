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
        self.resize(550, 650)
        self.config = load_config()

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)
        self.setLayout(layout)

        # Add title
        title = QLabel("Configuration")
        title.setStyleSheet("""
            font-size: 20px;
            font-weight: 600;
            color: #FFFFFF;
            margin-bottom: 10px;
        """)
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(12)
        form.setContentsMargins(0, 10, 0, 10)

        # API Keys Section
        api_section = QLabel("API Keys")
        api_section.setStyleSheet("""
            font-size: 13px;
            font-weight: 600;
            color: #2196F3;
            margin-top: 5px;
        """)
        form.addRow(api_section)

        self.groq_key_edit = QLineEdit(self.config.get("groq_api_key", ""))
        self.groq_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.groq_key_edit.setPlaceholderText("Enter your Groq API key...")
        form.addRow("Groq API Key:", self.groq_key_edit)

        self.or_key_edit = QLineEdit(self.config.get("openrouter_api_key", ""))
        self.or_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.or_key_edit.setPlaceholderText("Enter your OpenRouter API key...")
        form.addRow("OpenRouter API Key:", self.or_key_edit)

        self.zhipu_key_edit = QLineEdit(self.config.get("zhipu_api_key", ""))
        self.zhipu_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.zhipu_key_edit.setPlaceholderText("Enter your ZhipuAI API key...")
        form.addRow("ZhipuAI API Key:", self.zhipu_key_edit)

        layout.addLayout(form)

        # Resume Upload Section
        resume_section = QLabel("Resume")
        resume_section.setStyleSheet("""
            font-size: 13px;
            font-weight: 600;
            color: #2196F3;
            margin-top: 10px;
        """)
        layout.addWidget(resume_section)
        
        resume_label = QLabel("Upload your resume (PDF format):")
        resume_label.setStyleSheet("color: #B0B0B0; font-size: 12px; margin-top: 5px;")
        layout.addWidget(resume_label)
        
        self.resume_path_edit = QLineEdit(self.config.get("resume_path", ""))
        self.resume_path_edit.setReadOnly(True)
        self.resume_path_edit.setPlaceholderText("No file selected")
        layout.addWidget(self.resume_path_edit)

        self.browse_btn = QPushButton("📁  Browse...")
        self.browse_btn.clicked.connect(self.browse_resume)
        layout.addWidget(self.browse_btn)

        # Job Description Section
        jd_section = QLabel("Job Description")
        jd_section.setStyleSheet("""
            font-size: 13px;
            font-weight: 600;
            color: #2196F3;
            margin-top: 10px;
        """)
        layout.addWidget(jd_section)
        
        jd_label = QLabel("Paste the job description for this interview:")
        jd_label.setStyleSheet("color: #B0B0B0; font-size: 12px; margin-top: 5px;")
        layout.addWidget(jd_label)
        
        self.jd_edit = QTextEdit()
        self.jd_edit.setPlainText(self.config.get("job_description", ""))
        self.jd_edit.setPlaceholderText("Enter the job description here...")
        self.jd_edit.setMinimumHeight(100)
        layout.addWidget(self.jd_edit)

        # Strategic Notes Section
        notes_section = QLabel("Strategic Notes")
        notes_section.setStyleSheet("""
            font-size: 13px;
            font-weight: 600;
            color: #2196F3;
            margin-top: 10px;
        """)
        layout.addWidget(notes_section)
        
        notes_label = QLabel("High-level strategy, interviewer details, and goals:")
        notes_label.setStyleSheet("color: #B0B0B0; font-size: 12px; margin-top: 5px;")
        layout.addWidget(notes_label)
        
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlainText(self.config.get("strategic_notes", ""))
        self.notes_edit.setPlaceholderText("Enter high-level strategy, interviewer name, goals...")
        self.notes_edit.setMinimumHeight(80)
        layout.addWidget(self.notes_edit)

        # Cheat Sheet Section
        cheat_section = QLabel("Cheat Sheet")
        cheat_section.setStyleSheet("""
            font-size: 13px;
            font-weight: 600;
            color: #2196F3;
            margin-top: 10px;
        """)
        layout.addWidget(cheat_section)
        
        cheat_label = QLabel("Technical details, facts, and quick references:")
        cheat_label.setStyleSheet("color: #B0B0B0; font-size: 12px; margin-top: 5px;")
        layout.addWidget(cheat_label)
        
        self.cheat_sheet_edit = QTextEdit()
        self.cheat_sheet_edit.setPlainText(self.config.get("cheat_sheet", ""))
        self.cheat_sheet_edit.setPlaceholderText("Enter specific technical details, facts, or quick references...")
        self.cheat_sheet_edit.setMinimumHeight(80)
        layout.addWidget(self.cheat_sheet_edit)

        # Buttons
        layout.addStretch()
        self.save_btn = QPushButton("✓  Save & Close")
        self.save_btn.setMinimumHeight(40)
        self.save_btn.clicked.connect(self.save_settings)
        layout.addWidget(self.save_btn)

        # Styling
        self.setStyleSheet("""
            QDialog {
                background-color: #202124;
                color: white;
            }
            QLabel {
                color: #E8E8E8;
                font-size: 12px;
            }
            QLineEdit, QTextEdit {
                background-color: #2D2F33;
                color: #FFFFFF;
                border: 1px solid #404040;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
                selection-background-color: #2196F3;
            }
            QLineEdit:focus, QTextEdit:focus {
                border: 1px solid #2196F3;
                background-color: #2A2C30;
            }
            QLineEdit::placeholder, QTextEdit::placeholder {
                color: #666666;
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
        self.config["strategic_notes"] = self.notes_edit.toPlainText()
        self.config["cheat_sheet"] = self.cheat_sheet_edit.toPlainText()

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
