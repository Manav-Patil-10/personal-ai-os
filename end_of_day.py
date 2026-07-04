#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from datetime import datetime, date
import schedule
import time
import sys

from PyQt5.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QCheckBox, QScrollArea, QFrame, QWidget)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from dotenv import load_dotenv

load_dotenv()

COMPLETION_FILE = Path("completion_history.json")

def get_pending_tasks():
    tasks_file = Path("tasks.json")
    if not tasks_file.exists():
        return []
    tasks = json.loads(tasks_file.read_text(encoding="utf-8"))
    return [t for t in tasks if not t["done"]][:10]

def load_completion_history():
    if not COMPLETION_FILE.exists():
        return {}
    return json.loads(COMPLETION_FILE.read_text(encoding="utf-8"))

def save_completion_history(history):
    COMPLETION_FILE.write_text(json.dumps(history, indent=2, default=str), encoding="utf-8")

def update_tasks_json(completed_task_ids):
    tasks_file = Path("tasks.json")
    if not tasks_file.exists():
        return
    tasks = json.loads(tasks_file.read_text(encoding="utf-8"))
    for task in tasks:
        if task["id"] in completed_task_ids:
            task["done"] = True
    tasks_file.write_text(json.dumps(tasks, indent=2), encoding="utf-8")

def generate_progress_report():
    history = load_completion_history()
    if not history:
        return "No completion data yet."
    
    today = str(date.today())
    total_days = len(history)
    total_completed = sum(len(v) for v in history.values())
    avg_daily = total_completed / total_days if total_days > 0 else 0
    today_count = len(history.get(today, []))
    
    streak = 0
    current_date = date.today()
    while str(current_date) in history and len(history[str(current_date)]) > 0:
        streak += 1
        current_date = date.fromordinal(current_date.toordinal() - 1)
    
    report = f"📊 Progress Report\nDays Tracked: {total_days}\nTotal Completed: {total_completed}\nAverage: {avg_daily:.1f}/day\nToday: {today_count}\nStreak: {streak} days\n"
    return report

def show_end_of_day_popup(tasks):
    app = QApplication.instance() or QApplication(sys.argv)
    
    dialog = QDialog()
    dialog.setWindowTitle("Mandy — Daily Review")
    dialog.setFixedSize(500, 550)
    dialog.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Dialog)
    dialog.setStyleSheet("QDialog { background: #ffffff; }")

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(28, 24, 28, 20)
    layout.setSpacing(12)

    header = QLabel("📋 End of Day Review")
    header.setFont(QFont("Segoe UI", 16, 1))
    header.setAlignment(Qt.AlignCenter)
    header.setStyleSheet("color: #534AB7;")
    layout.addWidget(header)

    date_label = QLabel("Which tasks did you complete today?")
    date_label.setFont(QFont("Segoe UI", 11))
    date_label.setAlignment(Qt.AlignCenter)
    date_label.setStyleSheet("color: #666;")
    layout.addWidget(date_label)

    scroll = QScrollArea()
    scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
    
    scroll_widget = QWidget()
    scroll_layout = QVBoxLayout(scroll_widget)
    scroll_layout.setContentsMargins(0, 0, 0, 0)
    scroll_layout.setSpacing(8)

    checkboxes = []
    for task in tasks:
        checkbox = QCheckBox(task["title"])
        checkbox.setFont(QFont("Segoe UI", 10))
        checkbox.setStyleSheet("QCheckBox { color: #333; spacing: 8px; }")
        scroll_layout.addWidget(checkbox)
        checkboxes.append((task["id"], checkbox))

    scroll_layout.addStretch()
    scroll.setWidget(scroll_widget)
    layout.addWidget(scroll)

    btn_layout = QHBoxLayout()
    
    progress_btn = QPushButton("📊 Progress")
    progress_btn.setFixedHeight(40)
    progress_btn.setFont(QFont("Segoe UI", 10))
    progress_btn.setStyleSheet("QPushButton { background: #f0f0f0; color: #666; border: none; border-radius: 6px; }")
    progress_btn.clicked.connect(lambda: print(generate_progress_report()))
    btn_layout.addWidget(progress_btn)

    save_btn = QPushButton("✓ Save & Done")
    save_btn.setFixedHeight(40)
    save_btn.setFont(QFont("Segoe UI", 11, 1))
    save_btn.setStyleSheet("QPushButton { background: #534AB7; color: white; border: none; border-radius: 6px; } QPushButton:hover { background: #3C3489; }")
    
    def save_and_close():
        completed_ids = [task_id for task_id, cb in checkboxes if cb.isChecked()]
        history = load_completion_history()
        today = str(date.today())
        history[today] = completed_ids
        save_completion_history(history)
        update_tasks_json(completed_ids)
        print(f"\n✓ Saved! {len(completed_ids)} tasks completed.")
        dialog.accept()
    
    save_btn.clicked.connect(save_and_close)
    btn_layout.addWidget(save_btn)
    
    layout.addLayout(btn_layout)
    dialog.exec_()

def check_and_show():
    tasks = get_pending_tasks()
    print(f"[{datetime.now().strftime('%I:%M %p')}] Daily review...")
    show_end_of_day_popup(tasks)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--now", action="store_true")
    args = parser.parse_args()

    if args.now:
        check_and_show()
        return

    print("End-of-Day Review started - 9 PM daily")
    schedule.every().day.at("21:00").do(check_and_show)

    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main()
