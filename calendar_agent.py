#!/usr/bin/env python3
"""
Mandy Calendar Agent — manage your Google Calendar through natural language.

First run: opens browser to authorize Calendar access.

Usage:
    python calendar_agent.py "what's on my schedule today?"
    python calendar_agent.py "add a meeting with John tomorrow at 3pm"
    python calendar_agent.py "what do I have this week?"
    python calendar_agent.py          # interactive mode
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import dateutil.parser

from dotenv import load_dotenv
load_dotenv()

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from groq import Groq

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.modify",
]
CREDENTIALS_FILE = Path("gmail_credentials.json")
TOKEN_FILE = Path("gmail_token.json")


# ── Auth ───────────────────────────────────────────────────────────────────────

def get_calendar_service():
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                print("Error: gmail_credentials.json not found.")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    return build("calendar", "v3", credentials=creds)


# ── Calendar helpers ───────────────────────────────────────────────────────────

def get_upcoming_events(service, days=7, max_results=20) -> list:
    now = datetime.utcnow().isoformat() + "Z"
    end = (datetime.utcnow() + timedelta(days=days)).isoformat() + "Z"

    events_result = service.events().list(
        calendarId="primary",
        timeMin=now,
        timeMax=end,
        maxResults=max_results,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    return events_result.get("items", [])


def get_today_events(service) -> list:
    now = datetime.utcnow()
    start = datetime(now.year, now.month, now.day).isoformat() + "Z"
    end = datetime(now.year, now.month, now.day, 23, 59, 59).isoformat() + "Z"

    events_result = service.events().list(
        calendarId="primary",
        timeMin=start,
        timeMax=end,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    return events_result.get("items", [])


def format_events(events: list) -> str:
    if not events:
        return "No events found."
    lines = []
    for e in events:
        start = e["start"].get("dateTime", e["start"].get("date", ""))
        try:
            dt = dateutil.parser.parse(start)
            formatted_time = dt.strftime("%A, %B %d at %I:%M %p")
        except Exception:
            formatted_time = start
        summary = e.get("summary", "No title")
        location = e.get("location", "")
        lines.append(f"• {summary}")
        lines.append(f"  {formatted_time}")
        if location:
            lines.append(f"  📍 {location}")
        lines.append("")
    return "\n".join(lines)


def create_event(service, title: str, start_time: str, end_time: str, description: str = "", location: str = "") -> dict:
    event = {
        "summary": title,
        "description": description,
        "location": location,
        "start": {"dateTime": start_time, "timeZone": "Asia/Kolkata"},
        "end": {"dateTime": end_time, "timeZone": "Asia/Kolkata"},
    }
    return service.events().insert(calendarId="primary", body=event).execute()


# ── AI layer ───────────────────────────────────────────────────────────────────

def get_client() -> Groq:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("Error: GROQ_API_KEY not set.")
        sys.exit(1)
    return Groq(api_key=api_key)


def decide_action(client: Groq, user_input: str) -> str:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": (
                    "Classify the calendar request into one word:\n"
                    "- 'today' : what's on today's schedule\n"
                    "- 'week' : what's coming up this week\n"
                    "- 'add' : add/create/schedule a new event\n"
                    "- 'check' : check availability or find free time\n"
                    "Reply with ONLY one word."
                ),
            },
            {"role": "user", "content": user_input},
        ],
    )
    action = response.choices[0].message.content.strip().lower()
    return action if action in ("today", "week", "add", "check") else "today"


def parse_and_create_event(client: Groq, service, user_input: str) -> str:
    now = datetime.now()
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    f"Today is {now.strftime('%A, %B %d, %Y %I:%M %p')} IST.\n"
                    "Extract event details from the user's request and respond with ONLY a JSON object:\n"
                    '{"title": "event title", "start": "YYYY-MM-DDTHH:MM:SS", "end": "YYYY-MM-DDTHH:MM:SS", "location": "", "description": ""}\n'
                    "Use IST timezone. If no duration given, assume 1 hour. No other text."
                ),
            },
            {"role": "user", "content": user_input},
        ],
    )

    raw = response.choices[0].message.content.strip().replace("```json", "").replace("```", "").strip()

    try:
        data = json.loads(raw)
        event = create_event(
            service,
            title=data.get("title", "New Event"),
            start_time=data.get("start", ""),
            end_time=data.get("end", ""),
            description=data.get("description", ""),
            location=data.get("location", ""),
        )
        link = event.get("htmlLink", "")
        return (
            f"Event created!\n\n"
            f"📅 {data.get('title')}\n"
            f"🕐 {data.get('start')} to {data.get('end')}\n"
            f"{'📍 ' + data.get('location') if data.get('location') else ''}\n"
            f"\nOpen in Google Calendar: {link}"
        )
    except Exception as e:
        return f"Could not create event: {e}\n\nRaw response: {raw}"


def answer_schedule(client: Groq, user_input: str, events: list) -> str:
    events_text = format_events(events)
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": "You are Mandy, a personal AI assistant. Answer questions about the user's calendar clearly and helpfully.",
            },
            {
                "role": "user",
                "content": f"Request: {user_input}\n\nCalendar events:\n{events_text}",
            },
        ],
    )
    return response.choices[0].message.content


# ── Main handler ───────────────────────────────────────────────────────────────

def handle(client: Groq, service, user_input: str) -> str:
    action = decide_action(client, user_input)
    print(f"[Calendar Agent — {action}]")

    if action == "add":
        return parse_and_create_event(client, service, user_input)
    elif action == "today":
        events = get_today_events(service)
        return answer_schedule(client, user_input, events)
    else:
        events = get_upcoming_events(service, days=7)
        return answer_schedule(client, user_input, events)


def main():
    parser = argparse.ArgumentParser(description="Mandy Calendar Agent")
    parser.add_argument("request", nargs="?", help="What to do with your calendar.")
    args = parser.parse_args()

    print("Connecting to Google Calendar...")
    service = get_calendar_service()
    print("Connected.\n")

    client = get_client()

    if args.request:
        print(handle(client, service, args.request))
        return

    print("Mandy Calendar Agent — interactive mode. Type 'exit' to quit.\n")
    while True:
        user_input = input("> ").strip()
        if user_input.lower() in ("exit", "quit"):
            break
        if not user_input:
            continue
        print(handle(client, service, user_input))
        print()


if __name__ == "__main__":
    main()