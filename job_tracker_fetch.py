"""
job_tracker_fetch.py
--------------------
Job Application Dashboard - Gmail Fetcher
Searches Gmail for job-related emails, classifies them,
and merges new records into job_tracker_data.json.

Usage:
    python job_tracker_fetch.py [--days N] [--dry-run]

Requirements:
    pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client

OAuth Setup (first time only):
    1. Go to https://console.cloud.google.com/
    2. Create a project -> Enable Gmail API
    3. Create OAuth 2.0 Desktop credentials -> Download as credentials.json
    4. Place credentials.json in the SAME folder as this script
    5. Run this script once -> browser opens -> sign in -> token.json saved automatically
    6. All future runs use token.json silently
"""

import json
import re
import argparse
import sys
from datetime import datetime
from pathlib import Path

# ── Paths (all relative to this script's folder) ──────────────────────────────
SCRIPT_DIR = Path(__file__).parent
DATA_FILE  = SCRIPT_DIR / "job_tracker_data.json"
CREDS_FILE = SCRIPT_DIR / "credentials.json"
TOKEN_FILE = SCRIPT_DIR / "token.json"

# ── Classification patterns ───────────────────────────────────────────────────
REJECTION_PATTERNS = [
    r"not selected", r"not moving forward", r"decided not to proceed",
    r"will not be moving forward", r"not be proceeding", r"unfortunately",
    r"other candidates", r"not a match", r"not be considering",
    r"not be advancing", r"position has been filled",
]
ACTION_PATTERNS = [
    r"action required", r"still looking for a job", r"check if you.?re still",
    r"response required", r"please respond", r"confirm your interest",
    r"follow.up required",
]
INTERVIEW_PATTERNS = [
    r"interview", r"next steps", r"move forward with you", r"schedule a call",
    r"would like to speak", r"time sensitive", r"connect with you",
    r"phone screen", r"video call", r"assessment",
]
VIEWED_PATTERNS    = [r"viewed your application", r"application was viewed"]
CONFIRMATION_PATTERNS = [
    r"thank you for applying", r"application has been received",
    r"officially applied", r"received your application",
    r"application submitted", r"thank you for your (interest|application)",
    r"we (will review|have received)",
]
APPLIED_PATTERNS = [
    r"your application (was sent|to .+ at .+)",
    r"track your application",
    r"application sent",
]

GMAIL_QUERIES = [
    'subject:("thank you for applying" OR "application received" OR "application submitted" OR "officially applied") newer_than:{days}d',
    'subject:("not selected" OR "not moving forward" OR "unfortunately" OR "other candidates") newer_than:{days}d',
    '("application was viewed" OR "viewed your application") newer_than:{days}d',
    '(from:jobs-noreply@linkedin.com OR from:jobalerts-noreply@linkedin.com) newer_than:{days}d',
    'subject:("next steps" OR "interview" OR "time sensitive" OR "schedule") newer_than:{days}d',
    '("action required" OR "still looking for a job" OR "confirm your interest") newer_than:{days}d',
]

# ── Classification helpers ────────────────────────────────────────────────────
def classify_email(subject, snippet, sender):
    text = (subject + " " + snippet + " " + sender).lower()
    for pat in REJECTION_PATTERNS:
        if re.search(pat, text): return "Rejected"
    for pat in ACTION_PATTERNS:
        if re.search(pat, text): return "Action Required"
    for pat in INTERVIEW_PATTERNS:
        if re.search(pat, text): return "Interview/Next Steps"
    for pat in VIEWED_PATTERNS:
        if re.search(pat, text): return "Viewed"
    for pat in CONFIRMATION_PATTERNS:
        if re.search(pat, text): return "Confirmed"
    for pat in APPLIED_PATTERNS:
        if re.search(pat, text): return "Applied"
    return "Applied"

def extract_company(subject, snippet, sender):
    m = re.search(r'application to .+ at (.+?)(?:\.|$)', subject, re.IGNORECASE)
    if m: return m.group(1).strip()
    m = re.search(r'application was sent to (.+?)(?:\.|$)', subject, re.IGNORECASE)
    if m: return m.group(1).strip()
    m = re.search(r'@([\w.-]+)\.(com|org|io|co)', sender)
    if m: return m.group(1).split('.')[-1].title()
    return "(Unknown)"

