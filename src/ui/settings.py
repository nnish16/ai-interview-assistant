import os
import shutil
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit,
                             QPushButton, QTextEdit, QFileDialog, QMessageBox, QLabel,
                             QTabWidget, QWidget, QListWidget, QListWidgetItem, QHBoxLayout,
                             QAbstractItemView)
from PyQt6.QtCore import pyqtSignal, Qt
from src.backend.config import load_config, save_config

class SettingsDialog(QDialog):
    config_updated = pyqtSignal()
    story_added = pyqtSignal(str, str, str) # tag, content, style
    story_deleted = pyqtSignal(int) # story_id

    def __init__(self, parent=None, db_manager=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle("Settings & Knowledge Base")
        self.resize(650, 700)
        self.config = load_config()

        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.setLayout(self.main_layout)

        # Tabs
        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)

        # --- Tab 1: Configuration ---
        self.config_tab = QWidget()
        self.setup_config_tab()
        self.tabs.addTab(self.config_tab, "Configuration")

        # --- Tab 2: Q&A Library (Stories) ---
        self.qa_tab = QWidget()
        self.setup_qa_tab()
        self.tabs.addTab(self.qa_tab, "Q&A Library")

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.save_btn = QPushButton("✓  Save & Close")
        self.save_btn.setMinimumHeight(40)
        self.save_btn.setFixedWidth(200)
        self.save_btn.clicked.connect(self.save_settings)
        btn_layout.addWidget(self.save_btn)

        self.main_layout.addLayout(btn_layout)

        # Styling
        self.setStyleSheet("""
            QDialog, QTabWidget::pane {
                background-color: #202124;
                color: white;
                border: none;
            }
            QTabBar::tab {
                background: #2D2F33;
                color: #B0B0B0;
                padding: 10px 20px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #2196F3;
                color: white;
            }
            QLabel {
                color: #E8E8E8;
                font-size: 12px;
            }
            QLineEdit, QTextEdit, QListWidget {
                background-color: #2D2F33;
                color: #FFFFFF;
                border: 1px solid #404040;
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
                selection-background-color: #2196F3;
            }
            QLineEdit:focus, QTextEdit:focus, QListWidget:focus {
                border: 1px solid #2196F3;
                background-color: #2A2C30;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #1E88E5;
            }
            QPushButton:pressed {
                background-color: #1976D2;
            }
            QPushButton#DeleteBtn {
                background-color: #D32F2F;
            }
            QPushButton#DeleteBtn:hover {
                background-color: #C62828;
            }
        """)

    def setup_config_tab(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        self.config_tab.setLayout(layout)

        # Scroll area for config if needed? No, standard layout is fine.
        # But we need a widget to hold the form if we want scrolling.
        # For now, simplistic approach matches previous.

        form = QFormLayout()
        form.setSpacing(12)

        # API Keys Section
        api_label = QLabel("API Keys")
        api_label.setStyleSheet("color: #2196F3; font-weight: bold; font-size: 14px; margin-bottom: 5px;")
        layout.addWidget(api_label)

        self.groq_key_edit = QLineEdit(self.config.get("groq_api_key", ""))
        self.groq_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.groq_key_edit.setPlaceholderText("Groq API Key")
        form.addRow("Groq:", self.groq_key_edit)

        self.or_key_edit = QLineEdit(self.config.get("openrouter_api_key", ""))
        self.or_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.or_key_edit.setPlaceholderText("OpenRouter API Key")
        form.addRow("OpenRouter:", self.or_key_edit)

        self.zhipu_key_edit = QLineEdit(self.config.get("zhipu_api_key", ""))
        self.zhipu_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.zhipu_key_edit.setPlaceholderText("ZhipuAI API Key")
        form.addRow("ZhipuAI:", self.zhipu_key_edit)

        layout.addLayout(form)

        # Resume
        resume_label = QLabel("Resume & Context")
        resume_label.setStyleSheet("color: #2196F3; font-weight: bold; font-size: 14px; margin-top: 10px;")
        layout.addWidget(resume_label)

        h_resume = QHBoxLayout()
        self.resume_path_edit = QLineEdit(self.config.get("resume_path", ""))
        self.resume_path_edit.setReadOnly(True)
        self.resume_path_edit.setPlaceholderText("No resume loaded")
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse_resume)
        h_resume.addWidget(self.resume_path_edit)
        h_resume.addWidget(self.browse_btn)
        layout.addLayout(h_resume)

        # JD
        layout.addWidget(QLabel("Job Description:"))
        self.jd_edit = QTextEdit()
        self.jd_edit.setPlainText(self.config.get("job_description", ""))
        self.jd_edit.setPlaceholderText("Paste job description here...")
        self.jd_edit.setMaximumHeight(100)
        layout.addWidget(self.jd_edit)

        # Notes
        layout.addWidget(QLabel("Strategic Notes:"))
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlainText(self.config.get("strategic_notes", ""))
        self.notes_edit.setPlaceholderText("Key points to hit...")
        self.notes_edit.setMaximumHeight(80)
        layout.addWidget(self.notes_edit)

        # Cheat Sheet
        layout.addWidget(QLabel("Cheat Sheet (Facts/Refs):"))
        self.cheat_sheet_edit = QTextEdit()
        self.cheat_sheet_edit.setPlainText(self.config.get("cheat_sheet", ""))
        self.cheat_sheet_edit.setPlaceholderText("Technical specs, dates, metrics...")
        self.cheat_sheet_edit.setMaximumHeight(80)
        layout.addWidget(self.cheat_sheet_edit)

        layout.addStretch()

    def setup_qa_tab(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        self.qa_tab.setLayout(layout)

        info = QLabel("Pre-load stories or Q&A pairs. If a question is similar to the 'Topic', the AI will prioritize the 'Answer' content.")
        info.setWordWrap(True)
        info.setStyleSheet("color: #B0B0B0; margin-bottom: 10px;")
        layout.addWidget(info)

        # Input Form
        form = QFormLayout()
        self.qa_topic = QLineEdit()
        self.qa_topic.setPlaceholderText("e.g., Tell me about a challenge you faced")
        form.addRow("Question/Topic:", self.qa_topic)

        self.qa_answer = QTextEdit()
        self.qa_answer.setPlaceholderText("The full story or answer you want to give...")
        self.qa_answer.setMaximumHeight(100)
        form.addRow("Answer/Story:", self.qa_answer)

        self.qa_style = QLineEdit()
        self.qa_style.setPlaceholderText("e.g., Be humble, emphasize teamwork")
        form.addRow("Style/Delivery:", self.qa_style)

        layout.addLayout(form)

        # Add Button
        self.add_qa_btn = QPushButton("➕ Add to Library")
        self.add_qa_btn.clicked.connect(self.add_qa_item)
        layout.addWidget(self.add_qa_btn)

        # List of existing items
        layout.addWidget(QLabel("Current Library:"))
        self.qa_list = QListWidget()
        self.qa_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        layout.addWidget(self.qa_list)

        # Load existing
        self.refresh_qa_list()

        # Delete Button
        self.del_qa_btn = QPushButton("🗑️ Delete Selected")
        self.del_qa_btn.setObjectName("DeleteBtn")
        self.del_qa_btn.clicked.connect(self.delete_qa_item)
        layout.addWidget(self.del_qa_btn)

    def refresh_qa_list(self):
        if not self.db_manager:
            return

        self.qa_list.clear()
        stories = self.db_manager.get_all_stories()
        # id, tag, content, style, embedding
        for s in stories:
            sid, tag, content, style, _ = s
            # Display: [Topic] Start of content...
            preview = (content[:60] + '...') if len(content) > 60 else content
            item_text = f"[{tag}] {preview}"

            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, sid) # Store ID
            self.qa_list.addItem(item)

    def add_qa_item(self):
        tag = self.qa_topic.text().strip()
        content = self.qa_answer.toPlainText().strip()
        style = self.qa_style.text().strip()

        if not tag or not content:
            QMessageBox.warning(self, "Missing Info", "Topic and Answer are required.")
            return

        # Emit signal for MainController to handle (via StoryEngine)
        self.story_added.emit(tag, content, style)

        # Clear inputs
        self.qa_topic.clear()
        self.qa_answer.clear()
        self.qa_style.clear()

        # We can't immediately refresh unless we know it's done.
        # Ideally MainController updates us, or we just wait a bit?
        # Better: MainController calls us back or we just optimistically add to list?
        # For simplicity, let's assume MainController is fast or we refresh later.
        # Actually, let's manually trigger refresh if we had a direct link.
        # Since we use signal, we'll wait for user to close or update list manually?
        # Let's simple append to list locally for feedback?
        # No, better to just wait. Or assume success.

        # Hack for immediate feedback if DB is local (it is)
        # But we need the ID to delete it later.
        # We'll rely on reloading the list next time or if the user re-opens?
        # Let's try to reload.
        import time
        # Small delay to allow DB thread (if any) to write? No, DB is sync usually here.
        # But embedding is heavy.

        QMessageBox.information(self, "Added", "Item added to library (embedding generating in background).")

    def delete_qa_item(self):
        item = self.qa_list.currentItem()
        if not item:
            return

        sid = item.data(Qt.ItemDataRole.UserRole)
        self.story_deleted.emit(sid)

        # Remove from list
        row = self.qa_list.row(item)
        self.qa_list.takeItem(row)

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
