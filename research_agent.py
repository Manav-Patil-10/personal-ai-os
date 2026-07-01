#!/usr/bin/env python3
"""
Jarvis Research Agent — Step 1

Searches the web, summarizes findings, and automatically saves
results to your notes folder so you can query them later with RAG.

Usage:
    python research_agent.py "latest developments in AI agents"
    python research_agent.py "best productivity techniques 2026"
    python research_agent.py "Python asyncio tutorial"
    python research_agent.py          # interactive mode
"""

import argparse
import os
import sys
import json
from pathlib import Path
from datetime import datetime

from groq import Groq
from dotenv import load_dotenv
from ddgs import DDGS

load_dotenv()

NOTES_DIR = Path("notes")


def get_client() -> Groq:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("Error: GROQ_API_KEY not set.")
        sys.exit(1)
    return Groq(api_key=api_key)


def search_web(query: str, max_results: int = 6) -> list:
    """Search DuckDuckGo and return structured results."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        return results
    except Exception as e:
        print(f"Search error: {e}")
        return []


def search_news(query: str, max_results: int = 6) -> list:
    """Search DuckDuckGo news for recent articles."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.news(query, max_results=max_results))
        return results
    except Exception as e:
        print(f"News search error: {e}")
        return []


def format_results(results: list, is_news: bool = False) -> str:
    """Format search results into a readable block for the model."""
    if not results:
        return "No results found."
    lines = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "No title")
        body = r.get("body", r.get("excerpt", ""))[:300]
        url = r.get("href", r.get("url", ""))
        lines.append(f"[{i}] {title}")
        lines.append(f"    {body}")
        if url:
            lines.append(f"    Source: {url}")
        lines.append("")
    return "\n".join(lines)


def generate_summary(client: Groq, topic: str, search_results: str) -> str:
    """Generate a clean, structured summary from search results."""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a research assistant. Given search results on a topic, "
                    "write a clear, structured summary that covers:\n"
                    "1. Key findings and main points\n"
                    "2. Important facts, numbers, or dates\n"
                    "3. Actionable insights or takeaways\n\n"
                    "Be concise but thorough. Use bullet points where appropriate. "
                    "Cite sources by number (e.g. [1], [2]) where relevant."
                ),
            },
            {
                "role": "user",
                "content": f"Topic: {topic}\n\nSearch results:\n{search_results}",
            },
        ],
    )
    return response.choices[0].message.content


def save_to_notes(topic: str, summary: str) -> Path:
    """Save research summary to notes folder."""
    NOTES_DIR.mkdir(exist_ok=True)

    # Create a clean filename from the topic
    safe_name = "".join(c if c.isalnum() or c in " -_" else "" for c in topic)
    safe_name = safe_name.strip().replace(" ", "_")[:50]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"research_{safe_name}_{timestamp}.txt"
    filepath = NOTES_DIR / filename

    content = f"""Research: {topic}
Date: {datetime.now().strftime("%B %d, %Y at %H:%M")}
{'=' * 60}

{summary}
"""
    filepath.write_text(content, encoding="utf-8")
    return filepath


def decide_search_type(client: Groq, topic: str) -> str:
    """Decide whether to use web search or news search."""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": (
                    "Decide whether this research topic needs 'news' (recent events, "
                    "current developments, latest updates) or 'web' (general knowledge, "
                    "tutorials, concepts, stable information). "
                    "Reply with ONLY one word: news or web."
                ),
            },
            {"role": "user", "content": topic},
        ],
    )
    result = response.choices[0].message.content.strip().lower()
    return "web"


def research(client: Groq, topic: str, save: bool = True) -> str:
    """Full research pipeline: search → summarize → save."""

    print(f"\nResearching: {topic}")

    # Decide search type
    search_type = decide_search_type(client, topic)
    print(f"Search type: {search_type}")

    # Search
    print("Searching the web...")
    if search_type == "news":
        results = search_news(topic)
    else:
        results = search_web(topic)

    if not results:
        return "No results found for that topic."

    print(f"Found {len(results)} results. Generating summary...")
    formatted = format_results(results, is_news=(search_type == "news"))

    # Generate summary
    summary = generate_summary(client, topic, formatted)

    # Save to notes
    if save:
        filepath = save_to_notes(topic, summary)
        print(f"Saved to: {filepath}")
        print("Re-indexing notes...")
        try:
            # Re-index notes so RAG picks up the new file
            from rag_assistant import build_index
            build_index()
            print("Notes re-indexed. You can now query this research with:")
            print(f'  python rag_assistant.py --ask-notes "what did you find about {topic}?"')
        except Exception as e:
            print(f"(Auto-index failed: {e} — run python rag_assistant.py --index manually)")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Jarvis research agent — search, summarize, save.")
    parser.add_argument("topic", nargs="?", help="What to research. Omit for interactive mode.")
    parser.add_argument("--no-save", action="store_true", help="Don't save results to notes.")
    args = parser.parse_args()

    client = get_client()

    if args.topic:
        result = research(client, args.topic, save=not args.no_save)
        print("\n" + "=" * 60)
        print(result)
        return

    print("Jarvis Research Agent — interactive mode. Type 'exit' to quit.")
    print("I'll search the web, summarize findings, and save to your notes.\n")
    while True:
        topic = input("What should I research? > ").strip()
        if topic.lower() in ("exit", "quit"):
            break
        if not topic:
            continue
        result = research(client, topic, save=True)
        print("\n" + "=" * 60)
        print(result)
        print()


if __name__ == "__main__":
    main()