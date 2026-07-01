import argparse, json, os, sys
from datetime import datetime
from pathlib import Path
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
TASKS_FILE = Path("tasks.json")

def load_tasks():
    if not TASKS_FILE.exists():
        return []
    return json.loads(TASKS_FILE.read_text(encoding="utf-8"))

def save_tasks(tasks):
    TASKS_FILE.write_text(json.dumps(tasks, indent=2), encoding="utf-8")

def add_task(title):
    tasks = load_tasks()
    task = {"id": len(tasks)+1, "title": title, "done": False}
    tasks.append(task)
    save_tasks(tasks)
    return f"Task added: [{task['id']}] {title}"

def list_tasks():
    tasks = load_tasks()
    if not tasks:
        return "No tasks yet."
    lines = [f"  [{t['id']}] {'done' if t['done'] else 'todo'} {t['title']}" for t in tasks]
    return "Your tasks:\n" + "\n".join(lines)

def complete_task(task_id):
    tasks = load_tasks()
    for t in tasks:
        if t["id"] == task_id:
            t["done"] = True
            save_tasks(tasks)
            return f"Marked done: [{task_id}] {t['title']}"
    return f"No task found with id {task_id}."

def delete_task(task_id):
    tasks = load_tasks()
    remaining = [t for t in tasks if t["id"] != task_id]
    if len(remaining) == len(tasks):
        return f"No task found with id {task_id}."
    save_tasks(remaining)
    return f"Deleted task {task_id}."

TOOL_DEFINITIONS = [
    {"type":"function","function":{"name":"add_task","description":"Add a new task.","parameters":{"type":"object","properties":{"title":{"type":"string"}},"required":["title"]}}},
    {"type":"function","function":{"name":"list_tasks","description":"List all tasks.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"complete_task","description":"Mark a task done by ID.","parameters":{"type":"object","properties":{"task_id":{"type":"integer"}},"required":["task_id"]}}},
    {"type":"function","function":{"name":"delete_task","description":"Delete a task by ID.","parameters":{"type":"object","properties":{"task_id":{"type":"integer"}},"required":["task_id"]}}},
]
TOOL_MAP = {"add_task":add_task,"list_tasks":list_tasks,"complete_task":complete_task,"delete_task":delete_task}

def get_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("Error: GROQ_API_KEY not set.")
        sys.exit(1)
    return Groq(api_key=api_key)

def run(client, user_input):
    messages = [{"role":"system","content":"You are a task manager. Always use a tool to act."},{"role":"user","content":user_input}]
    response = client.chat.completions.create(model="llama-3.3-70b-versatile",messages=messages,tools=TOOL_DEFINITIONS,tool_choice="auto",temperature=0.1)
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
            result = fn(**args) if fn else "Unknown tool"
            messages.append({"role":"tool","tool_call_id":tc.id,"content":result})
        final = client.chat.completions.create(model="llama-3.3-70b-versatile",messages=messages)
        return final.choices[0].message.content
    return msg.content or "Try: add, list, complete, or delete a task."

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("request", nargs="?")
    args = parser.parse_args()
    client = get_client()
    if args.request:
        print(run(client, args.request))
        return
    print("Interactive mode. Type exit to quit.")
    while True:
        user_input = input("\n> ").strip()
        if user_input.lower() in ("exit","quit"):
            break
        if user_input:
            print(run(client, user_input))

if __name__ == "__main__":
    main()
