import sys
import re
import math
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QRectF, QPointF
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QRadialGradient
from html import escape
from cognition import think


from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QLineEdit,
    QPushButton
)

from ollama import chat

from atlas_config import MODEL, MEMORY_LIMIT, SYSTEM_PROMPT
from memory_db import load_recent_messages, save_message


# ==========================================
# AI WORKER
# ==========================================

class AtlasWorker(QThread):

    response_ready = Signal(str)
    error = Signal(str)
    speaking = Signal()

    def __init__(self, messages):
        super().__init__()
        self.messages = messages

    def run(self):

        try:
            # Atlas evaluates and makes a decision
            text, state = think(self.messages)

            self.response_ready.emit(text)

            # Atlas respects his current voice state
            if state["voice"] == "on":

                self.speaking.emit()

                try:
                    from voice import speak
                    speak(text)

                except Exception as error:
                    self.error.emit(
                        f"Voice error: {error}"
                    )

        except Exception as error:
            self.error.emit(
                f"Cognition error: {error}"
            )
# ==========================================
# MICROPHONE WORKER
# ==========================================

class MicrophoneWorker(QThread):

    text_ready = Signal(str)
    error = Signal(str)

    def run(self):

        try:
            from microphone import listen

            text = listen(silent=True).strip()

            self.text_ready.emit(text)

        except Exception as error:
            self.error.emit(f"Microphone error: {error}")


# ==========================================
# ANIMATED ATLAS CORE
# ==========================================

class AtlasVisualizer(QWidget):
    """State-driven animation; not a live audio-level meter."""

    STATES = {
        "idle": ("#4ade80", 0.16, 0.65),
        "standby": ("#a78bfa", 0.12, 0.45),
        "listening": ("#a78bfa", 0.76, 1.8),
        "thinking": ("#facc15", 0.42, 2.5),
        "speaking": ("#38bdf8", 1.0, 3.0),
        "error": ("#f87171", 0.12, 0.5),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(156)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.state = "idle"
        self.phase = 0.0
        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self.advance)
        self.timer.start()
        self.setToolTip("Animated system state, not microphone volume")

    def set_state(self, state):
        if state in self.STATES:
            self.state = state
            self.update()

    def advance(self):
        self.phase = (self.phase + 0.033 * self.STATES[self.state][2]) % (math.tau * 20)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(self.width() / 2, self.height() / 2)
        color_name, activity, _ = self.STATES[self.state]
        color = QColor(color_name)
        phase = self.phase
        pulse = 0.5 + 0.5 * math.sin(phase * 2)
        radius = 58

        # Soft central glow.
        glow = QRadialGradient(QPointF(0, 0), 78)
        center = QColor(color)
        center.setAlpha(int(22 + 18 * pulse * activity))
        edge = QColor(color)
        edge.setAlpha(0)
        glow.setColorAt(0, center)
        glow.setColorAt(1, edge)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(glow))
        painter.drawEllipse(QRectF(-78, -78, 156, 156))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        # Fine concentric rings.
        for r, alpha in ((72, 55), (65, 34), (46, 52)):
            ring = QColor(color)
            ring.setAlpha(alpha)
            painter.setPen(QPen(ring, 1))
            painter.drawEllipse(QRectF(-r, -r, r * 2, r * 2))

        # Two counter-rotating arcs.
        arc_pen = QPen(color, 2.5)
        arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(arc_pen)
        rect = QRectF(-radius, -radius, radius * 2, radius * 2)
        angle = int((phase * 52 % 360) * 16)
        painter.drawArc(rect, angle, 92 * 16)
        painter.drawArc(rect, angle + 180 * 16, 55 * 16)

        # Symmetrical animated waveform inside the core.
        painter.setPen(Qt.PenStyle.NoPen)
        for i in range(13):
            x = (i - 6) * 6
            envelope = math.exp(-((i - 6) / 4.3) ** 2)
            wave = abs(math.sin(phase * 3.1 + i * 0.72))
            height = 5 + 48 * envelope * activity * (0.25 + 0.75 * wave)
            bar = QColor(color)
            bar.setAlpha(170 + int(85 * wave))
            painter.setBrush(QBrush(bar))
            painter.drawRoundedRect(QRectF(x - 1.7, -height / 2, 3.4, height), 1.7, 1.7)

        painter.end()


