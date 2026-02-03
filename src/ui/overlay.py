from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QApplication, QGraphicsDropShadowEffect, QSizePolicy, QMenu)
from PyQt6.QtCore import Qt, QPoint, QRect, QPropertyAnimation, QEasingCurve, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QPainter, QBrush, QPen, QIcon, QFont, QAction

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
            Qt.WindowType.Tool |
            Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        # Dimensions
        self.collapsed_height = 60
        self.expanded_height = 300
        self.width_val = 400
        self.resize(self.width_val, self.collapsed_height)

        # State
        self.is_expanded = False
        self.is_listening = False
        self.old_pos = None

        # Layout
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(15, 10, 15, 10)
        self.setLayout(self.main_layout)

        # Header (Controls)
        self.header_layout = QHBoxLayout()

        # Status Indicator (Circle)
        self.status_indicator = QLabel()
        self.status_indicator.setFixedSize(12, 12)
        self.status_indicator.setStyleSheet("background-color: #555; border-radius: 6px;")
        self.header_layout.addWidget(self.status_indicator)

        # Title/Drag Area
        self.title_label = QLabel("Cluely")
        self.title_label.setStyleSheet("color: white; font-weight: bold;")
        self.header_layout.addWidget(self.title_label)
        self.header_layout.addStretch()

        # Mute Toggle
        self.mute_btn = QPushButton("🔇") # Start muted
        self.mute_btn.setFixedSize(30, 30)
        self.mute_btn.setStyleSheet("border: none; background-color: transparent; font-size: 16px;")
        self.mute_btn.clicked.connect(self.toggle_mute)
        self.header_layout.addWidget(self.mute_btn)

        # Settings Button
        self.settings_btn = QPushButton("⚙️")
        self.settings_btn.setFixedSize(30, 30)
        self.settings_btn.setStyleSheet("border: none; background-color: transparent; font-size: 16px;")
        self.settings_btn.clicked.connect(self.request_settings.emit)
        self.header_layout.addWidget(self.settings_btn)

        self.main_layout.addLayout(self.header_layout)

        # Content Area (Text)
        self.text_display = QLabel("")
        self.text_display.setWordWrap(True)
        self.text_display.setStyleSheet("color: white; font-size: 14px; padding-top: 10px;")
        self.text_display.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.text_display.hide() # Hidden initially
        self.main_layout.addWidget(self.text_display)

        self.main_layout.addStretch()

        # Audio Visualizer (Progress Bar Style)
        self.audio_bar = QWidget()
        self.audio_bar.setFixedHeight(4)
        self.audio_bar.setStyleSheet("background-color: #333; border-radius: 2px;")
        self.audio_bar_fill = QWidget(self.audio_bar)
        self.audio_bar_fill.setFixedHeight(4)
        self.audio_bar_fill.setStyleSheet("background-color: #00ff00; border-radius: 2px;")
        self.audio_bar_fill.setFixedWidth(0)
        self.main_layout.addWidget(self.audio_bar)

        # Shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setOffset(0, 0)
        shadow.setColor(QColor(0, 0, 0, 150))
        self.setGraphicsEffect(shadow)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw Pill/Rounded Rect
        brush = QBrush(QColor(30, 30, 30, 240)) # Dark semi-transparent
        painter.setBrush(brush)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 20, 20)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
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

    def update_text(self, text):
        """Appends streaming text and expands window if needed."""
        if not text:
            return

        current = self.text_display.text()
        if not self.is_expanded:
            self.expand()

        self.text_display.setText(current + text)

    def set_full_text(self, text):
        """Sets full text (e.g. for transcription updates or clear)."""
        if not text:
            # Maybe collapse?
            pass
        self.text_display.setText(text)
        if text and not self.is_expanded:
            self.expand()

    def clear_text(self):
        self.text_display.setText("")
        # Optional: Collapse logic can be handled separately or by a timer

    def expand(self):
        if self.is_expanded:
            return

        self.is_expanded = True
        self.text_display.show()

        # Animation
        self.anim = QPropertyAnimation(self, b"size")
        self.anim.setDuration(300)
        self.anim.setStartValue(QSize(self.width_val, self.collapsed_height))
        self.anim.setEndValue(QSize(self.width_val, self.expanded_height))
        self.anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self.anim.start()

    def collapse(self):
        if not self.is_expanded:
            return

        self.is_expanded = False
        self.text_display.hide()
        self.resize(self.width_val, self.collapsed_height)

    def set_status(self, state):
        """Visual feedback for Listening, Thinking, etc."""
        # state: "listening", "processing", "idle"
        if state == "listening":
            self.status_indicator.setStyleSheet("background-color: #00ff00; border-radius: 6px;") # Green
        elif state == "processing":
            self.status_indicator.setStyleSheet("background-color: #ffff00; border-radius: 6px;") # Yellow
        else:
            self.status_indicator.setStyleSheet("background-color: #555; border-radius: 6px;") # Gray

    def update_audio_level(self, level):
        """Updates the audio visualizer bar. Level is 0.0 - 1.0"""
        width = self.audio_bar.width()
        fill_width = int(width * level)
        self.audio_bar_fill.setFixedWidth(fill_width)

        # Dynamic color based on level
        if level > 0.8:
            self.audio_bar_fill.setStyleSheet("background-color: #ff0000; border-radius: 2px;") # Clip warning
        else:
            self.audio_bar_fill.setStyleSheet("background-color: #00ff00; border-radius: 2px;")
