from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QApplication, QGraphicsDropShadowEffect,
                             QSizePolicy, QMenu, QScrollArea, QFrame, QSizeGrip, QScrollBar)
from PyQt6.QtCore import Qt, QPoint, QRect, QPropertyAnimation, QEasingCurve, pyqtSignal, QSize, QEvent
from PyQt6.QtGui import QColor, QPainter, QBrush, QPen, QIcon, QFont, QAction, QShortcut, QKeySequence

class ConversationItem(QWidget):
    def __init__(self, role, text, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)
        self.setLayout(layout)
        
        # Add subtle background
        self.setStyleSheet("""
            ConversationItem {
                background-color: rgba(255, 255, 255, 0.02);
                border-radius: 8px;
                margin: 2px 0px;
            }
        """)

        self.role_label = QLabel(role.upper())
        role_colors = {'You': '#4CAF50', 'AI': '#2196F3', 'System': '#FF9800'}
        color = role_colors.get(role, '#00ccff')
        self.role_label.setStyleSheet(f"font-weight: 600; color: {color}; font-size: 11px; letter-spacing: 0.5px;")
        layout.addWidget(self.role_label)

        self.text_label = QLabel(text)
        self.text_label.setWordWrap(True)
        self.text_label.setStyleSheet("color: #E8E8E8; font-size: 13px; line-height: 1.5; padding: 2px 0;")
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
        self.collapsed_height = 85
        self.expanded_height = 450
        self.width_val = 600
        self.resize(self.width_val, self.collapsed_height)

        # State
        self.is_expanded = False
        self.is_listening = False
        self.old_pos = None
        self.current_ai_item = None
        self.has_animated_in = False  # Track if initial animation played
        self.has_animated_in = False  # Track if initial animation played

        # Layout
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(15, 12, 15, 12)
        self.main_layout.setSpacing(8)
        self.setLayout(self.main_layout)

        # --- Header ---
        self.header_layout = QHBoxLayout()
        self.header_layout.setSpacing(8)

        # Status
        self.status_indicator = QLabel()
        self.status_indicator.setFixedSize(10, 10)
        self.status_indicator.setStyleSheet("""
            background-color: #666;
            border-radius: 5px;
            border: 2px solid rgba(102, 102, 102, 0.3);
        """)
        # Add glow effect to status indicator
        status_glow = QGraphicsDropShadowEffect()
        status_glow.setBlurRadius(8)
        status_glow.setOffset(0, 0)
        status_glow.setColor(QColor(102, 102, 102, 150))
        self.status_indicator.setGraphicsEffect(status_glow)
        self.header_layout.addWidget(self.status_indicator)

        # Title
        self.title_label = QLabel("J.A.R.V.I.S.")
        self.title_label.setStyleSheet("""
            color: #FFFFFF;
            font-weight: 600;
            font-size: 14px;
            letter-spacing: 1px;
            padding-left: 8px;
        """)
        self.header_layout.addWidget(self.title_label)
        self.header_layout.addStretch()

        # Mute
        self.mute_btn = QPushButton("🔇")
        self.mute_btn.setFixedSize(36, 36)
        self.mute_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid rgba(255, 255, 255, 0.1);
                background-color: rgba(255, 255, 255, 0.04);
                border-radius: 8px;
                font-size: 16px;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.15);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.12);
            }
        """)
        self.mute_btn.clicked.connect(self.toggle_mute)
        self.header_layout.addWidget(self.mute_btn)

        # Settings
        self.settings_btn = QPushButton("⚙️")
        self.settings_btn.setFixedSize(36, 36)
        self.settings_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid rgba(255, 255, 255, 0.1);
                background-color: rgba(255, 255, 255, 0.04);
                border-radius: 8px;
                font-size: 16px;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.15);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.12);
            }
        """)
        self.settings_btn.clicked.connect(self.request_settings.emit)
        self.header_layout.addWidget(self.settings_btn)

        # Close
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(36, 36)
        self.close_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid rgba(255, 255, 255, 0.1);
                background-color: rgba(255, 255, 255, 0.04);
                border-radius: 8px;
                font-size: 18px;
                font-weight: bold;
                color: #FFFFFF;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: rgba(244, 67, 54, 0.7);
                border: 1px solid rgba(244, 67, 54, 0.9);
            }
            QPushButton:pressed {
                background-color: rgba(244, 67, 54, 0.9);
            }
        """)
        self.close_btn.clicked.connect(QApplication.instance().quit)
        self.header_layout.addWidget(self.close_btn)

        self.main_layout.addLayout(self.header_layout)

        # --- Scroll Area for History ---
        # Use custom DragScrollArea
        self.scroll_area = DragScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: rgba(0, 0, 0, 0.15);
                border-radius: 10px;
            }
            QScrollBar:vertical {
                width: 5px;
                background: rgba(255, 255, 255, 0.03);
                border-radius: 2px;
                margin: 2px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.15);
                border-radius: 2px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 0.25);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        # Keep visible even if empty to take up space/allow drag? No, hide if empty/collapsed.
        self.scroll_area.hide()

        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(4)
        self.content_layout.setContentsMargins(4, 4, 4, 4)
        self.content_layout.addStretch() # Push content up
        self.content_widget.setLayout(self.content_layout)
        self.scroll_area.setWidget(self.content_widget)

        self.main_layout.addWidget(self.scroll_area)

        # --- Audio Visualizer ---
        self.audio_bar = QWidget()
        self.audio_bar.setFixedHeight(4)
        self.audio_bar.setStyleSheet("""
            background-color: rgba(255, 255, 255, 0.08);
            border-radius: 2px;
        """)
        self.audio_bar_fill = QWidget(self.audio_bar)
        self.audio_bar_fill.setFixedHeight(4)
        self.audio_bar_fill.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #4CAF50, stop:1 #8BC34A);
            border-radius: 2px;
        """)
        self.audio_bar_fill.setFixedWidth(0)
        self.main_layout.addWidget(self.audio_bar)

        # --- Footer (Hotkeys) ---
        self.footer_label = QLabel("M: Toggle Mute  •  ↑/↓: Scroll History")
        self.footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.footer_label.setStyleSheet("""
            color: rgba(255, 255, 255, 0.35);
            font-size: 10px;
            margin-top: 6px;
            margin-bottom: 2px;
            font-weight: 500;
            letter-spacing: 0.5px;
        """)
        self.main_layout.addWidget(self.footer_label)

        # --- Resize Grip ---
        self.sizegrip = QSizeGrip(self)
        self.sizegrip.setStyleSheet("width: 0px; height: 0px; background-color: transparent;")
        self.sizegrip.hide()  # Hide completely to fix corner issue

        # Shadow - Enhanced for floating effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 200))
        self.setGraphicsEffect(shadow)

        # Shortcuts
        self.setup_shortcuts()
        
        # Position at top center initially (will be set properly when shown)
        self.position_at_dynamic_island()

    def position_at_dynamic_island(self):
        """Position the overlay at the top center of the screen (Dynamic Island area)"""
        screen = QApplication.primaryScreen().geometry()
        # Center horizontally
        x = (screen.width() - self.width_val) // 2
        # Start slightly above the screen for animation
        y = -10  # Just barely visible, like peeking from Dynamic Island
        self.move(x, y)

    def showEvent(self, event):
        """Override showEvent to animate from Dynamic Island"""
        super().showEvent(event)
        if not self.has_animated_in:
            self.has_animated_in = True
            self.animate_from_dynamic_island()

    def animate_from_dynamic_island(self):
        """Animate the overlay sliding down from the Dynamic Island area"""
        from PyQt6.QtWidgets import QGraphicsOpacityEffect
        
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width_val) // 2
        
        # Start position (hidden in Dynamic Island)
        start_y = -self.collapsed_height + 15
        # End position (visible below Dynamic Island)
        end_y = 20
        
        self.move(x, start_y)
        
        # Create slide-down animation with bounce
        self.slide_anim = QPropertyAnimation(self, b"pos")
        self.slide_anim.setDuration(800)
        self.slide_anim.setStartValue(QPoint(x, start_y))
        self.slide_anim.setEndValue(QPoint(x, end_y))
        self.slide_anim.setEasingCurve(QEasingCurve.Type.OutBack)  # Adds subtle overshoot
        self.slide_anim.start()
        
        # Add fade-in effect
        self.fade_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.fade_effect)
        
        self.fade_anim = QPropertyAnimation(self.fade_effect, b"opacity")
        self.fade_anim.setDuration(500)
        self.fade_anim.setStartValue(0.0)
        self.fade_anim.setEndValue(1.0)
        self.fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # When fade completes, restore shadow effect
        def restore_shadow():
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(30)
            shadow.setOffset(0, 4)
            shadow.setColor(QColor(0, 0, 0, 200))
            self.setGraphicsEffect(shadow)
        
        self.fade_anim.finished.connect(restore_shadow)
        self.fade_anim.start()
        
        # Position at top center initially (will be set properly when shown)
        self.position_at_dynamic_island()

    def position_at_dynamic_island(self):
        """Position the overlay at the top center of the screen (Dynamic Island area)"""
        screen = QApplication.primaryScreen().geometry()
        # Center horizontally
        x = (screen.width() - self.width_val) // 2
        # Start slightly above the screen for animation
        y = -10  # Just barely visible, like peeking from Dynamic Island
        self.move(x, y)

    def showEvent(self, event):
        """Override showEvent to animate from Dynamic Island"""
        super().showEvent(event)
        if not self.has_animated_in:
            self.has_animated_in = True
            self.animate_from_dynamic_island()

    def animate_from_dynamic_island(self):
        """Animate the overlay sliding down from the Dynamic Island area"""
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width_val) // 2
        
        # Start position (hidden in Dynamic Island)
        start_y = -self.collapsed_height + 10
        # End position (visible below Dynamic Island)
        end_y = 20
        
        self.move(x, start_y)
        
        # Create slide-down animation
        self.slide_anim = QPropertyAnimation(self, b"pos")
        self.slide_anim.setDuration(600)
        self.slide_anim.setStartValue(QPoint(x, start_y))
        self.slide_anim.setEndValue(QPoint(x, end_y))
        self.slide_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.slide_anim.start()

    def setup_shortcuts(self):
        # Navigation shortcuts
        self.sc_up = QShortcut(QKeySequence(Qt.Key.Key_Up), self)
        self.sc_up.activated.connect(self.scroll_up)

        self.sc_down = QShortcut(QKeySequence(Qt.Key.Key_Down), self)
        self.sc_down.activated.connect(self.scroll_down)

        # Key 'M' to toggle listening (if window has focus)
        self.sc_mute = QShortcut(QKeySequence(Qt.Key.Key_M), self)
        self.sc_mute.activated.connect(self.toggle_mute)

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

        # Semi-transparent background for overlay effect
        rect = self.rect()
        rect.adjust(1, 1, -1, -1)  # Slight inset for cleaner edges
        
        # Main background with transparency
        brush = QBrush(QColor(20, 21, 23, 220))  # More transparent
        painter.setBrush(brush)
        
        # Subtle border for definition
        painter.setPen(QPen(QColor(80, 80, 80, 120), 1))
        painter.drawRoundedRect(rect, 16, 16)  # Increased corner radius

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
            self.status_indicator.setStyleSheet("""
                background-color: #4CAF50;
                border-radius: 5px;
                border: 2px solid rgba(76, 175, 80, 0.4);
            """)
            # Update glow effect
            glow = QGraphicsDropShadowEffect()
            glow.setBlurRadius(12)
            glow.setOffset(0, 0)
            glow.setColor(QColor(76, 175, 80, 200))
            self.status_indicator.setGraphicsEffect(glow)
            self.toggle_listening.emit(True)
        else:
            self.mute_btn.setText("🔇")
            self.status_indicator.setStyleSheet("""
                background-color: #F44336;
                border-radius: 5px;
                border: 2px solid rgba(244, 67, 54, 0.4);
            """)
            # Update glow effect
            glow = QGraphicsDropShadowEffect()
            glow.setBlurRadius(12)
            glow.setOffset(0, 0)
            glow.setColor(QColor(244, 67, 54, 200))
            self.status_indicator.setGraphicsEffect(glow)
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
            self.status_indicator.setStyleSheet("""
                background-color: #4CAF50;
                border-radius: 5px;
                border: 2px solid rgba(76, 175, 80, 0.4);
            """)
            glow = QGraphicsDropShadowEffect()
            glow.setBlurRadius(12)
            glow.setOffset(0, 0)
            glow.setColor(QColor(76, 175, 80, 200))
            self.status_indicator.setGraphicsEffect(glow)
        elif state == "processing":
            self.status_indicator.setStyleSheet("""
                background-color: #FFC107;
                border-radius: 5px;
                border: 2px solid rgba(255, 193, 7, 0.4);
            """)
            glow = QGraphicsDropShadowEffect()
            glow.setBlurRadius(12)
            glow.setOffset(0, 0)
            glow.setColor(QColor(255, 193, 7, 200))
            self.status_indicator.setGraphicsEffect(glow)
        else:
            self.status_indicator.setStyleSheet("""
                background-color: #666;
                border-radius: 5px;
                border: 2px solid rgba(102, 102, 102, 0.3);
            """)
            glow = QGraphicsDropShadowEffect()
            glow.setBlurRadius(8)
            glow.setOffset(0, 0)
            glow.setColor(QColor(102, 102, 102, 150))
            self.status_indicator.setGraphicsEffect(glow)

    def update_audio_level(self, level):
        width = self.audio_bar.width()
        fill_width = int(width * level)
        self.audio_bar_fill.setFixedWidth(fill_width)
        if level > 0.8:
            self.audio_bar_fill.setStyleSheet("""
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #FF5722, stop:1 #F44336);
                border-radius: 2px;
            """)
        elif level > 0.5:
            self.audio_bar_fill.setStyleSheet("""
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #FFC107, stop:1 #FF9800);
                border-radius: 2px;
            """)
        else:
            self.audio_bar_fill.setStyleSheet("""
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4CAF50, stop:1 #8BC34A);
                border-radius: 2px;
            """)
