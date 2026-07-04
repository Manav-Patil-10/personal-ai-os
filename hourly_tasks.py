#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from datetime import datetime
import schedule
import time
import sys

from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QLabel, QPushButton, QFrame
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from dotenv import load_dotenv

load_dotenv()

def get_pending_tasks():
    tasks_file = Path("tasks.json")
    if not tasks_file.exists():
        return []
    tasks = json.loads(tasks_file.read_text(encoding="utf-8"))
    return [t for t in tasks if not t["done"]][:10]

def show_popup(tasks):
    app = QApplication.instance() or QApplication(sys.argv)
    dialog = QDialog()
    dialog.setWindowTitle("Mandy — Tasks")
    dialog.setFixedSize(480, 420)
    dialog.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Dialog)
    dialog.setStyleSheet("QDialog { background: #1a1a2e; }")

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(28, 24, 28, 20)
    layout.setSpacing(12)

    header = QLabel("📋 Your Tasks")
    header.setFont(QFont("Segoe UI", 16, 1))
    header.setAlignment(Qt.AlignCenter)
    header.setStyleSheet("color: #4faafe;")
    layout.addWidget(header)

    time_label = QLabel(datetime.now().strftime("%I:%M %p"))
    time_label.setFont(QFont("Segoe UI", 10))
    time_label.setAlignment(Qt.AlignCenter)
    time_label.setStyleSheet("color: #888;")
    layout.addWidget(time_label)

    count_label = QLabel(f"You have {len(tasks)} pending tasks")
    count_label.setFont(QFont("Segoe UI", 11))
    count_label.setAlignment(Qt.AlignCenter)
    count_label.setStyleSheet("color: #4faafe;")
    layout.addWidget(count_label)

    if tasks:
        for i, task in enumerate(tasks, 1):
            task_label = QLabel(f"  {i}. {task['title']}")
            task_label.setFont(QFont("Segoe UI", 10))
            task_label.setWordWrap(True)
            task_label.setStyleSheet("color: #ddd; padding: 6px 0;")
            layout.addWidget(task_label)
    else:
        empty = QLabel("✓ All caught up!")
        empty.setFont(QFont("Segoe UI", 12, 1))
        empty.setAlignment(Qt.AlignCenter)
        empty.setStyleSheet("color: #4faafe;")
        layout.addWidget(empty)

    layout.addStretch()

    btn = QPushButton("Got it")
    btn.setFixedHeight(44)
    btn.setFont(QFont("Segoe UI", 11, 1))
    btn.setStyleSheet("QPushButton { background: #4faafe; color: white; border: none; border-radius: 8px; } QPushButton:hover { background: #2196F3; }")
    btn.clicked.connect(dialog.accept)
    layout.addWidget(btn)

    dialog.exec_()

def check_and_show():
    tasks = get_pending_tasks()
    print(f"[{datetime.now().strftime('%I:%M %p')}] Reminder ({len(tasks)} tasks)...")
    show_popup(tasks)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--now", action="store_true")
    parser.add_argument("--interval", type=int, default=30)
    args = parser.parse_args()

    if args.now:
        check_and_show()
        return

    print(f"Task Reminder started - every {args.interval} minutes")
    schedule.every(args.interval).minutes.do(check_and_show)

    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main()