#!/usr/bin/env python3
"""
Phase 2: ask questions about your own notes (RAG - Retrieval-Augmented Generation).

How it works:
    1. Put .txt files in a folder called "notes" (created automatically).
    2. Run --index to read those files, split them into chunks, and convert
       each chunk into an embedding (a vector representing its meaning).
       These are stored locally in notes_index.json.
    3. Run --ask-notes "question" to find the most relevant chunks for your
       question and have the model answer using only that content.

This is a separate script from ai_assistant.py (Phase 0/1) so the two
phases stay easy to read and compare. Phase 3+ will merge them into one
unified assistant.

Setup:
    pip install groq python-dotenv sentence-transformers numpy
    .env file in this folder containing: GROQ_API_KEY=your-key-here

Usage:
    python rag_assistant.py --index                  # (re)build the index from notes/*.txt
    python rag_assistant.py --ask-notes "question"    # ask using your notes as context
"""

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
from groq import Groq
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

NOTES_DIR = Path("notes")
INDEX_PATH = Path("notes_index.json")
CHUNK_SIZE = 500       # characters per chunk
CHUNK_OVERLAP = 50     # overlap so we don't cut a sentence in half between chunks
TOP_K = 3              # how many chunks to retrieve per question

_embedder = None  # loaded lazily, since loading the model takes a few seconds


def get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        print("Loading embedding model (first run only, takes a moment)...")
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP):
    """Split text into overlapping chunks so context isn't lost at chunk boundaries."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return [c.strip() for c in chunks if c.strip()]


def build_index():
    """Read every .txt file in notes/, chunk it, embed each chunk, save to disk."""
    NOTES_DIR.mkdir(exist_ok=True)
    txt_files = list(NOTES_DIR.glob("*.txt"))

    if not txt_files:
        print(f"No .txt files found in '{NOTES_DIR}/'. Add some notes there first.")
        return

    embedder = get_embedder()
    records = []  # each record: {source, text, embedding}

    for file_path in txt_files:
        text = file_path.read_text(encoding="utf-8")
        chunks = chunk_text(text)
        print(f"  {file_path.name}: {len(chunks)} chunks")
        embeddings = embedder.encode(chunks).tolist()
        for chunk, embedding in zip(chunks, embeddings):
            records.append({
                "source": file_path.name,
                "text": chunk,
                "embedding": embedding,
            })

    INDEX_PATH.write_text(json.dumps(records), encoding="utf-8")
    print(f"Indexed {len(records)} chunks from {len(txt_files)} file(s) into {INDEX_PATH}")


def load_index():
    if not INDEX_PATH.exists():
        print("No index found. Run with --index first.")
        sys.exit(1)
    return json.loads(INDEX_PATH.read_text(encoding="utf-8"))


def retrieve_relevant_chunks(question: str, records: list, top_k: int = TOP_K):
    """Embed the question, compare it to every stored chunk via cosine similarity,
    and return the most similar ones."""
    embedder = get_embedder()
    question_vec = np.array(embedder.encode(question))

    scored = []
    for record in records:
        chunk_vec = np.array(record["embedding"])
        similarity = np.dot(question_vec, chunk_vec) / (
            np.linalg.norm(question_vec) * np.linalg.norm(chunk_vec)
        )
        scored.append((similarity, record))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [record for _, record in scored[:top_k]]


def get_client() -> Groq:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("Error: GROQ_API_KEY environment variable is not set.")
        sys.exit(1)
    return Groq(api_key=api_key)


def ask_notes(client: Groq, question: str):
    records = load_index()
    relevant = retrieve_relevant_chunks(question, records)

    context = "\n\n".join(f"[From {r['source']}]\n{r['text']}" for r in relevant)
    system_prompt = (
        "Answer the user's question using ONLY the context provided below. "
        "The context is written in the user's own words (first person, 'I'). "
        "Rephrase your answer in second person, addressing the user directly "
        "(e.g. 'Your name is...', 'You are learning...'), as a helpful assistant "
        "would. If the context doesn't contain the answer, say you don't have "
        "that information in the notes, rather than guessing.\n\n"
        f"Context:\n{context}"
    )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
    )

    print(response.choices[0].message.content)
    print("\n--- Sources used ---")
    for r in relevant:
        print(f"  {r['source']}: \"{r['text'][:80]}...\"")


def main():
    parser = argparse.ArgumentParser(description="Ask questions about your own notes.")
    parser.add_argument("--index", action="store_true", help="Build/rebuild the notes index.")
    parser.add_argument("--ask-notes", metavar="QUESTION", help="Ask a question using your notes.")
    args = parser.parse_args()

    if args.index:
        build_index()
        return

    if args.ask_notes:
        client = get_client()
        ask_notes(client, args.ask_notes)
        return

    parser.print_help()


if __name__ == "__main__":
    main()