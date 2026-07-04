#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from datetime import datetime
import schedule
import time
from groq import Groq
from dotenv import load_dotenv
from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QLabel, QPushButton, QFrame
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import sys

load_dotenv()

def get_pending_tasks():
    tasks_file = Path("tasks.json")
    if not tasks_file.exists():
        return []
    tasks = json.loads(tasks_file.read_text(encoding="utf-8"))
    return [t for t in tasks if not t["done"]][:10]

def show_hourly_popup(tasks):
    app = QApplication.instance() or QApplication(sys.argv)
    dialog = QDialog()
    dialog.setWindowTitle("Mandy — Tasks")
    dialog.setFixedSize(420, 300)
    dialog.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Dialog)
    dialog.setStyleSheet("QDialog { background: #ffffff; }")

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(24, 20, 24, 20)
    layout.setSpacing(12)

    header = QLabel("📋 Your Pending Tasks")
    header.setFont(QFont("Segoe UI", 13, 1))
    header.setStyleSheet("color: #534AB7;")
    layout.addWidget(header)

    time_label = QLabel(datetime.now().strftime("%I:%M %p"))
    time_label.setFont(QFont("Segoe UI", 10))
    time_label.setStyleSheet("color: #999;")
    layout.addWidget(time_label)

    if tasks:
        for i, task in enumerate(tasks, 1):
            task_label = QLabel(f"{i}. {task['title']}")
            task_label.setFont(QFont("Segoe UI", 10))
            task_label.setWordWrap(True)
            task_label.setStyleSheet("color: #333; padding: 4px 0;")
            layout.addWidget(task_label)
    else:
        empty = QLabel("✓ No pending tasks!")
        empty.setFont(QFont("Segoe UI", 11, 1))
        empty.setStyleSheet("color: #27ae60;")
        layout.addWidget(empty)

    layout.addStretch()

    close_btn = QPushButton("Got it")
    close_btn.setFixedHeight(40)
    close_btn.setFont(QFont("Segoe UI", 11))
    close_btn.setStyleSheet("""
        QPushButton {
            background: #534AB7;
            color: white;
            border: none;
            border-radius: 8px;
        }
        QPushButton:hover { background: #3C3489; }
    """)
    close_btn.clicked.connect(dialog.accept)
    layout.addWidget(close_btn)

    dialog.exec_()

def check_and_show():
    tasks = get_pending_tasks()
    print(f"[{datetime.now().strftime('%I:%M %p')}] Showing {len(tasks)} tasks...")
    show_hourly_popup(tasks)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--now", action="store_true")
    parser.add_argument("--interval", type=int, default=60)
    args = parser.parse_args()

    if args.now:
        tasks = get_pending_tasks()
        show_hourly_popup(tasks)
        return

    print(f"Hourly reminder started. Checks every {args.interval} minutes.")
    schedule.every(args.interval).minutes.do(check_and_show)

    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main()