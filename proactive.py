#!/usr/bin/env python3
"""
Phase 5: Proactive intelligence — the system acts without being asked.

Runs a daily briefing automatically at a set time, pulling your tasks
and notes to generate a personalized morning summary.

Setup:
    pip install groq python-dotenv schedule
    .env file with GROQ_API_KEY=your-key-here

Usage:
    python proactive.py --now          # trigger briefing immediately (for testing)
    python proactive.py --time 08:00   # run scheduler, trigger daily at 8 AM
    python proactive.py                # defaults to 08:00
"""

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import schedule
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

BRIEFING_LOG = Path("briefings.log")

# ── Helpers ────────────────────────────────────────────────────────────────────

def get_client() -> Groq:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("Error: GROQ_API_KEY not set.")
        sys.exit(1)
    return Groq(api_key=api_key)


def get_tasks() -> str:
    """Pull current task list from tasks.json."""
    tasks_file = Path("tasks.json")
    if not tasks_file.exists():
        return "No tasks yet."
    import json
    tasks = json.loads(tasks_file.read_text(encoding="utf-8"))
    if not tasks:
        return "No tasks yet."
    lines = []
    for t in tasks:
        status = "✓" if t["done"] else "○"
        lines.append(f"  [{t['id']}] {status} {t['title']}")
    return "\n".join(lines)


def get_notes_summary() -> str:
    """Pull a quick summary from notes index if available."""
    index_file = Path("notes_index.json")
    if not index_file.exists():
        return "No notes indexed yet."
    import json
    records = json.loads(index_file.read_text(encoding="utf-8"))
    if not records:
        return "No notes indexed yet."
    # Just grab the first chunk from each unique source as a quick overview
    seen = {}
    for r in records:
        src = r["source"]
        if src not in seen:
            seen[src] = r["text"][:200]
    lines = [f"  [{src}]: {snippet}..." for src, snippet in seen.items()]
    return "\n".join(lines)


# ── Briefing generator ─────────────────────────────────────────────────────────

def generate_briefing(client: Groq) -> str:
    today = datetime.now().strftime("%A, %B %d, %Y")
    tasks = get_tasks()
    notes_preview = get_notes_summary()

    prompt = f"""Today is {today}.

Here is the user's current task list:
{tasks}

Here is a preview of the user's personal notes:
{notes_preview}

Generate a concise, friendly morning briefing for the user. Include:
1. A one-line greeting for the day
2. A summary of pending tasks (skip completed ones)
3. One insight or reminder based on their notes
4. One short motivational line to start the day

Keep it under 150 words. Be direct and encouraging."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a personal AI assistant generating a morning briefing."},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content


def run_briefing(client: Groq):
    """Generate and display the briefing, and save it to a log file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*50}")
    print(f"  DAILY BRIEFING — {timestamp}")
    print(f"{'='*50}\n")

    briefing = generate_briefing(client)
    print(briefing)
    print()

    # Save to log so you can review past briefings
    with open(BRIEFING_LOG, "a", encoding="utf-8") as f:
        f.write(f"\n[{timestamp}]\n{briefing}\n{'─'*40}\n")

    print(f"(Briefing saved to {BRIEFING_LOG})")


# ── Scheduler ──────────────────────────────────────────────────────────────────

def start_scheduler(client: Groq, run_time: str):
    print(f"Scheduler started. Daily briefing will run at {run_time}.")
    print("Press Ctrl+C to stop.\n")

    schedule.every().day.at(run_time).do(run_briefing, client=client)

    while True:
        schedule.run_pending()
        time.sleep(30)  # check every 30 seconds


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Proactive daily briefing agent.")
    parser.add_argument("--now", action="store_true", help="Trigger briefing immediately.")
    parser.add_argument("--time", default="08:00", help="Time to run daily briefing (HH:MM, 24hr). Default: 08:00")
    args = parser.parse_args()

    client = get_client()

    if args.now:
        run_briefing(client)
        return

    start_scheduler(client, args.time)


if __name__ == "__main__":
    main()