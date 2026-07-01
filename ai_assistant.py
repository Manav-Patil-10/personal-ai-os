#!/usr/bin/env python3
"""
Phase 1: same CLI assistant as Phase 0, now with persistent memory.

Every question and answer is saved to a local SQLite database (memory.db,
created automatically in this folder). Before asking a new question, the
script loads recent conversation history and includes it as context, so
the assistant can recall things from earlier sessions.
"""

import argparse
import os
import sqlite3
import sys
from datetime import datetime

from groq import Groq
from dotenv import load_dotenv

load_dotenv()

DB_PATH = "memory.db"
HISTORY_LIMIT = 10

PERSONAS = {
    "default": "You are a helpful, direct assistant.",
    "concise": "You are a terse assistant. Answer in 2-3 sentences max. No fluff.",
    "tutor": (
        "You are a patient tutor. Explain concepts step by step, check "
        "understanding with a follow-up question, and use a simple example."
    ),
}


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def save_exchange(conn, question, answer):
    conn.execute(
        "INSERT INTO conversations (timestamp, question, answer) VALUES (?, ?, ?)",
        (datetime.now().isoformat(timespec="seconds"), question, answer),
    )
    conn.commit()


def load_recent_history(conn, limit=HISTORY_LIMIT):
    rows = conn.execute(
        "SELECT question, answer FROM conversations ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return list(reversed(rows))


def print_history(conn):
    rows = conn.execute(
        "SELECT timestamp, question, answer FROM conversations ORDER BY id ASC"
    ).fetchall()
    if not rows:
        print("No conversation history yet.")
        return
    for ts, q, a in rows:
        print(f"\n[{ts}]")
        print(f"You: {q}")
        print(f"Assistant: {a}")


def get_client() -> Groq:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("Error: GROQ_API_KEY environment variable is not set.")
        sys.exit(1)
    return Groq(api_key=api_key)


def ask(client, conn, question, persona):
    system_prompt = PERSONAS.get(persona, PERSONAS["default"])
    messages = [{"role": "system", "content": system_prompt}]
    for past_q, past_a in load_recent_history(conn):
        messages.append({"role": "user", "content": past_q})
        messages.append({"role": "assistant", "content": past_a})
    messages.append({"role": "user", "content": question})

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
        )
    except Exception as e:
        return f"Error: API call failed ({e})."

    answer = response.choices[0].message.content
    save_exchange(conn, question, answer)
    return answer


def main():
    parser = argparse.ArgumentParser(description="Ask a question, get an answer, with memory.")
    parser.add_argument("question", nargs="?")
    parser.add_argument("--persona", choices=PERSONAS.keys(), default="default")
    parser.add_argument("--history", action="store_true")
    args = parser.parse_args()

    conn = init_db()

    if args.history:
        print_history(conn)
        return

    client = get_client()

    if args.question:
        if not args.question.strip():
            print("Error: question was empty.")
            sys.exit(1)
        print(ask(client, conn, args.question, args.persona))
        return

    print(f"Interactive mode (persona: {args.persona}). Type 'exit' to quit.")
    while True:
        question = input("\n> ").strip()
        if question.lower() in ("exit", "quit"):
            break
        if not question:
            continue
        print(ask(client, conn, question, args.persona))


if __name__ == "__main__":
    main()