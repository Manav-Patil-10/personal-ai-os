#!/usr/bin/env python3
"""
Personal AI OS — Desktop App
A proper desktop GUI built with PyQt5.
"""

import sys
import os
import json
import threading
from pathlib import Path
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLineEdit, QLabel, QScrollArea,
    QFrame, QSplitter, QListWidget, QListWidgetItem, QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon

from dotenv import load_dotenv
from settings_window import SettingsWindow
load_dotenv()


# ── Worker thread (keeps UI responsive while AI thinks) ───────────────────────

class AIWorker(QThread):
    response_ready = pyqtSignal(str, str)  # agent, response
    error_occurred = pyqtSignal(str)

    def __init__(self, user_input):
        super().__init__()
        self.user_input = user_input

    def run(self):
        try:
            from groq import Groq
            import json as _json
            from pathlib import Path as _Path

            api_key = os.environ.get("GROQ_API_KEY")
            if not api_key:
                self.error_occurred.emit("GROQ_API_KEY not set. Please check Settings.")
                return

            client = Groq(api_key=api_key)

            # Simple intent classification
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                temperature=0,
                messages=[
                    {"role": "system", "content": "Classify into one word: task, notes, or chat. No punctuation."},
                    {"role": "user", "content": self.user_input},
                ],
            )
            intent = resp.choices[0].message.content.strip().lower()
            if intent not in ("task", "notes", "chat"):
                intent = "chat"

            label = {"task": "Task Agent", "notes": "Notes Agent", "chat": "Chat Agent"}[intent]

            # Run the appropriate agent
            if intent == "chat":
                result = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": "You are a helpful personal assistant."},
                        {"role": "user", "content": self.user_input},
                    ],
                )
                response = result.choices[0].message.content

            elif intent == "task":
                sys.path.insert(0, str(_Path(__file__).parent))
                from task_assistant import TOOL_DEFINITIONS, TOOL_MAP
                messages = [
                    {"role": "system", "content": "You are a task manager. Always use a tool."},
                    {"role": "user", "content": self.user_input},
                ]
                result = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=messages,
                    tools=TOOL_DEFINITIONS,
                    tool_choice="auto",
                    temperature=0.1,
                )
                msg = result.choices[0].message
                if msg.tool_calls:
                    messages.append(msg)
                    for tc in msg.tool_calls:
                        fn = TOOL_MAP.get(tc.function.name)
                        try:
                            args = _json.loads(tc.function.arguments) if tc.function.arguments else {}
                        except Exception:
                            args = {}
                        if not isinstance(args, dict):
                            args = {}
                        res = fn(**args) if fn else f"Unknown tool: {tc.function.name}"
                        messages.append({"role": "tool", "tool_call_id": tc.id, "content": res})
                    final = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=messages)
                    response = final.choices[0].message.content
                else:
                    response = msg.content or "Could not perform task action."

            elif intent == "notes":
                index_file = _Path("notes_index.json")
                if not index_file.exists():
                    response = "No notes indexed yet. Please run the indexer first."
                else:
                    import numpy as np
                    from sentence_transformers import SentenceTransformer
                    records = _json.loads(index_file.read_text(encoding="utf-8"))
                    embedder = SentenceTransformer("all-MiniLM-L6-v2")
                    q_vec = np.array(embedder.encode(self.user_input))
                    scored = []
                    for r in records:
                        v = np.array(r["embedding"])
                        sim = np.dot(q_vec, v) / (np.linalg.norm(q_vec) * np.linalg.norm(v))
                        scored.append((sim, r))
                    scored.sort(key=lambda x: x[0], reverse=True)
                    top = [r for _, r in scored[:3]]
                    context = "\n\n".join(f"[{r['source']}]\n{r['text']}" for r in top)
                    result = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": f"Answer in second person using ONLY this context:\n\n{context}"},
                            {"role": "user", "content": self.user_input},
                        ],
                    )
                    response = result.choices[0].message.content

            self.response_ready.emit(label, response)

        except Exception as e:
            self.error_occurred.emit(f"Error: {str(e)}")


# ── Message bubble widget ─────────────────────────────────────────────────────

class MessageBubble(QFrame):
    def __init__(self, text, is_user=False, agent_label=""):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        if not is_user and agent_label:
            label = QLabel(agent_label)
            label.setStyleSheet("color: #7c6af7; font-size: 11px; font-weight: 600;")
            layout.addWidget(label)

        msg = QLabel(text)
        msg.setWordWrap(True)
        msg.setTextFormat(Qt.PlainText)
        msg.setFont(QFont("Segoe UI", 10))

        if is_user:
            msg.setStyleSheet("""
                background: #7c6af7;
                color: white;
                padding: 10px 14px;
                border-radius: 14px 14px 4px 14px;
            """)
            layout.setAlignment(Qt.AlignRight)
        else:
            msg.setStyleSheet("""
                background: #f0f0f5;
                color: #1a1a1a;
                padding: 10px 14px;
                border-radius: 14px 14px 14px 4px;
            """)
            layout.setAlignment(Qt.AlignLeft)

        layout.addWidget(msg)
        self.setStyleSheet("background: transparent;")