def extract_role(subject, snippet):
    m = re.search(r'application to (.+?) at ', subject, re.IGNORECASE)
    if m: return m.group(1).strip()
    m = re.search(r'Track Your Application: .+? (.+)', subject, re.IGNORECASE)
    if m: return m.group(1).strip()
    return "(Not specified)"

def detect_source(sender):
    s = sender.lower()
    for key, label in [
        ("linkedin","LinkedIn"), ("workday","Workday"), ("myworkdayjobs","Workday"),
        ("greenhouse","Greenhouse"), ("lever","Lever"), ("ashby","Ashby"),
        ("ycombinator","YC"), ("lensa","Lensa"), ("mercor","Mercor"),
        ("teamtailor","TeamTailor"), ("clearcompany","ClearCompany"),
    ]:
        if key in s: return label
    return "Direct"

def parse_date(date_str):
    import email.utils
    try:
        return email.utils.parsedate_to_datetime(date_str).strftime("%Y-%m-%d")
    except Exception:
        return datetime.now().strftime("%Y-%m-%d")

# ── Gmail fetch ───────────────────────────────────────────────────────────────
def fetch_gmail(days=30):
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError:
        print("[ERROR] Install: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
        return []

    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDS_FILE.exists():
                print(f"[ERROR] credentials.json not found at {CREDS_FILE}")
                print("  See README.md for OAuth setup instructions.")
                return []
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json())

    service = build("gmail", "v1", credentials=creds)
    messages, seen = [], set()

    for query_template in GMAIL_QUERIES:
        query = query_template.format(days=days)
        print(f"  [SEARCH] {query[:72]}...")
        try:
            result = service.users().messages().list(userId="me", q=query, maxResults=50).execute()
            for ref in result.get("messages", []):
                mid = ref["id"]
                if mid in seen: continue
                seen.add(mid)
                msg = service.users().messages().get(
                    userId="me", id=mid, format="metadata",
                    metadataHeaders=["From", "Subject", "Date"]
                ).execute()
                hdrs = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
                messages.append({
                    "id":       mid,
                    "subject":  hdrs.get("Subject", ""),
                    "sender":   hdrs.get("From", ""),
                    "date_raw": hdrs.get("Date", ""),
                    "snippet":  msg.get("snippet", ""),
                })
        except Exception as e:
            print(f"  [WARN] Query failed: {e}")

    return messages

# ── Data helpers ──────────────────────────────────────────────────────────────
def load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_data(records):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

def messages_to_records(messages):
    records = []
    for msg in messages:
        records.append({
            "id":      msg["id"],
            "company": extract_company(msg["subject"], msg["snippet"], msg["sender"]),
            "role":    extract_role(msg["subject"], msg["snippet"]),
            "date":    parse_date(msg["date_raw"]),
            "status":  classify_email(msg["subject"], msg["snippet"], msg["sender"]),
            "source":  detect_source(msg["sender"]),
            "snippet": msg["snippet"][:200],
            "link":    f"https://mail.google.com/mail/u/0/#inbox/{msg['id']}",
        })
    return records

def merge(existing, new_records):
    ids = {r["id"] for r in existing}
    added = [r for r in new_records if r["id"] not in ids]
    return existing + added, len(added)

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Fetch Gmail job emails and update tracker")
    parser.add_argument("--days",    type=int, default=30,   help="Search last N days (default: 30)")
    parser.add_argument("--dry-run", action="store_true",    help="Preview without saving")
    args = parser.parse_args()

    print("\nJob Application Dashboard - Gmail Sync")
    print("=" * 50)

    existing = load_data()
    print(f"[INFO] {len(existing)} existing records loaded")

    print(f"\n[FETCH] Searching last {args.days} days of Gmail...")
    messages = fetch_gmail(days=args.days)
    print(f"  Found {len(messages)} job-related emails")

    if not messages:
        print("[WARN] No emails fetched. Check credentials.json or broaden search.")
        return

    new_records = messages_to_records(messages)
    merged, added = merge(existing, new_records)
    print(f"\n[DONE] {added} new | {len(existing)} existing -> {len(merged)} total")

    if args.dry_run:
        print("\n[DRY-RUN] Would add:")
        ids = {r["id"] for r in existing}
        for r in new_records:
            if r["id"] not in ids:
                print(f"  + {r['company']} | {r['role'][:45]} | {r['status']} | {r['date']}")
        return

    save_data(merged)
    print(f"[SAVE] Written to {DATA_FILE}")
    print("[OK]   Streamlit will auto-refresh if running.")

if __name__ == "__main__":
    main()
