#!/usr/bin/env python3
"""
Mandy Monthly Reminder — cool animated popup on the last day of every month.
"""

import argparse
import json
import os
import sys
from datetime import datetime, date
from pathlib import Path

import schedule
import time
from groq import Groq
from dotenv import load_dotenv

load_dotenv()


def get_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("Error: GROQ_API_KEY not set.")
        sys.exit(1)
    return Groq(api_key=api_key)


def is_last_day_of_month():
    today = date.today()
    try:
        date(today.year, today.month, today.day + 1)
        return False
    except ValueError:
        return True


def get_pending_tasks():
    tasks_file = Path("tasks.json")
    if not tasks_file.exists():
        return []
    tasks = json.loads(tasks_file.read_text(encoding="utf-8"))
    return [t for t in tasks if not t["done"]]


def generate_reminder_message(client, tasks):
    task_text = "\n".join(f"- {t['title']}" for t in tasks) if tasks else "No pending tasks."
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are Mandy, a cool AI assistant. Write a short punchy motivational end-of-month message (2-3 sentences max). Be energetic and encouraging."},
            {"role": "user", "content": f"Pending tasks:\n{task_text}"},
        ],
    )
    return response.choices[0].message.content.strip()


def show_popup(message, tasks):
    from PyQt5.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout,
                                  QLabel, QPushButton, QFrame, QGraphicsDropShadowEffect)
    from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QRect, pyqtProperty
    from PyQt5.QtGui import QFont, QColor, QLinearGradient, QPainter, QPalette

    app = QApplication.instance() or QApplication(sys.argv)

    dialog = QDialog()
    dialog.setWindowTitle("Mandy")
    dialog.setFixedSize(480, 500)
    dialog.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Dialog)
    dialog.setAttribute(Qt.WA_TranslucentBackground)

    # Get screen center
    screen = app.primaryScreen().geometry()
    dialog.move(
        (screen.width() - 480) // 2,
        (screen.height() - 500) // 2
    )

    dialog.setStyleSheet("""
        QDialog { background: transparent; }
    """)

    main_frame = QFrame(dialog)
    main_frame.setGeometry(0, 0, 480, 500)
    main_frame.setStyleSheet("""
        QFrame {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #0f0c29, stop:0.5 #302b63, stop:1 #24243e);
            border-radius: 20px;
            border: 1px solid rgba(124, 106, 247, 0.5);
        }
    """)

    # Drop shadow
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(40)
    shadow.setColor(QColor(124, 106, 247, 180))
    shadow.setOffset(0, 0)
    main_frame.setGraphicsEffect(shadow)

    layout = QVBoxLayout(main_frame)
    layout.setContentsMargins(32, 28, 32, 24)
    layout.setSpacing(14)

    # Mandy branding
    brand = QLabel("⚡ MANDY")
    brand.setFont(QFont("Segoe UI", 11, QFont.Bold))
    brand.setAlignment(Qt.AlignCenter)
    brand.setStyleSheet("color: #7c6af7; letter-spacing: 4px; background: transparent;")
    layout.addWidget(brand)

    # Big emoji
    emoji = QLabel("🗓️")
    emoji.setFont(QFont("Segoe UI", 48))
    emoji.setAlignment(Qt.AlignCenter)
    emoji.setStyleSheet("background: transparent;")
    layout.addWidget(emoji)

    # Title
    month_name = datetime.now().strftime("%B")
    title = QLabel(f"Last Day of {month_name}!")
    title.setFont(QFont("Segoe UI", 22, QFont.Bold))
    title.setAlignment(Qt.AlignCenter)
    title.setStyleSheet("""
        color: white;
        background: transparent;
    """)
    layout.addWidget(title)

    # Date
    date_label = QLabel(datetime.now().strftime("%A, %B %d, %Y"))
    date_label.setFont(QFont("Segoe UI", 11))
    date_label.setAlignment(Qt.AlignCenter)
    date_label.setStyleSheet("color: #AFA9EC; background: transparent;")
    layout.addWidget(date_label)

    # Divider
    divider = QFrame()
    divider.setFrameShape(QFrame.HLine)
    divider.setStyleSheet("background: rgba(124,106,247,0.3); border: none; max-height: 1px;")
    layout.addWidget(divider)

    # Message
    msg = QLabel(message)
    msg.setFont(QFont("Segoe UI", 11))
    msg.setWordWrap(True)
    msg.setAlignment(Qt.AlignCenter)
    msg.setStyleSheet("color: #d0cef0; background: transparent; line-height: 1.6;")
    layout.addWidget(msg)

    # Tasks
    if tasks:
        tasks_frame = QFrame()
        tasks_frame.setStyleSheet("""
            QFrame {
                background: rgba(124, 106, 247, 0.15);
                border-radius: 10px;
                border: 1px solid rgba(124, 106, 247, 0.3);
            }
        """)
        tasks_layout = QVBoxLayout(tasks_frame)
        tasks_layout.setContentsMargins(16, 12, 16, 12)
        tasks_layout.setSpacing(6)

        tasks_title = QLabel("📋  Wrap these up today:")
        tasks_title.setFont(QFont("Segoe UI", 10, QFont.Bold))
        tasks_title.setStyleSheet("color: #7c6af7; background: transparent;")
        tasks_layout.addWidget(tasks_title)

        for t in tasks:
            task_label = QLabel(f"  ›  {t['title']}")
            task_label.setFont(QFont("Segoe UI", 10))
            task_label.setStyleSheet("color: #c0bef0; background: transparent;")
            tasks_layout.addWidget(task_label)

        layout.addWidget(tasks_frame)

    layout.addStretch()

    # Button
    btn = QPushButton("Let's crush it! 💪")
    btn.setFont(QFont("Segoe UI", 12, QFont.Bold))
    btn.setFixedHeight(48)
    btn.setStyleSheet("""
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #7c6af7, stop:1 #a855f7);
            color: white;
            border: none;
            border-radius: 10px;
            letter-spacing: 1px;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #6a5ae0, stop:1 #9333ea);
        }
        QPushButton:pressed { background: #534AB7; }
    """)
    btn.clicked.connect(dialog.accept)
    layout.addWidget(btn)

    dialog.exec_()


def show_reminder(client):
    tasks = get_pending_tasks()
    message = generate_reminder_message(client, tasks)
    print("Showing Mandy reminder...")
    show_popup(message, tasks)
    print("Dismissed.")


def check_and_remind(client):
    if is_last_day_of_month():
        show_reminder(client)
    else:
        print(f"[{date.today()}] Not end of month.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--now", action="store_true")
    parser.add_argument("--time", default="08:00")
    args = parser.parse_args()

    client = get_client()

    if args.now:
        show_reminder(client)
        return

    print(f"Scheduler started. Checks daily at {args.time}. Ctrl+C to stop.")
    schedule.every().day.at(args.time).do(check_and_remind, client=client)
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()