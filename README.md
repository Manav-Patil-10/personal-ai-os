# Personal AI OS

A personal AI operating system built from scratch — from a basic CLI chatbot to a multi-agent system with persistent memory, document retrieval, tool-calling, proactive briefings, a web dashboard, and a local privacy mode.

Built as a portfolio project to demonstrate progressive AI engineering skills across 8 phases.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Interfaces                        │
│   CLI (Phase 0)   Web Dashboard (6)   Scheduler (5)  │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│              Orchestrator (Phase 4)                  │
│         Intent classification → agent routing        │
└────────┬─────────────┬──────────────────┬───────────┘
         │             │                  │
┌────────▼──┐   ┌──────▼──────┐   ┌──────▼──────┐
│ Chat agent│   │ Notes agent │   │ Task agent  │
│ Phase 0/1 │   │  Phase 2    │   │  Phase 3    │
└────────┬──┘   └──────┬──────┘   └──────┬──────┘
         │             │                  │
┌────────▼──┐   ┌──────▼──────┐   ┌──────▼──────┐
│ memory.db │   │notes index  │   │ tasks.json  │
│  SQLite   │   │ embeddings  │   │  local file │
└───────────┘   └─────────────┘   └─────────────┘
         │             │                  │
┌────────▼─────────────▼──────────────────▼───────────┐
│                   Infrastructure                     │
│   Groq API (cloud)   Ollama (local)   sentence-      │
│                                       transformers   │
└─────────────────────────────────────────────────────┘
```

---

## Phases

| Phase | File | What it does |
|---|---|---|
| 0 | `ai_assistant.py` | CLI assistant with swappable personas via system prompt |
| 1 | `ai_assistant.py` | Adds cross-session memory via SQLite |
| 2 | `rag_assistant.py` | Ask questions about your own `.txt` notes (RAG) |
| 3 | `task_assistant.py` | Natural language task manager using tool-calling |
| 4 | `orchestrator.py` | Routes requests to the right specialist agent |
| 5 | `proactive.py` | Daily briefing generated automatically on a schedule |
| 6 | `app.py` | Web dashboard: chat, task panel, briefing button |
| 7 | `private_assistant.py` | Cloud/local toggle + data flow audit + threat model |

---

## Setup

**1. Clone the repo:**
```bash
git clone https://github.com/Manav-Patil-10/personal-ai-os.git
cd personal-ai-os
```

**2. Install dependencies:**
```bash
pip install groq python-dotenv sentence-transformers numpy flask schedule
```

**3. Create a `.env` file:**
```
GROQ_API_KEY=your-key-here
```
Get a free key at https://console.groq.com/keys

**4. Optional — install Ollama for local/private mode:**
Download from https://ollama.com, then:
```bash
ollama pull llama3.2
```

---

## Usage

**Chat with memory:**
```bash
python ai_assistant.py "What should I learn next?"
python ai_assistant.py --history
```

**Ask your notes:**
```bash
python rag_assistant.py --index
python rag_assistant.py --ask-notes "What am I currently working on?"
```

**Task manager:**
```bash
python task_assistant.py "add a task to review my notes"
python task_assistant.py "show my tasks"
python task_assistant.py "mark task 1 as done"
```

**Orchestrator:**
```bash
python orchestrator.py "add a task to study embeddings"
python orchestrator.py "what are my goals according to my notes?"
python orchestrator.py "explain what RAG means"
```

**Daily briefing:**
```bash
python proactive.py --now
python proactive.py --time 08:00
```

**Web dashboard:**
```bash
python app.py
# open http://127.0.0.1:5000
```

**Privacy mode:**
```bash
python private_assistant.py --audit
python private_assistant.py --local "sensitive question"
```

---

## Design decisions

**Why personas live in the system prompt** — persists across the whole conversation, shapes model behavior throughout, doesn't clutter the context window per-message.

**Why SQLite for memory** — structured queries (`SELECT ... ORDER BY id DESC LIMIT 10`) are trivial; replicating this in a text file means reading everything every time.

**Why local embeddings** — notes never leave your machine during indexing. Only the final answer generation hits an external API, with just the small relevant excerpt.

**Why zero temperature for intent classification** — routing decisions must be deterministic. The same input should always go to the same agent.

**Why --local is a flag, not the default** — makes the privacy tradeoff explicit and deliberate.

---

## What is excluded from Git

```
.env             # API key
memory.db        # conversation history
notes/           # personal documents
notes_index.json # embeddings of personal documents
tasks.json       # task list
briefings.log    # daily briefings
```

The code is public. The data is yours.

---

## Tech stack

- **LLM:** Groq API (cloud) / Ollama (local)
- **Embeddings:** sentence-transformers (all-MiniLM-L6-v2)
- **Memory:** SQLite
- **Web framework:** Flask
- **Scheduler:** schedule
- **Language:** Python 3.10+