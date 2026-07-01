#!/usr/bin/env python3
"""
Tier 2 upgrade: web search agent.

Instead of tool-calling (which has issues with this model), we use a
two-step approach:
  1. Ask the model: should I search for this? If yes, what query?
  2. If search needed: run DuckDuckGo, feed results back, generate answer.
  3. If no search needed: answer directly.

Setup:
    pip install groq python-dotenv duckduckgo-search
    .env file with GROQ_API_KEY=your-key-here

Usage:
    python web_search_agent.py "what's the latest news in AI?"
    python web_search_agent.py "what is the capital of France?"
    python web_search_agent.py          # interactive mode
"""

import argparse
import json
import os
import sys

from groq import Groq
from dotenv import load_dotenv
from ddgs import DDGS

load_dotenv()


def get_client() -> Groq:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("Error: GROQ_API_KEY not set.")
        sys.exit(1)
    return Groq(api_key=api_key)


def search_web(query: str, max_results: int = 4) -> str:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return "No results found."
        lines = []
        for i, r in enumerate(results, 1):
            lines.append(f"[{i}] {r['title']}")
            lines.append(f"    {r['body'][:250]}")
            lines.append("")
        return "\n".join(lines)
    except Exception as e:
        return f"Search failed: {e}"


def decide_search(client: Groq, question: str) -> dict:
    """Ask the model whether to search and what query to use. Returns JSON."""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": (
                    "You decide whether a question needs a web search. "
                    "Respond with ONLY a JSON object, no other text:\n"
                    '{"search": true, "query": "search query here"}\n'
                    "or\n"
                    '{"search": false}\n\n'
                    "Search when: current events, recent news, latest releases, "
                    "prices, scores, weather, anything time-sensitive. "
                    "Don't search for: general knowledge, definitions, math, "
                    "history, stable facts."
                ),
            },
            {"role": "user", "content": question},
        ],
    )
    text = response.choices[0].message.content.strip()
    try:
        text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception:
        return {"search": False}


def answer_with_context(client: Groq, question: str, context: str) -> str:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "Answer the user's question using the search results below. "
                    "Be concise. Mention where the information comes from.\n\n"
                    f"Search results:\n{context}"
                ),
            },
            {"role": "user", "content": question},
        ],
    )
    return response.choices[0].message.content


def answer_direct(client: Groq, question: str) -> str:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a helpful, direct assistant."},
            {"role": "user", "content": question},
        ],
    )
    return response.choices[0].message.content


def run(client: Groq, question: str) -> str:
    decision = decide_search(client, question)

    if decision.get("search"):
        query = decision.get("query", question)
        print(f"[Searching: \"{query}\"]")
        results = search_web(query)
        return answer_with_context(client, question, results)
    else:
        print("[Answering directly — no search needed]")
        return answer_direct(client, question)


def main():
    parser = argparse.ArgumentParser(description="Chat agent with web search.")
    parser.add_argument("question", nargs="?", help="Question to ask.")
    args = parser.parse_args()

    client = get_client()

    if args.question:
        print(run(client, args.question))
        return

    print("Web search agent — interactive mode. Type 'exit' to quit.\n")
    while True:
        user_input = input("> ").strip()
        if user_input.lower() in ("exit", "quit"):
            break
        if not user_input:
            continue
        print(run(client, user_input))
        print()


if __name__ == "__main__":
    main()