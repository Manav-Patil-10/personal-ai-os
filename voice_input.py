#!/usr/bin/env python3
import speech_recognition as sr
from PyQt5.QtWidgets import QWidget, QPushButton, QVBoxLayout, QLabel, QFrame
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from PyQt5.QtGui import QFont

class VoiceWorker(QThread):
    transcribed = pyqtSignal(str)
    error = pyqtSignal(str)
    status = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.recognizer = sr.Recognizer()
        self.mic = sr.Microphone()

    def run(self):
        try:
            self.status.emit("🎤 Listening...")
            with self.mic as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                audio = self.recognizer.listen(source, timeout=10, phrase_time_limit=10)
            self.status.emit("🔄 Processing...")
            text = self.recognizer.recognize_google(audio)
            self.transcribed.emit(text)
            self.status.emit("✓ Transcribed")
        except sr.UnknownValueError:
            self.error.emit("Sorry, I didn't catch that.")
            self.status.emit("❌ Couldn't understand")
        except sr.RequestError:
            self.error.emit("No internet or speech service unavailable.")
            self.status.emit("❌ Error")
        except Exception as e:
            self.error.emit(f"Error: {str(e)}")
            self.status.emit("❌ Error")

class VoiceInputWidget(QFrame):
    transcribed_text = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self.setup_ui()

    def setup_ui(self):
        self.setStyleSheet("QFrame { background: transparent; }")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.speak_btn = QPushButton("🎙️  SPEAK")
        self.speak_btn.setFixedHeight(44)
        self.speak_btn.setFont(QFont("Segoe UI", 10, 1))
        self.speak_btn.setStyleSheet("""
            QPushButton {
                background: #534AB7;
                color: white;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover { background: #3C3489; }
            QPushButton:pressed { background: #E74C3C; }
        """)
        self.speak_btn.pressed.connect(self.start_listening)
        self.speak_btn.released.connect(self.stop_listening)
        layout.addWidget(self.speak_btn)

    def start_listening(self):
        if self.worker is None or not self.worker.isRunning():
            self.speak_btn.setStyleSheet("QPushButton { background: #E74C3C; color: white; border: none; border-radius: 8px; }")
            self.speak_btn.setText("🔴 LISTENING...")
            self.worker = VoiceWorker()
            self.worker.transcribed.connect(self.on_transcribed)
            self.worker.error.connect(self.on_error)
            self.worker.start()

    def stop_listening(self):
        self.speak_btn.setStyleSheet("QPushButton { background: #534AB7; color: white; border: none; border-radius: 8px; }")
        self.speak_btn.setText("🎙️  SPEAK")

    def on_transcribed(self, text):
        self.transcribed_text.emit(text)

    def on_error(self, error_msg):
        pass