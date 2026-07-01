#!/usr/bin/env python3
"""
Personal AI OS — Automated Setup Script

Run this once after cloning the repo:
    python setup.py

It will:
    1. Install all required dependencies
    2. Ask for your Groq API key and create the .env file
    3. Create the notes folder with a sample note
    4. Verify everything is working
    5. Show you how to get started
"""

import os
import sys
import subprocess
from pathlib import Path


def print_header():
    print("""
╔══════════════════════════════════════════════════╗
║         Personal AI OS — Setup Wizard            ║
║         github.com/Manav-Patil-10/personal-ai-os ║
╚══════════════════════════════════════════════════╝
""")


def step(n, text):
    print(f"\n[Step {n}] {text}")
    print("─" * 50)


def install_dependencies():
    step(1, "Installing dependencies...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
        capture_output=False,
    )
    if result.returncode != 0:
        print("❌ Dependency installation failed. Please check the error above.")
        sys.exit(1)
    print("✓ Dependencies installed successfully.")


def create_env_file():
    step(2, "Setting up your API key...")

    if Path(".env").exists():
        print("✓ .env file already exists — skipping.")
        return

    print("You need a free Groq API key to use the cloud AI features.")
    print("Get one at: https://console.groq.com/keys\n")

    key = input("Paste your GROQ_API_KEY here (or press Enter to skip): ").strip()

    if key:
        Path(".env").write_text(f"GROQ_API_KEY={key}\n", encoding="utf-8")
        print("✓ .env file created.")
    else:
        Path(".env").write_text("GROQ_API_KEY=your-key-here\n", encoding="utf-8")
        print("⚠ Skipped. Edit .env manually and add your key before running.")


def create_notes_folder():
    step(3, "Creating notes folder with sample note...")

    notes_dir = Path("notes")
    notes_dir.mkdir(exist_ok=True)

    sample = notes_dir / "about_me.txt"
    if not sample.exists():
        sample.write_text(
            "Edit this file with facts about yourself.\n"
            "For example: your name, what you're learning, your goals.\n"
            "The AI will use this to answer personal questions about you.\n",
            encoding="utf-8",
        )
        print("✓ Created notes/about_me.txt — edit it with your own information.")
    else:
        print("✓ Notes folder already exists — skipping.")


def verify_setup():
    step(4, "Verifying setup...")

    issues = []

    if not Path(".env").exists():
        issues.append("Missing .env file")
    else:
        content = Path(".env").read_text()
        if "your-key-here" in content:
            issues.append("GROQ_API_KEY not set in .env file")

    if not Path("requirements.txt").exists():
        issues.append("Missing requirements.txt")

    if not Path("notes").exists():
        issues.append("Missing notes folder")

    if issues:
        print("⚠ Setup issues found:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("✓ Everything looks good!")


def print_getting_started():
    step(5, "You're ready! Here's how to get started:")
    print("""
  Chat with memory:
    python ai_assistant.py "hello"

  Add your notes and index them:
    python rag_assistant.py --index
    python rag_assistant.py --ask-notes "what am I learning?"

  Manage tasks:
    python task_assistant.py "add a task to try the AI OS"

  Use the orchestrator (routes automatically):
    python orchestrator.py "what should I work on today?"

  Open the web dashboard:
    python app.py
    → then open http://127.0.0.1:5000 in your browser

  Get a daily briefing:
    python proactive.py --now

  Use private/local mode (requires Ollama):
    python private_assistant.py --local "your question"

  Full documentation: README.md
""")


def main():
    print_header()
    install_dependencies()
    create_env_file()
    create_notes_folder()
    verify_setup()
    print_getting_started()
    print("Setup complete. Enjoy your Personal AI OS!\n")


if __name__ == "__main__":
    main()