#!/usr/bin/env python3
"""
Tier 2 upgrade: orchestrator with agent memory sharing.

Agents can now pass context to each other within a single request.
The orchestrator detects multi-step requests and chains agents automatically.

New behavior:
  - Single-agent requests work exactly as before
  - Multi-step requests (e.g. "read my notes AND add a task") chain agents
  - Each agent's output becomes context for the next agent

Usage:
    python orchestrator.py "what am I learning?"                         # single agent
    python orchestrator.py "read my goals and add a task for next phase" # chained agents
    python orchestrator.py        # interactive mode
"""

import json
import os
import sys
import argparse
from pathlib import Path

from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# ── Agent imports ──────────────────────────────────────────────────────────────

from task_assistant import (
    TOOL_DEFINITIONS as TASK_TOOL_DEFINITIONS,
    TOOL_MAP as TASK_TOOL_MAP,
)


def get_client() -> Groq:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("Error: GROQ_API_KEY not set.")
        sys.exit(1)
    return Groq(api_key=api_key)


# ── Shared context ─────────────────────────────────────────────────────────────

class SharedContext:
    """Passed between agents so each one can read what previous agents found."""
    def __init__(self):
        self.entries = []

    def add(self, agent: str, content: str):
        self.entries.append({"agent": agent, "content": content})

    def as_text(self) -> str:
        if not self.entries:
            return ""
        lines = ["Context from previous agents:"]
        for e in self.entries:
            lines.append(f"\n[{e['agent']}]: {e['content']}")
        return "\n".join(lines)

    def has_content(self) -> bool:
        return len(self.entries) > 0


# ── Intent planning ────────────────────────────────────────────────────────────

def plan_agents(client: Groq, user_input: str) -> list:
    """
    Decide which agents to run and in what order.
    Returns a list like ["notes", "task"] or ["chat"].
    """
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": (
                    "Decide which agents to run for the user's request. "
                    "Available agents:\n"
                    "- 'notes': retrieve info from personal notes/documents\n"
                    "- 'task': add, list, complete, or delete tasks\n"
                    "- 'chat': general questions and conversation\n\n"
                    "Respond with ONLY a JSON array of agent names in execution order. "
                    "Examples:\n"
                    '["notes"] — just a notes lookup\n'
                    '["task"] — just a task action\n'
                    '["chat"] — general question\n'
                    '["notes", "task"] — look up notes THEN create a task based on them\n'
                    '["task", "chat"] — check tasks THEN answer a question about them\n\n'
                    "Use multiple agents only when the request clearly needs both. "
                    "Respond with ONLY the JSON array, nothing else."
                ),
            },
            {"role": "user", "content": user_input},
        ],
    )
    text = response.choices[0].message.content.strip()
    try:
        text = text.replace("```json", "").replace("```", "").strip()
        agents = json.loads(text)
        if isinstance(agents, list) and all(a in ("notes", "task", "chat") for a in agents):
            return agents
    except Exception:
        pass
    return ["chat"]


# ── Specialist agents ──────────────────────────────────────────────────────────

def run_task_agent(client: Groq, user_input: str, ctx: SharedContext) -> str:
    context_text = ctx.as_text()
    system = "You are a task manager. Always use a tool to act on the user's request."
    if context_text:
        system += f"\n\n{context_text}\nUse this context to make the task more specific and useful."

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_input},
    ]
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        tools=TASK_TOOL_DEFINITIONS,
        tool_choice="auto",
        temperature=0.1,
    )
    msg = response.choices[0].message
    if msg.tool_calls:
        messages.append(msg)
        for tc in msg.tool_calls:
            fn = TASK_TOOL_MAP.get(tc.function.name)
            try:
                args = json.loads(tc.function.arguments) if tc.function.arguments else {}
            except Exception:
                args = {}
            if not isinstance(args, dict):
                args = {}
            result = fn(**args) if fn else f"Unknown tool: {tc.function.name}"
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
        final = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
        )
        return final.choices[0].message.content
    return msg.content or "Could not perform task action."


def run_notes_agent(client: Groq, user_input: str, ctx: SharedContext) -> str:
    index_file = Path("notes_index.json")
    if not index_file.exists():
        return "No notes indexed. Run: python rag_assistant.py --index"

    import numpy as np
    from sentence_transformers import SentenceTransformer

    records = json.loads(index_file.read_text(encoding="utf-8"))
    embedder = SentenceTransformer("all-MiniLM-L6-v2")
    q_vec = np.array(embedder.encode(user_input))
    scored = []
    for r in records:
        v = np.array(r["embedding"])
        sim = np.dot(q_vec, v) / (np.linalg.norm(q_vec) * np.linalg.norm(v))
        scored.append((sim, r))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = [r for _, r in scored[:3]]
    context = "\n\n".join(f"[{r['source']}]\n{r['text']}" for r in top)

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": f"Answer using ONLY this context, in second person:\n\n{context}"},
            {"role": "user", "content": user_input},
        ],
    )
    return response.choices[0].message.content


def run_chat_agent(client: Groq, user_input: str, ctx: SharedContext) -> str:
    system = "You are a helpful, direct personal assistant."
    if ctx.has_content():
        system += f"\n\n{ctx.as_text()}"

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_input},
        ],
    )
    return response.choices[0].message.content


# ── Orchestrator ───────────────────────────────────────────────────────────────

AGENT_RUNNERS = {
    "notes": run_notes_agent,
    "task": run_task_agent,
    "chat": run_chat_agent,
}

AGENT_LABELS = {
    "notes": "Notes Agent",
    "task": "Task Agent",
    "chat": "Chat Agent",
}


def orchestrate(client: Groq, user_input: str) -> str:
    agents = plan_agents(client, user_input)
    ctx = SharedContext()
    results = []

    for agent_name in agents:
        runner = AGENT_RUNNERS[agent_name]
        label = AGENT_LABELS[agent_name]
        result = runner(client, user_input, ctx)
        ctx.add(label, result)
        results.append(f"[{label}]\n{result}")

    return "\n\n".join(results)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Personal AI OS orchestrator with agent memory sharing.")
    parser.add_argument("request", nargs="?", help="What you want. Omit for interactive mode.")
    parser.add_argument("--chain", nargs="+", choices=["notes", "task", "chat"],
                        help="Force a specific agent chain e.g. --chain notes task")
    args = parser.parse_args()

    client = get_client()

    if args.request:
        if args.chain:
            ctx = SharedContext()
            results = []
            for agent_name in args.chain:
                runner = AGENT_RUNNERS[agent_name]
                label = AGENT_LABELS[agent_name]
                result = runner(client, args.request, ctx)
                ctx.add(label, result)
                results.append(f"[{label}]\n{result}")
            print("\n\n".join(results))
        else:
            print(orchestrate(client, args.request))
        return

    print("Personal AI OS — interactive mode. Type 'exit' to quit.")
    print("I'll route your request to the right agent(s) automatically.\n")
    while True:
        user_input = input("> ").strip()
        if user_input.lower() in ("exit", "quit"):
            break
        if not user_input:
            continue
        print(orchestrate(client, user_input))
        print()


if __name__ == "__main__":
    main()