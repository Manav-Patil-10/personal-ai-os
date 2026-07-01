#!/usr/bin/env python3
"""
Phase 7: Privacy-first assistant with local model option.

Adds a --local flag that routes all requests through Ollama (runs on your
machine, zero data leaves your computer) instead of the Groq cloud API.

Usage:
    python private_assistant.py "explain RAG"           # uses Groq (cloud)
    python private_assistant.py --local "explain RAG"   # uses Ollama (local)
    python private_assistant.py --audit                 # show data flow audit
"""

import argparse
import os
import sys
import urllib.request
import json

from dotenv import load_dotenv

load_dotenv()

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"

# ── Data flow audit ────────────────────────────────────────────────────────────

AUDIT = """
╔══════════════════════════════════════════════════════╗
║         PERSONAL AI OS — DATA FLOW AUDIT             ║
╠══════════════════════════════════════════════════════╣
║                                                      ║
║  CLOUD MODE (default, uses Groq API):                ║
║  • Your question → sent to Groq servers              ║
║  • Response → returned from Groq servers             ║
║  • tasks.json → stays on your machine only           ║
║  • notes/ folder → stays on your machine only        ║
║  • memory.db → stays on your machine only            ║
║  • .env (API key) → never leaves your machine        ║
║                                                      ║
║  LOCAL MODE (--local flag, uses Ollama):             ║
║  • Your question → processed on YOUR machine only    ║
║  • Response → generated on YOUR machine only         ║
║  • Zero data sent to any external server             ║
║  • Slightly slower, but fully private                ║
║                                                      ║
║  WHAT'S NEVER UPLOADED (either mode):                ║
║  • .env file (API keys)                              ║
║  • memory.db (conversation history)                  ║
║  • notes/ folder (personal documents)                ║
║  • tasks.json (your task list)                       ║
║  • notes_index.json (embeddings of your notes)       ║
║                                                      ║
║  THREAT MODEL:                                       ║
║  • Laptop stolen → .env has API key; revoke it       ║
║    immediately at console.groq.com/keys              ║
║  • GitHub repo public → secrets excluded via         ║
║    .gitignore; personal data never committed         ║
║  • Cloud API breach → your questions could be        ║
║    exposed; use --local for sensitive queries        ║
╚══════════════════════════════════════════════════════╝
"""


# ── Local model via Ollama ─────────────────────────────────────────────────────

def ask_local(question: str, system_prompt: str = "You are a helpful assistant.") -> str:
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": f"System: {system_prompt}\n\nUser: {question}\n\nAssistant:",
        "stream": False,
    }).encode("utf-8")

    try:
        req = urllib.request.Request(
            OLLAMA_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result.get("response", "No response from local model.")
    except ConnectionRefusedError:
        return "Error: Ollama is not running. Start it with: ollama serve"
    except Exception as e:
        return f"Error calling local model: {e}"


# ── Cloud model via Groq ───────────────────────────────────────────────────────

def ask_cloud(question: str, system_prompt: str = "You are a helpful assistant.") -> str:
    try:
        from groq import Groq
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            return "Error: GROQ_API_KEY not set in .env file."
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error calling cloud model: {e}"


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Privacy-first assistant.")
    parser.add_argument("question", nargs="?", help="Question to ask.")
    parser.add_argument("--local", action="store_true", help="Use local Ollama model (fully private).")
    parser.add_argument("--audit", action="store_true", help="Show data flow audit.")
    args = parser.parse_args()

    if args.audit:
        print(AUDIT)
        return

    if not args.question:
        parser.print_help()
        return

    if args.local:
        print("[LOCAL MODE — your data stays on your machine]")
        print(ask_local(args.question))
    else:
        print("[CLOUD MODE — question sent to Groq API]")
        print(ask_cloud(args.question))


if __name__ == "__main__":
    main()