# ==========================================
# ATLAS APPLICATION
# ==========================================

class AtlasWindow(QWidget):

    def __init__(self):

        super().__init__()

        self.worker = None
        self.mic_worker = None

        self.current_message = ""
        self.recognized_text = ""
        self.mic_failed = False
        self.hands_free = False
        self.conversation_active = False
        self.automatic_listening = False
        self.discard_recording = False
        self.closing = False

        self.listen_timer = QTimer(self)
        self.listen_timer.setSingleShot(True)
        self.listen_timer.timeout.connect(self.listen_automatically)


        self.setWindowTitle("Atlas AI")
        self.resize(800, 720)

        self.setStyleSheet("""
            QWidget {
                background-color: #0b101a;
                color: #e2e8f0;
                font-family: Segoe UI;
                font-size: 14px;
            }

            QTextEdit, QLineEdit {
                background-color: #111827;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 12px;
            }

            QLineEdit:focus {
                border: 1px solid #38bdf8;
            }

            QPushButton {
                background-color: #2563eb;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                color: white;
            }

            QPushButton:hover {
                background-color: #3b82f6;
            }

            QPushButton:disabled {
                background-color: #1e293b;
                color: #64748b;
            }

            QPushButton#micButton {
                background-color: #7c3aed;
                padding: 12px;
            }

            QPushButton#micButton:hover {
                background-color: #8b5cf6;
            }

            QPushButton#micButton:disabled {
                background-color: #1e293b;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # ==================================
        # APPLICATION TITLE
        # ==================================

        title = QLabel("A T L A S")

        title.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        title.setStyleSheet("""
            font-size: 36px;
            font-weight: bold;
            color: #38bdf8;
            padding: 20px;
        """)

        layout.addWidget(title)

        self.visualizer = AtlasVisualizer(self)
        layout.addWidget(self.visualizer)

        # ==================================
        # SYSTEM STATUS
        # ==================================

        self.status = QLabel("SYSTEM ONLINE")

        self.status.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.status.setStyleSheet(
            "color: #4ade80;"
        )

        layout.addWidget(self.status)

        # ==================================
        # CONVERSATION HISTORY
        # ==================================

        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)

        self.append_message(
            "Atlas",
            "Systems operational. Try not to break anything.",
            "#38bdf8"
        )

        layout.addWidget(self.chat_history)

        # ==================================
        # INPUT AREA
        # ==================================

        input_layout = QHBoxLayout()

        self.message_input = QLineEdit()

        self.message_input.setPlaceholderText(
            "Message Atlas..."
        )

        self.message_input.returnPressed.connect(
            self.send_message
        )

        # Microphone button
        self.mic_button = QPushButton("🎙")

        self.mic_button.setObjectName("micButton")
        self.mic_button.setFixedWidth(55)

        self.mic_button.setToolTip(
            "Speak to Atlas"
        )

        self.mic_button.clicked.connect(
            lambda checked=False: self.start_listening()
        )

        # Send button
        self.send_button = QPushButton("Send")

        self.send_button.clicked.connect(
            self.send_message
        )

        input_layout.addWidget(self.message_input)
        input_layout.addWidget(self.mic_button)
        input_layout.addWidget(self.send_button)

        layout.addLayout(input_layout)
        self.hands_free_button = QPushButton("Hands-Free: OFF")
        self.hands_free_button.setCheckable(True)

        self.hands_free_button.toggled.connect(
            self.toggle_hands_free
        )

        layout.addWidget(self.hands_free_button)

        # ==================================
        # FOOTER
        # ==================================

        footer = QLabel(
            f"{MODEL.upper()}  |  WHISPER  |  LOCAL AI"
        )

        footer.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        footer.setStyleSheet("""
            color: #64748b;
            font-size: 11px;
            padding: 5px;
        """)

        layout.addWidget(footer)

        self.setLayout(layout)

    # ======================================
    # DISPLAY MESSAGE
    # ======================================

    def append_message(self, sender, message, color):

        safe_message = escape(message).replace(
            "\n", "<br>"
        )

        self.chat_history.append(
            f'<b style="color: {color};">'
            f'{escape(sender)}:</b> {safe_message}'
        )

        scrollbar = self.chat_history.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    # ======================================
    # STATUS AND CONTROLS
    # ======================================

    def set_status(self, text, color):

        self.status.setText(text)
        self.status.setStyleSheet(
            f"color: {color};"
        )

        status = text.upper()
        if "ERROR" in status:
            state = "error"
        elif "STANDBY" in status:
            state = "standby"
        elif "SPEAKING" in status:
            state = "speaking"
        elif "THINKING" in status:
            state = "thinking"
        elif "LISTENING" in status or "ACTIVATED" in status:
            state = "listening"
        else:
            state = "idle"
        self.visualizer.set_state(state)

    def set_controls_enabled(self, enabled):

        self.send_button.setEnabled(enabled)
        self.mic_button.setEnabled(enabled)
        self.message_input.setEnabled(enabled)

    # ======================================
    # SEND TEXT MESSAGE
    # ======================================

    def send_message(self):

        message = self.message_input.text().strip()

        if self.submit_message(message):
            self.message_input.clear()

    def submit_message(self, message):

        if (
            not message
            or self.closing
            or self.worker is not None
            or self.mic_worker is not None
        ):
            return False

        try:
            history = load_recent_messages(
                limit=MEMORY_LIMIT
            )

        except Exception as error:
            self.show_error(f"Memory error: {error}")
            return False

        messages = [SYSTEM_PROMPT] + history + [
            {
                "role": "user",
                "content": message
            }
        ]

        self.listen_timer.stop()
        self.current_message = message

        self.append_message(
            "You",
            message,
            "#94a3b8"
        )

        self.set_status(
            "ATLAS IS THINKING...",
            "#facc15"
        )

        self.set_controls_enabled(False)

        self.worker = AtlasWorker(messages)

        self.worker.response_ready.connect(
            self.receive_response
        )

        self.worker.speaking.connect(
            self.show_speaking
        )

        self.worker.error.connect(
            self.show_error
        )

        self.worker.finished.connect(
            self.finish_response
        )

        self.worker.start()

        return True

    # ======================================
    # RECEIVE AI RESPONSE
    # ======================================

    def receive_response(self, response):

        self.append_message(
            "Atlas",
            response,
            "#38bdf8"
        )

        try:
            save_message("user", self.current_message)
            save_message("assistant", response)

        except Exception as error:
            self.show_error(f"Memory error: {error}")

    # ======================================
    # SPEAKING STATUS
    # ======================================

    def show_speaking(self):

        self.set_status(
            "ATLAS IS SPEAKING...",
            "#38bdf8"
        )

    # ======================================
    # FINISH AI RESPONSE
    # ======================================

    def finish_response(self):
        self.worker.deleteLater()
        self.worker = None

        if self.closing:
            self.close()
            return

        self.set_status("SYSTEM ONLINE", "#4ade80")
        self.set_controls_enabled(True)
        self.message_input.setFocus()
        self.resume_hands_free()

    # ======================================
    # START MICROPHONE
    # ======================================

    def toggle_hands_free(self, enabled):
        self.hands_free = enabled
        self.conversation_active = False

        if enabled:
            self.hands_free_button.setText("Hands-Free: ON")
            self.hands_free_button.setStyleSheet("background-color: #16a34a;")
            self.resume_hands_free()
        else:
            self.hands_free_button.setText("Hands-Free: OFF")
            self.hands_free_button.setStyleSheet("")
            self.listen_timer.stop()

            if self.mic_worker is not None and self.automatic_listening:
                self.discard_recording = True
                self.set_status("FINISHING RECORDING...", "#facc15")
            elif self.worker is None and self.mic_worker is None:
                self.set_status("SYSTEM ONLINE", "#4ade80")


    def resume_hands_free(self):
        if (self.hands_free and not self.closing
                and self.worker is None and self.mic_worker is None):
            self.listen_timer.start(150)


    def listen_automatically(self):
        if self.hands_free and not self.closing:
            self.start_listening(automatic=True)


    def start_listening(self, automatic=False):
        if (self.closing or self.worker is not None
                or self.mic_worker is not None):
            return

        self.listen_timer.stop()
        self.automatic_listening = automatic
        self.discard_recording = False
        self.recognized_text = ""
        self.mic_failed = False

        if automatic and not self.conversation_active:
            self.set_status('STANDBY - SAY "HEY ATLAS"', "#a78bfa")
        else:
            self.set_status("ATLAS IS LISTENING...", "#a78bfa")

        self.set_controls_enabled(False)
        self.mic_worker = MicrophoneWorker()
        self.mic_worker.text_ready.connect(self.receive_speech)
        self.mic_worker.error.connect(self.microphone_error)
        self.mic_worker.finished.connect(self.finish_listening)
        self.mic_worker.start()

    # ======================================
    # RECEIVE RECOGNIZED SPEECH
    # ======================================

    def receive_speech(self, text):

        self.recognized_text = text

    def microphone_error(self, error):

        self.mic_failed = True
        self.show_error(error)

    # ======================================
    # FINISH LISTENING
    # ======================================

    def finish_listening(self):
        self.mic_worker.deleteLater()
        self.mic_worker = None

        text = self.recognized_text.strip()
        self.recognized_text = ""
        automatic = self.automatic_listening
        discard = self.discard_recording
        self.automatic_listening = False
        self.discard_recording = False

        if self.closing:
            self.close()
            return

        self.set_controls_enabled(True)
        self.set_status("SYSTEM ONLINE", "#4ade80")

        if self.mic_failed:
            self.hands_free_button.setChecked(False)
            self.set_status("MICROPHONE ERROR", "#f87171")
            return

        if discard or (automatic and not self.hands_free):
            self.resume_hands_free()
            return

        if not text:
            if not automatic:
                self.set_status("NO SPEECH DETECTED", "#facc15")
            self.resume_hands_free()
            return

        if automatic and not self.conversation_active:
            wake = re.search(r"\bhey[\s,!.:-]+atlas\b", text, re.IGNORECASE)
            if wake is None:
                self.resume_hands_free()
                return

            self.conversation_active = True
            self.set_status("ATLAS ACTIVATED", "#4ade80")
            text = text[wake.end():].strip(" ,.!?:;-")

            if not text:
                self.resume_hands_free()
                return

        command = text.lower().replace("’", "'")
        command = re.sub(r"[^\w\s']", " ", command)
        command = " ".join(command.split())

        if command in (
            "go to sleep", "goodbye atlas", "standby", "that's all",
            "thats all", "atlas go to sleep", "go to sleep atlas"
        ):
            self.conversation_active = False
            self.append_message("Atlas", "Finally, some peace and quiet.", "#38bdf8")
            self.resume_hands_free()
            return

        if command in ("stop listening", "text mode", "disable hands free"):
            self.hands_free_button.setChecked(False)
            return

        if not self.submit_message(text):
            self.resume_hands_free()

    # ======================================
    # ERROR HANDLING
    # ======================================

    def show_error(self, error):

        self.append_message(
            "System",
            error,
            "#f87171"
        )

        print("Error:", error)

    # ======================================
    # CLOSE APPLICATION
    # ======================================

    def closeEvent(self, event):
        self.closing = True
        self.listen_timer.stop()
        self.hands_free_button.setChecked(False)

        if self.worker is not None or self.mic_worker is not None:
            event.ignore()
            self.set_controls_enabled(False)
            self.hands_free_button.setEnabled(False)
            self.set_status("WAITING FOR TASK TO FINISH...", "#facc15")
        else:
            event.accept()


# ==========================================
# PROGRAM ENTRY POINT
# ==========================================

if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = AtlasWindow()
    window.show()

    sys.exit(app.exec())