# ── Main window ───────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Personal AI OS")
        self.setMinimumSize(900, 600)
        self.resize(1100, 700)
        self.setup_ui()
        self.load_tasks()

    def setup_ui(self):
        self.setStyleSheet("""
            QMainWindow { background: #f8f8f6; }
            QWidget { background: #f8f8f6; }
        """)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Sidebar ──
        sidebar = QFrame()
        sidebar.setFixedWidth(260)
        sidebar.setStyleSheet("background: #ffffff; border-right: 1px solid #e0ded8;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # Logo
        logo_frame = QFrame()
        logo_frame.setStyleSheet("border-bottom: 1px solid #e0ded8; padding: 0;")
        logo_layout = QHBoxLayout(logo_frame)
        logo_layout.setContentsMargins(16, 14, 16, 14)
        logo_label = QLabel("⚡ Personal AI OS")
        logo_label.setFont(QFont("Segoe UI", 13, QFont.Medium))
        logo_label.setStyleSheet("color: #534AB7; border: none;")
        logo_layout.addWidget(logo_label)
        sidebar_layout.addWidget(logo_frame)

        # Tasks header
        tasks_header = QLabel("  Tasks")
        tasks_header.setFont(QFont("Segoe UI", 10))
        tasks_header.setStyleSheet("color: #888; padding: 12px 16px 8px; border-bottom: none; background: #f8f8f6; text-transform: uppercase; letter-spacing: 1px; font-size: 10px;")
        sidebar_layout.addWidget(tasks_header)

        # Task list
        self.task_list = QListWidget()
        self.task_list.setStyleSheet("""
            QListWidget { border: none; background: #ffffff; padding: 4px; }
            QListWidget::item { padding: 8px 12px; border-radius: 6px; color: #1a1a1a; font-size: 13px; }
            QListWidget::item:hover { background: #f0efff; }
        """)
        sidebar_layout.addWidget(self.task_list)

        # Sidebar buttons
        btn_style = """
            QPushButton {
                background: #f1efea;
                border: 1px solid #e0ded8;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 12px;
                color: #1a1a1a;
                text-align: left;
                margin: 4px 12px;
            }
            QPushButton:hover { background: #e8e6ff; border-color: #7c6af7; color: #534AB7; }
        """

        briefing_btn = QPushButton("📋  Get Daily Briefing")
        briefing_btn.setStyleSheet(btn_style)
        briefing_btn.clicked.connect(self.get_briefing)
        sidebar_layout.addWidget(briefing_btn)

        refresh_btn = QPushButton("🔄  Refresh Tasks")
        refresh_btn.setStyleSheet(btn_style)
        refresh_btn.clicked.connect(self.load_tasks)
        sidebar_layout.addWidget(refresh_btn)

        settings_btn = QPushButton("⚙  Settings")
        settings_btn.setStyleSheet(btn_style)
        settings_btn.clicked.connect(self.open_settings)
        sidebar_layout.addWidget(settings_btn)

        sidebar_layout.addStretch()

        # API key status
        api_key = os.environ.get("GROQ_API_KEY", "")
        status_text = "✓ API key set" if api_key and "your-key" not in api_key else "⚠ API key not set"
        status_color = "#1D9E75" if api_key and "your-key" not in api_key else "#D85A30"
        status_label = QLabel(f"  {status_text}")
        status_label.setStyleSheet(f"color: {status_color}; font-size: 11px; padding: 8px 16px; border-top: 1px solid #e0ded8;")
        sidebar_layout.addWidget(status_label)

        main_layout.addWidget(sidebar)

        # ── Chat area ──
        chat_frame = QFrame()
        chat_frame.setStyleSheet("background: #ffffff;")
        chat_layout = QVBoxLayout(chat_frame)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.setSpacing(0)

        # Chat header
        header = QFrame()
        header.setStyleSheet("background: #ffffff; border-bottom: 1px solid #e0ded8;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 12, 20, 12)
        header_title = QLabel("Chat")
        header_title.setFont(QFont("Segoe UI", 13, QFont.Medium))
        header_title.setStyleSheet("color: #1a1a1a;")
        header_layout.addWidget(header_title)
        header_layout.addStretch()
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #888; font-size: 12px;")
        header_layout.addWidget(self.status_label)
        chat_layout.addWidget(header)

        # Messages area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: #ffffff; }")

        self.messages_widget = QWidget()
        self.messages_widget.setStyleSheet("background: #ffffff;")
        self.messages_layout = QVBoxLayout(self.messages_widget)
        self.messages_layout.setContentsMargins(20, 16, 20, 16)
        self.messages_layout.setSpacing(12)
        self.messages_layout.addStretch()

        # Welcome message
        welcome = MessageBubble("Hello! I'm your Personal AI OS. Ask me anything, manage tasks, or query your notes.", is_user=False, agent_label="Personal AI OS")
        self.messages_layout.addWidget(welcome)

        self.scroll_area.setWidget(self.messages_widget)
        chat_layout.addWidget(self.scroll_area)

        # Input area
        input_frame = QFrame()
        input_frame.setStyleSheet("background: #ffffff; border-top: 1px solid #e0ded8;")
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(16, 12, 16, 12)
        input_layout.setSpacing(10)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask anything...")
        self.input_field.setFont(QFont("Segoe UI", 11))
        self.input_field.setStyleSheet("""
            QLineEdit {
                background: #f8f8f6;
                border: 1px solid #e0ded8;
                border-radius: 20px;
                padding: 10px 16px;
                color: #1a1a1a;
            }
            QLineEdit:focus { border-color: #7c6af7; }
        """)
        self.input_field.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.input_field)

        send_btn = QPushButton("Send")
        send_btn.setFont(QFont("Segoe UI", 11))
        send_btn.setStyleSheet("""
            QPushButton {
                background: #534AB7;
                color: white;
                border: none;
                border-radius: 20px;
                padding: 10px 20px;
                font-weight: 500;
            }
            QPushButton:hover { background: #3C3489; }
        """)
        send_btn.clicked.connect(self.send_message)
        input_layout.addWidget(send_btn)

        chat_layout.addWidget(input_frame)
        main_layout.addWidget(chat_frame)

    def open_settings(self):
        dialog = SettingsWindow(self)
        dialog.exec_()

    def load_tasks(self):
        self.task_list.clear()
        tasks_file = Path("tasks.json")
        if not tasks_file.exists():
            item = QListWidgetItem("No tasks yet")
            item.setForeground(QColor("#888"))
            self.task_list.addItem(item)
            return
        tasks = json.loads(tasks_file.read_text(encoding="utf-8"))
        for t in tasks:
            status = "✓" if t["done"] else "○"
            item = QListWidgetItem(f"{status}  {t['title']}")
            if t["done"]:
                item.setForeground(QColor("#aaa"))
            self.task_list.addItem(item)

    def send_message(self):
        text = self.input_field.text().strip()
        if not text:
            return
        self.input_field.clear()

        # Add user bubble
        bubble = MessageBubble(text, is_user=True)
        self.messages_layout.addWidget(bubble)
        self.scroll_to_bottom()

        # Show thinking indicator
        self.thinking_label = QLabel("Thinking...")
        self.thinking_label.setStyleSheet("color: #888; font-size: 12px; padding: 4px 20px; font-style: italic;")
        self.messages_layout.addWidget(self.thinking_label)
        self.scroll_to_bottom()
        self.status_label.setText("Processing...")

        # Run AI in background thread
        self.worker = AIWorker(text)
        self.worker.response_ready.connect(self.on_response)
        self.worker.error_occurred.connect(self.on_error)
        self.worker.start()

    def on_response(self, agent, response):
        self.thinking_label.deleteLater()
        bubble = MessageBubble(response, is_user=False, agent_label=agent)
        self.messages_layout.addWidget(bubble)
        self.scroll_to_bottom()
        self.status_label.setText("Ready")
        self.load_tasks()

    def on_error(self, error):
        self.thinking_label.deleteLater()
        bubble = MessageBubble(error, is_user=False, agent_label="Error")
        self.messages_layout.addWidget(bubble)
        self.scroll_to_bottom()
        self.status_label.setText("Error")

    def get_briefing(self):
        self.send_message_programmatic("Generate my daily briefing based on my tasks and notes")

    def send_message_programmatic(self, text):
        self.input_field.setText(text)
        self.send_message()

    def scroll_to_bottom(self):
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, lambda: self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        ))


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Mandy")
    app.setStyle("Fusion")

    from onboarding import needs_onboarding, OnboardingWindow
    if needs_onboarding():
        onboarding = OnboardingWindow()
        onboarding.exec_()
        if not onboarding.completed:
            # User skipped — still launch app, they can set key in Settings later
            pass

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()