#!/usr/bin/env python3
"""
Phase 6: Web dashboard for the Mandy.

A simple Flask web app that lets you interact with your AI OS through
a browser instead of the terminal.

Features:
  - Chat interface connected to the orchestrator
  - Live task list panel
  - Daily briefing on demand

Setup:
    pip install flask groq python-dotenv
    .env file with GROQ_API_KEY=your-key-here

Usage:
    python app.py
    Then open http://localhost:5000 in your browser.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template_string, request
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

app = Flask(__name__)

# ── Helpers ────────────────────────────────────────────────────────────────────

def get_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("Error: GROQ_API_KEY not set.")
        sys.exit(1)
    return Groq(api_key=api_key)

client = get_client()

def get_tasks():
    tasks_file = Path("tasks.json")
    if not tasks_file.exists():
        return []
    return json.loads(tasks_file.read_text(encoding="utf-8"))

def save_tasks(tasks):
    Path("tasks.json").write_text(json.dumps(tasks, indent=2), encoding="utf-8")

# ── Orchestrator (inline, no import needed) ────────────────────────────────────

def classify_intent(user_input):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        temperature=0,
        messages=[
            {"role": "system", "content": "Classify the request into exactly one word: task, notes, or chat. No punctuation."},
            {"role": "user", "content": user_input},
        ],
    )
    intent = response.choices[0].message.content.strip().lower()
    return intent if intent in ("task", "notes", "chat") else "chat"

def run_chat(user_input):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a helpful personal assistant."},
            {"role": "user", "content": user_input},
        ],
    )
    return response.choices[0].message.content

def run_task_agent(user_input):
    from task_assistant import TOOL_DEFINITIONS, TOOL_MAP
    messages = [
        {"role": "system", "content": "You are a task manager. Always use a tool."},
        {"role": "user", "content": user_input},
    ]
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        tools=TOOL_DEFINITIONS,
        tool_choice="auto",
        temperature=0.1,
    )
    msg = response.choices[0].message
    if msg.tool_calls:
        messages.append(msg)
        for tc in msg.tool_calls:
            fn = TOOL_MAP.get(tc.function.name)
            try:
                args = json.loads(tc.function.arguments) if tc.function.arguments else {}
            except Exception:
                args = {}
            if not isinstance(args, dict):
                args = {}
            result = fn(**args) if fn else f"Unknown tool: {tc.function.name}"
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
        final = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=messages)
        return final.choices[0].message.content
    return msg.content or "Could not perform task action."

def run_notes_agent(user_input):
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

def orchestrate(user_input):
    intent = classify_intent(user_input)
    label = {"task": "Task Agent", "notes": "Notes Agent", "chat": "Chat Agent"}[intent]
    if intent == "task":
        result = run_task_agent(user_input)
    elif intent == "notes":
        result = run_notes_agent(user_input)
    else:
        result = run_chat(user_input)
    return label, result

def generate_briefing():
    tasks = get_tasks()
    pending = [t for t in tasks if not t["done"]]
    task_text = "\n".join(f"- {t['title']}" for t in pending) if pending else "No pending tasks."
    today = datetime.now().strftime("%A, %B %d, %Y")
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a personal assistant generating a morning briefing."},
            {"role": "user", "content": f"Today is {today}. Pending tasks:\n{task_text}\n\nGenerate a short, friendly briefing under 100 words."},
        ],
    )
    return response.choices[0].message.content

# ── HTML template ──────────────────────────────────────────────────────────────

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Mandy</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', sans-serif; background: #0f0f0f; color: #e0e0e0; height: 100vh; display: flex; flex-direction: column; }
  header { background: #1a1a2e; padding: 16px 24px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #333; }
  header h1 { font-size: 1.2rem; color: #7c6af7; letter-spacing: 1px; }
  header span { font-size: 0.8rem; color: #888; }
  .main { display: flex; flex: 1; overflow: hidden; }
  .sidebar { width: 280px; background: #141414; border-right: 1px solid #222; display: flex; flex-direction: column; }
  .sidebar h2 { padding: 16px; font-size: 0.85rem; color: #888; text-transform: uppercase; letter-spacing: 1px; border-bottom: 1px solid #222; }
  .task-list { flex: 1; overflow-y: auto; padding: 8px; }
  .task-item { padding: 10px 12px; border-radius: 8px; margin-bottom: 6px; background: #1e1e1e; font-size: 0.88rem; display: flex; align-items: center; gap: 10px; }
  .task-item.done { opacity: 0.5; text-decoration: line-through; }
  .task-dot { width: 8px; height: 8px; border-radius: 50%; background: #7c6af7; flex-shrink: 0; }
  .task-item.done .task-dot { background: #444; }
  .briefing-btn { margin: 12px; padding: 10px; background: #7c6af7; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 0.85rem; }
  .briefing-btn:hover { background: #6a5ae0; }
  .chat-area { flex: 1; display: flex; flex-direction: column; }
  .messages { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 16px; }
  .message { max-width: 75%; }
  .message.user { align-self: flex-end; }
  .message.user .bubble { background: #7c6af7; color: white; border-radius: 18px 18px 4px 18px; }
  .message.bot .bubble { background: #1e1e1e; border-radius: 18px 18px 18px 4px; }
  .bubble { padding: 12px 16px; font-size: 0.9rem; line-height: 1.5; }
  .label { font-size: 0.72rem; color: #666; margin-bottom: 4px; padding: 0 4px; }
  .input-area { padding: 16px; border-top: 1px solid #222; display: flex; gap: 10px; }
  .input-area input { flex: 1; background: #1e1e1e; border: 1px solid #333; color: #e0e0e0; padding: 12px 16px; border-radius: 24px; font-size: 0.9rem; outline: none; }
  .input-area input:focus { border-color: #7c6af7; }
  .input-area button { background: #7c6af7; color: white; border: none; border-radius: 24px; padding: 12px 20px; cursor: pointer; font-size: 0.9rem; }
  .input-area button:hover { background: #6a5ae0; }
  .thinking { color: #666; font-style: italic; font-size: 0.85rem; }
</style>
</head>
<body>
<header>
  <h1>⚡ Mandy</h1>
  <span id="clock"></span>
</header>
<div class="main">
  <div class="sidebar">
    <h2>Tasks</h2>
    <div class="task-list" id="taskList">Loading...</div>
    <button class="briefing-btn" onclick="getBriefing()">📋 Get Daily Briefing</button>
  </div>
  <div class="chat-area">
    <div class="messages" id="messages">
      <div class="message bot">
        <div class="label">Mandy</div>
        <div class="bubble">Hello! I'm your Mandy. Ask me anything, manage your tasks, or query your notes.</div>
      </div>
    </div>
    <div class="input-area">
      <input type="text" id="userInput" placeholder="Ask anything..." onkeydown="if(event.key==='Enter') sendMessage()">
      <button onclick="sendMessage()">Send</button>
    </div>
  </div>
</div>
<script>
  function updateClock() {
    document.getElementById('clock').textContent = new Date().toLocaleTimeString();
  }
  setInterval(updateClock, 1000);
  updateClock();

  async function loadTasks() {
    const res = await fetch('/api/tasks');
    const tasks = await res.json();
    const list = document.getElementById('taskList');
    if (tasks.length === 0) {
      list.innerHTML = '<div style="padding:12px;color:#666;font-size:0.85rem;">No tasks yet.</div>';
      return;
    }
    list.innerHTML = tasks.map(t =>
      `<div class="task-item ${t.done ? 'done' : ''}">
        <div class="task-dot"></div>
        <span>${t.title}</span>
      </div>`
    ).join('');
  }

  async function sendMessage() {
    const input = document.getElementById('userInput');
    const text = input.value.trim();
    if (!text) return;
    input.value = '';
    appendMessage('user', '', text);
    const thinking = appendMessage('bot', 'Thinking...', '...');
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: text})
    });
    const data = await res.json();
    thinking.remove();
    appendMessage('bot', data.agent, data.response);
    loadTasks();
  }

  async function getBriefing() {
    appendMessage('bot', 'Generating briefing...', '...');
    const res = await fetch('/api/briefing');
    const data = await res.json();
    document.querySelector('.messages .thinking')?.remove();
    const msgs = document.getElementById('messages');
    const last = msgs.lastElementChild;
    if (last && last.querySelector('.thinking')) last.remove();
    appendMessage('bot', 'Daily Briefing', data.briefing);
  }

  function appendMessage(role, label, text) {
    const msgs = document.getElementById('messages');
    const div = document.createElement('div');
    div.className = `message ${role}`;
    div.innerHTML = `${label ? `<div class="label">${label}</div>` : ''}<div class="bubble">${text.replace(/\\n/g, '<br>')}</div>`;
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
    return div;
  }

  loadTasks();
</script>
</body>
</html>
"""

# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/api/tasks")
def api_tasks():
    return jsonify(get_tasks())

@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json()
    user_input = data.get("message", "").strip()
    if not user_input:
        return jsonify({"agent": "Error", "response": "Empty message."})
    agent, response = orchestrate(user_input)
    return jsonify({"agent": agent, "response": response})

@app.route("/api/briefing")
def api_briefing():
    briefing = generate_briefing()
    return jsonify({"briefing": briefing})

# ── Run ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Starting Mandy dashboard...")
    print("Open http://localhost:5000 in your browser.\n")
    app.run(debug=False, port=5000)