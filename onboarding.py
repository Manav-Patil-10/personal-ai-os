#!/usr/bin/env python3
"""
Mandy Onboarding — first-run welcome screen for new users.
Shown when no API key is configured yet.
"""

from pathlib import Path
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QMessageBox
)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QFont, QDesktopServices

ENV_FILE = Path(".env")


class OnboardingWindow(QDialog):
    """Shown on first launch when no API key is set."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Welcome to Mandy")
        self.setFixedSize(520, 580)
        self.setModal(True)
        self.completed = False
        self.setup_ui()

    def setup_ui(self):
        self.setStyleSheet("QDialog { background: #ffffff; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header with gradient
        header = QFrame()
        header.setFixedHeight(160)
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #534AB7, stop:1 #3C3489);
            }
        """)
        header_layout = QVBoxLayout(header)
        header_layout.setAlignment(Qt.AlignCenter)
        header_layout.setSpacing(8)

        emoji = QLabel("⚡")
        emoji.setFont(QFont("Segoe UI", 36))
        emoji.setAlignment(Qt.AlignCenter)
        emoji.setStyleSheet("background: transparent; color: white;")
        header_layout.addWidget(emoji)

        title = QLabel("Welcome to Mandy")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("background: transparent; color: white;")
        header_layout.addWidget(title)

        subtitle = QLabel("Your personal AI assistant")
        subtitle.setFont(QFont("Segoe UI", 11))
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("background: transparent; color: #d0cdf5;")
        header_layout.addWidget(subtitle)

        layout.addWidget(header)

        # Body
        body = QFrame()
        body.setStyleSheet("background: #ffffff;")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(32, 28, 32, 28)
        body_layout.setSpacing(16)

        intro = QLabel(
            "To get started, Mandy needs a free Groq API key. "
            "This lets her think and respond to you. It takes about 30 seconds to get."
        )
        intro.setWordWrap(True)
        intro.setFont(QFont("Segoe UI", 11))
        intro.setStyleSheet("color: #444;")
        body_layout.addWidget(intro)

        # Step 1
        step1 = self.make_step("1", "Get your free key", "Click below to open Groq's website")
        body_layout.addWidget(step1)

        get_key_btn = QPushButton("Get free API key  →")
        get_key_btn.setFixedHeight(42)
        get_key_btn.setFont(QFont("Segoe UI", 11, QFont.Medium))
        get_key_btn.setStyleSheet("""
            QPushButton {
                background: #f1efea;
                color: #534AB7;
                border: 1px solid #e0ded8;
                border-radius: 8px;
            }
            QPushButton:hover { border-color: #534AB7; background: #f0efff; }
        """)
        get_key_btn.clicked.connect(self.open_groq_console)
        body_layout.addWidget(get_key_btn)

        # Step 2
        step2 = self.make_step("2", "Paste it below", "Copy the key and paste it here")
        body_layout.addWidget(step2)

        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("gsk_...")
        self.key_input.setFixedHeight(44)
        self.key_input.setFont(QFont("Segoe UI", 11))
        self.key_input.setStyleSheet("""
            QLineEdit {
                background: #f8f8f6;
                border: 1px solid #e0ded8;
                border-radius: 8px;
                padding: 0 14px;
                color: #1a1a1a;
            }
            QLineEdit:focus { border-color: #534AB7; }
        """)
        body_layout.addWidget(self.key_input)

        body_layout.addStretch()

        # Continue button
        self.continue_btn = QPushButton("Start using Mandy →")
        self.continue_btn.setFixedHeight(48)
        self.continue_btn.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.continue_btn.setStyleSheet("""
            QPushButton {
                background: #534AB7;
                color: white;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover { background: #3C3489; }
            QPushButton:disabled { background: #ccc; }
        """)
        self.continue_btn.clicked.connect(self.save_and_continue)
        body_layout.addWidget(self.continue_btn)

        skip_btn = QPushButton("Skip for now")
        skip_btn.setFlat(True)
        skip_btn.setFont(QFont("Segoe UI", 10))
        skip_btn.setStyleSheet("QPushButton { color: #999; border: none; } QPushButton:hover { color: #534AB7; }")
        skip_btn.clicked.connect(self.skip)
        body_layout.addWidget(skip_btn)

        layout.addWidget(body)

    def make_step(self, number, title, desc):
        frame = QFrame()
        frame.setStyleSheet("background: transparent;")
        h = QHBoxLayout(frame)
        h.setContentsMargins(0, 4, 0, 4)
        h.setSpacing(10)

        badge = QLabel(number)
        badge.setFixedSize(24, 24)
        badge.setAlignment(Qt.AlignCenter)
        badge.setFont(QFont("Segoe UI", 10, QFont.Bold))
        badge.setStyleSheet("background: #534AB7; color: white; border-radius: 12px;")
        h.addWidget(badge)

        text_frame = QFrame()
        text_frame.setStyleSheet("background: transparent;")
        v = QVBoxLayout(text_frame)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 11, QFont.Medium))
        title_label.setStyleSheet("color: #1a1a1a;")
        v.addWidget(title_label)

        desc_label = QLabel(desc)
        desc_label.setFont(QFont("Segoe UI", 9))
        desc_label.setStyleSheet("color: #888;")
        v.addWidget(desc_label)

        h.addWidget(text_frame)
        h.addStretch()
        return frame

    def open_groq_console(self):
        QDesktopServices.openUrl(QUrl("https://console.groq.com/keys"))

    def save_and_continue(self):
        key = self.key_input.text().strip()
        if not key:
            QMessageBox.warning(self, "Missing key", "Please paste your API key, or click 'Skip for now'.")
            return

        # Save to .env
        ENV_FILE.write_text(f"GROQ_API_KEY={key}\n", encoding="utf-8")
        import os
        os.environ["GROQ_API_KEY"] = key

        self.completed = True
        self.accept()

    def skip(self):
        self.completed = False
        self.reject()


def needs_onboarding() -> bool:
    """Check if onboarding should be shown (no valid API key configured)."""
    if not ENV_FILE.exists():
        return True
    content = ENV_FILE.read_text(encoding="utf-8")
    if "GROQ_API_KEY=" not in content:
        return True
    for line in content.splitlines():
        if line.startswith("GROQ_API_KEY="):
            key = line.split("=", 1)[1].strip()
            if not key or "your-key" in key:
                return True
    return False