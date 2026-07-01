import os, sys, json, base64, argparse
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
load_dotenv()
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from groq import Groq

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly","https://www.googleapis.com/auth/gmail.compose","https://www.googleapis.com/auth/gmail.modify"]
CREDENTIALS_FILE = Path("gmail_credentials.json")
TOKEN_FILE = Path("gmail_token.json")

def get_gmail_service():
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
    return build("gmail", "v1", credentials=creds)

def get_unread_emails(service, max_results=10):
    results = service.users().messages().list(userId="me", labelIds=["INBOX","UNREAD"], maxResults=max_results).execute()
    messages = results.get("messages", [])
    emails = []
    for msg in messages:
        full = service.users().messages().get(userId="me", id=msg["id"], format="metadata", metadataHeaders=["From","Subject","Date","To"]).execute()
        headers = {h["name"]: h["value"] for h in full["payload"]["headers"]}
        emails.append({"id": msg["id"], "from": headers.get("From","Unknown"), "to": headers.get("To",""), "subject": headers.get("Subject","No subject"), "date": headers.get("Date",""), "snippet": full.get("snippet","")})
    return emails

def format_emails_for_ai(emails):
    if not emails:
        return "No unread emails found."
    lines = []
    for i, e in enumerate(emails, 1):
        lines.append(f"[{i}] From: {e['from']}")
        lines.append(f"    Subject: {e['subject']}")
        lines.append(f"    Date: {e['date']}")
        lines.append(f"    Preview: {e['snippet'][:200]}")
        lines.append("")
    return "\n".join(lines)

def save_draft(service, to, subject, body):
    message = MIMEMultipart()
    message["to"] = to
    message["subject"] = subject
    message.attach(MIMEText(body, "plain"))
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    draft = service.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
    return draft["id"]

def get_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("Error: GROQ_API_KEY not set.")
        sys.exit(1)
    return Groq(api_key=api_key)

def decide_action(client, user_input):
    response = client.chat.completions.create(model="llama-3.3-70b-versatile", temperature=0, messages=[{"role":"system","content":"Classify into one word: read, summarize, draft, or find. No punctuation."},{"role":"user","content":user_input}])
    action = response.choices[0].message.content.strip().lower()
    return action if action in ("read","summarize","draft","find") else "read"

def process_emails(client, user_input, emails):
    email_text = format_emails_for_ai(emails)
    response = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"system","content":"You are Mandy, a personal AI assistant helping manage emails. Be concise and helpful."},{"role":"user","content":f"Request: {user_input}\n\nEmails:\n{email_text}"}])
    return response.choices[0].message.content

def draft_and_save(client, service, user_input, emails):
    email_text = format_emails_for_ai(emails)
    response = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"system","content":"You are Mandy drafting an email. Respond with ONLY a JSON object: {\"to\": \"email\", \"subject\": \"subject\", \"body\": \"body\"}. No other text."},{"role":"user","content":f"Draft request: {user_input}\n\nRecent emails:\n{email_text}"}])
    raw = response.choices[0].message.content.strip().replace("```json","").replace("```","").strip()
    try:
        data = json.loads(raw)
        to = data.get("to","")
        subject = data.get("subject","")
        body = data.get("body","")
    except Exception:
        return f"Could not parse draft:\n\n{raw}"
    try:
        draft_id = save_draft(service, to, subject, body)
        return f"Draft saved to Gmail Drafts!\n\nTo: {to}\nSubject: {subject}\n\n{body}\n\n(Open Gmail to review and send)"
    except Exception as e:
        return f"Draft generated but could not save ({e}).\n\nTo: {to}\nSubject: {subject}\n\n{body}"

def handle(client, service, user_input):
    action = decide_action(client, user_input)
    print(f"[Gmail Agent - {action}]")
    emails = get_unread_emails(service, max_results=10)
    if action == "draft":
        return draft_and_save(client, service, user_input, emails)
    else:
        return process_emails(client, user_input, emails)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("request", nargs="?")
    args = parser.parse_args()
    print("Connecting to Gmail...")
    service = get_gmail_service()
    print("Connected.\n")
    client = get_client()
    if args.request:
        print(handle(client, service, args.request))
        return
    print("Mandy Gmail Agent - interactive mode. Type exit to quit.\n")
    while True:
        user_input = input("> ").strip()
        if user_input.lower() in ("exit","quit"):
            break
        if not user_input:
            continue
        print(handle(client, service, user_input))
        print()

if __name__ == "__main__":
    main()
