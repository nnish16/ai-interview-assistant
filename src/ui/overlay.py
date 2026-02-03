from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QApplication, QGraphicsDropShadowEffect,
                             QSizePolicy, QMenu, QScrollArea, QFrame, QSizeGrip, QScrollBar)
from PyQt6.QtCore import Qt, QPoint, QRect, QPropertyAnimation, QEasingCurve, pyqtSignal, QSize, QEvent
from PyQt6.QtGui import QColor, QPainter, QBrush, QPen, QIcon, QFont, QAction, QShortcut, QKeySequence

class ConversationItem(QWidget):
    def __init__(self, role, text, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(2)
        self.setLayout(layout)

        self.role_label = QLabel(role.upper())
        self.role_label.setStyleSheet(f"font-weight: bold; color: {'#00ff00' if role == 'You' else '#00ccff'}; font-size: 10px;")
        layout.addWidget(self.role_label)

        self.text_label = QLabel(text)
        self.text_label.setWordWrap(True)
        self.text_label.setStyleSheet("color: white; font-size: 14px; line-height: 1.4;")
        self.text_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.text_label)

    def append_text(self, text):
        self.text_label.setText(self.text_label.text() + text)

class DragScrollArea(QScrollArea):
    """A ScrollArea that allows dragging the window if clicking on non-interactive parts."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.start_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if we clicked on a scrollbar
            if self.verticalScrollBar().geometry().contains(event.pos()):
                super().mousePressEvent(event)
                return

            self.start_pos = event.globalPosition().toPoint()
            # Don't call super() if we want to intercept drag, BUT we need selection to work.
            # If text is selectable, QLabel handles it.
            # We let event propagate.
            super().mousePressEvent(event)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.start_pos:
            delta = event.globalPosition().toPoint() - self.start_pos
            # Move the parent window
            self.window().move(self.window().pos() + delta)
            self.start_pos = event.globalPosition().toPoint()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.start_pos = None
        super().mouseReleaseEvent(event)

class OverlayWindow(QWidget):
    request_settings = pyqtSignal()
    toggle_listening = pyqtSignal(bool) # True = Start, False = Stop/Pause
    end_interview = pyqtSignal()

    def __init__(self):
        super().__init__()

        # Window Flags
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
            # Removed WindowDoesNotAcceptFocus to allow hotkeys and interaction
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        if hasattr(Qt.WidgetAttribute, "WA_MacAlwaysShowToolWindow"):
             self.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow, True)

        # Dimensions
        self.collapsed_height = 80 # Taller for footer
        self.expanded_height = 400
        self.width_val = 600
        self.resize(self.width_val, self.collapsed_height)

        # State
        self.is_expanded = False
        self.is_listening = False
        self.old_pos = None
        self.current_ai_item = None

        # Layout
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(5)
        self.setLayout(self.main_layout)

        # --- Header ---
        self.header_layout = QHBoxLayout()

        # Status
        self.status_indicator = QLabel()
        self.status_indicator.setFixedSize(12, 12)
        self.status_indicator.setStyleSheet("background-color: #555; border-radius: 6px;")
        self.header_layout.addWidget(self.status_indicator)

        # Title
        self.title_label = QLabel("Cluely")
        self.title_label.setStyleSheet("color: white; font-weight: bold;")
        self.header_layout.addWidget(self.title_label)
        self.header_layout.addStretch()

        # Mute
        self.mute_btn = QPushButton("🔇")
        self.mute_btn.setFixedSize(30, 30)
        self.mute_btn.setStyleSheet("border: none; background-color: transparent; font-size: 16px;")
        self.mute_btn.clicked.connect(self.toggle_mute)
        self.header_layout.addWidget(self.mute_btn)

        # Settings
        self.settings_btn = QPushButton("⚙️")
        self.settings_btn.setFixedSize(30, 30)
        self.settings_btn.setStyleSheet("border: none; background-color: transparent; font-size: 16px;")
        self.settings_btn.clicked.connect(self.request_settings.emit)
        self.header_layout.addWidget(self.settings_btn)

        self.main_layout.addLayout(self.header_layout)

        # --- Scroll Area for History ---
        # Use custom DragScrollArea
        self.scroll_area = DragScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { width: 8px; background: #333; border-radius: 4px; }
            QScrollBar::handle:vertical { background: #555; border-radius: 4px; }
        """)
        # Keep visible even if empty to take up space/allow drag? No, hide if empty/collapsed.
        self.scroll_area.hide()

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout()
        self.content_layout.addStretch() # Push content up
        self.content_widget.setLayout(self.content_layout)
        self.scroll_area.setWidget(self.content_widget)

        self.main_layout.addWidget(self.scroll_area)

        # --- Audio Visualizer ---
        self.audio_bar = QWidget()
        self.audio_bar.setFixedHeight(4)
        self.audio_bar.setStyleSheet("background-color: #333; border-radius: 2px;")
        self.audio_bar_fill = QWidget(self.audio_bar)
        self.audio_bar_fill.setFixedHeight(4)
        self.audio_bar_fill.setStyleSheet("background-color: #00ff00; border-radius: 2px;")
        self.audio_bar_fill.setFixedWidth(0)
        self.main_layout.addWidget(self.audio_bar)

        # --- Footer (Hotkeys) ---
        self.footer_label = QLabel("Space: Toggle Mute  •  ↑/↓: Scroll History")
        self.footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.footer_label.setStyleSheet("color: rgba(255, 255, 255, 0.5); font-size: 10px; margin-top: 2px;")
        self.main_layout.addWidget(self.footer_label)

        # --- Resize Grip ---
        self.sizegrip = QSizeGrip(self)
        self.sizegrip.setStyleSheet("width: 10px; height: 10px; background-color: rgba(255, 255, 255, 0.1);")
        # Position it in resize event

        # Shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setOffset(0, 0)
        shadow.setColor(QColor(0, 0, 0, 150))
        self.setGraphicsEffect(shadow)

        # Shortcuts
        self.setup_shortcuts()

    def setup_shortcuts(self):
        # Navigation shortcuts
        self.sc_up = QShortcut(QKeySequence(Qt.Key.Key_Up), self)
        self.sc_up.activated.connect(self.scroll_up)

        self.sc_down = QShortcut(QKeySequence(Qt.Key.Key_Down), self)
        self.sc_down.activated.connect(self.scroll_down)

        # Space to toggle listening (if window has focus)
        self.sc_space = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        self.sc_space.activated.connect(self.toggle_mute)

    def scroll_up(self):
        if self.scroll_area.isVisible():
            val = self.scroll_area.verticalScrollBar().value()
            self.scroll_area.verticalScrollBar().setValue(val - 50)

    def scroll_down(self):
        if self.scroll_area.isVisible():
            val = self.scroll_area.verticalScrollBar().value()
            self.scroll_area.verticalScrollBar().setValue(val + 50)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        rect = self.rect()
        self.sizegrip.move(rect.right() - self.sizegrip.width(), rect.bottom() - self.sizegrip.height())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        brush = QBrush(QColor(30, 30, 30, 245))
        painter.setBrush(brush)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 20, 20)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Check for direct child widgets that didn't consume event
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.old_pos:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.pos() + delta)
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.old_pos = None

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        end_action = QAction("End Interview", self)
        end_action.triggered.connect(self.end_interview.emit)
        menu.addAction(end_action)
        menu.exec(event.globalPos())

    def toggle_mute(self):
        self.is_listening = not self.is_listening
        if self.is_listening:
            self.mute_btn.setText("🎙️")
            self.status_indicator.setStyleSheet("background-color: #00ff00; border-radius: 6px;")
            self.toggle_listening.emit(True)
        else:
            self.mute_btn.setText("🔇")
            self.status_indicator.setStyleSheet("background-color: #ff0000; border-radius: 6px;")
            self.toggle_listening.emit(False)

    def add_transcription(self, text):
        """Adds a user question to the list."""
        if not text.strip():
            return
        if not self.is_expanded:
            self.expand()

        item = ConversationItem("You", text)
        self.content_layout.addWidget(item)
        self.scroll_to_bottom()
        self.current_ai_item = None # Reset for next answer

    def add_answer_chunk(self, chunk):
        """Appends to the current AI answer or creates a new one."""
        if not self.is_expanded:
            self.expand()

        if self.current_ai_item is None:
            self.current_ai_item = ConversationItem("AI", "")
            self.content_layout.addWidget(self.current_ai_item)

        self.current_ai_item.append_text(chunk)
        self.scroll_to_bottom()

    def set_full_text(self, text):
        """Legacy/System message support."""
        if not self.is_expanded:
            self.expand()
        # Treat as system message
        item = ConversationItem("System", text)
        self.content_layout.addWidget(item)
        self.scroll_to_bottom()

    def clear_text(self):
        # Keep history
        pass

    def update_text(self, text):
        """Backward compatibility for MainController's stream_chunk logic.
           Should not be called if MainController is fixed, but harmless pass."""
        pass

    def scroll_to_bottom(self):
        QApplication.processEvents() # Ensure layout updates
        vsb = self.scroll_area.verticalScrollBar()
        vsb.setValue(vsb.maximum())

    def expand(self):
        if self.is_expanded:
            return

        self.is_expanded = True
        self.scroll_area.show()

        self.anim = QPropertyAnimation(self, b"size")
        self.anim.setDuration(300)
        self.anim.setStartValue(self.size())
        self.anim.setEndValue(QSize(self.width(), self.expanded_height))
        self.anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self.anim.start()

    def set_status(self, state):
        if state == "listening":
            self.status_indicator.setStyleSheet("background-color: #00ff00; border-radius: 6px;")
        elif state == "processing":
            self.status_indicator.setStyleSheet("background-color: #ffff00; border-radius: 6px;")
        else:
            self.status_indicator.setStyleSheet("background-color: #555; border-radius: 6px;")

    def update_audio_level(self, level):
        width = self.audio_bar.width()
        fill_width = int(width * level)
        self.audio_bar_fill.setFixedWidth(fill_width)
        if level > 0.8:
            self.audio_bar_fill.setStyleSheet("background-color: #ff0000; border-radius: 2px;")
        else:
            self.audio_bar_fill.setStyleSheet("background-color: #00ff00; border-radius: 2px;")
