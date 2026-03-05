---
name: job-tracker-streamlit
description: >
  Fetches job-related emails from Gmail, updates the local job tracker JSON data file,
  and launches (or refreshes) a Streamlit web app at http://localhost:8501.
  Use this skill whenever the user says things like: "update my job tracker",
  "sync my job emails", "refresh the tracker", "check my job emails",
  "launch the job tracker", "open the job tracker", "did I get any new job emails",
  "show me my applications", or "what's new in my job search".
  Also trigger when the user asks about their application pipeline or wants to
  see a summary of their job search activity.
compatibility:
  required_mcp: Gmail (https://gmail.mcp.claude.com/mcp)
  required_tools: Windows-MCP (shell access to user's Windows PC)
  files:
    - <PROJECT_DIR>\job_tracker_fetch.py
    - <PROJECT_DIR>\job_tracker_app.py
    - <PROJECT_DIR>\job_tracker_data.json
  python: python  # or <PYTHON_PATH>
  streamlit_port: 8501
---

# Job Tracker Streamlit Skill

Fetches new job emails from Gmail via MCP, merges them into the persistent JSON
data store, and ensures the Streamlit dashboard is running and open in the browser.
Follow these steps precisely.

---

## Setup note

In the steps below, replace `<PROJECT_DIR>` with the folder where you saved this project (for example, `C:\\Users\\<YOU>\\Downloads\\job-application-dashboard`).

---

## Step 1 — Fetch New Job Emails from Gmail

Use Gmail MCP to search for job-related emails. Run these searches and collect ALL results:

**Search 1 — Application confirmations (last 30 days):**
```
subject:("thank you for applying" OR "application received" OR "application submitted" OR "officially applied") newer_than:30d
```

**Search 2 — Rejections:**
```
subject:("not selected" OR "not moving forward" OR "unfortunately" OR "other candidates" OR "not be proceeding") newer_than:30d
```

**Search 3 — Viewed notifications:**
```
("application was viewed" OR "viewed your application") newer_than:30d
```

**Search 4 — LinkedIn applied:**
```
from:(jobs-noreply@linkedin.com OR jobalerts-noreply@linkedin.com) newer_than:30d
```

**Search 5 — Interview / next steps:**
```
subject:("next steps" OR "interview" OR "time sensitive" OR "schedule") newer_than:30d
```

**Search 6 — Action required / platform follow-ups:**
```
("action required" OR "still looking for a job" OR "confirm your interest") newer_than:30d
```

For each result, retrieve via `gmail_read_message`:
- `id` (message ID)
- `subject`
- `from` header (sender)
- `date` header
- `snippet`

---

## Step 2 — Load Existing Data

Read the current data file using Windows-MCP Shell:

```powershell
Get-Content "<PROJECT_DIR>\job_tracker_data.json" -Raw
```

Parse the JSON and extract all existing `id` values into a set for deduplication.

---

## Step 3 — Classify Each New Email

For every fetched email whose `id` is NOT already in the existing data, classify it:

### Status Classification Rules (apply in this order)

| Status | Match signals in subject + snippet |
|---|---|
| **Rejected** | "not selected", "not moving forward", "decided not to proceed", "will not be moving forward", "unfortunately", "other candidates", "not a match", "position has been filled" |
| **Action Required** | "action required", "still looking for a job", "check if you're still", "response required", "please respond", "confirm your interest" |
| **Interview/Next Steps** | "interview", "next steps", "move forward with you", "schedule a call", "time sensitive", "phone screen", "video call", "assessment" |
| **Viewed** | "viewed your application", "application was viewed" |
| **Confirmed** | "thank you for applying", "application has been received", "officially applied", "received your application", "thank you for your interest" |
| **Applied** | "application was sent", "track your application", "your application to [role] at [company]" |

### Source Detection (from sender domain)

| Domain contains | Source label |
|---|---|
| linkedin | LinkedIn |
| workday / myworkdayjobs | Workday |
| greenhouse | Greenhouse |
| lever | Lever |
| ashby | Ashby |
| ycombinator | YC |
| lensa | Lensa |
| mercor | Mercor |
| teamtailor | TeamTailor |
| clearcompany | ClearCompany |
| anything else | Direct |

### Company Name Extraction (best effort)

Try these patterns in order:
1. "application to [ROLE] at [COMPANY]" → extract COMPANY
2. "application was sent to [COMPANY]" → extract COMPANY
3. Sender display name (e.g. "Roche Careers" → "Roche")
4. Sender domain second-level (e.g. `@novartis.com` → "Novartis")
5. Fallback: "(Unknown)"

### Role Extraction

1. "application to [ROLE] at [Company]" → extract ROLE
2. "Track Your Application: [Company] [ROLE]" → extract ROLE
3. Fallback: "(Not specified)"

### Date Parsing

Parse the `Date` email header to `YYYY-MM-DD` format.

---

## Step 4 — Build New Records

For each new classified email, create a JSON record:

```json
{
  "id":      "<gmail_message_id>",
  "company": "<extracted company name>",
  "role":    "<extracted role>",
  "date":    "YYYY-MM-DD",
  "status":  "<one of the 6 status values>",
  "source":  "<source label>",
  "snippet": "<first 200 chars of snippet>",
  "link":    "https://mail.google.com/mail/u/0/#inbox/<message_id>"
}
```

---

## Step 5 — Merge and Save

Merge new records into the existing data (existing records are NEVER modified).
Write the merged array back to the JSON file using Windows-MCP Shell:

```powershell
# Build the merged JSON in Python and save
$mergedJson = '<JSON string of merged array>'
$mergedJson | Out-File -FilePath "<PROJECT_DIR>\job_tracker_data.json" -Encoding utf8
```

Or use Python directly for reliable UTF-8 handling:

```powershell
$p = Start-Process "C:\anaconda3\python.exe" -ArgumentList @(
  "-c",
  "import json; existing=json.load(open(r'<PROJECT_DIR>\job_tracker_data.json',encoding='utf-8')); ids={r['id'] for r in existing}; new=[r for r in NEW_RECORDS if r['id'] not in ids]; existing.extend(new); json.dump(existing,open(r'<PROJECT_DIR>\job_tracker_data.json','w',encoding='utf-8'),indent=2); print(f'Added {len(new)} records')"
) -PassThru -Wait -NoNewWindow -RedirectStandardOutput "<PROJECT_DIR>\tracker_out.txt"
Get-Content "<PROJECT_DIR>\tracker_out.txt"
```

Where `NEW_RECORDS` is substituted with the actual JSON array of new records.

**Preferred approach**: Write the new records to a temp file, then call the fetch script:

```powershell
# Write new records to temp JSON
$newRecords = '<JSON array>'
$newRecords | Out-File "<PROJECT_DIR>\new_records_temp.json" -Encoding utf8

# Merge via Python one-liner
$script = @"
import json
existing = json.load(open(r'<PROJECT_DIR>\job_tracker_data.json', encoding='utf-8'))
new_recs = json.load(open(r'<PROJECT_DIR>\new_records_temp.json', encoding='utf-8'))
ids = {r['id'] for r in existing}
added = [r for r in new_recs if r['id'] not in ids]
existing.extend(added)
json.dump(existing, open(r'<PROJECT_DIR>\job_tracker_data.json', 'w', encoding='utf-8'), indent=2)
print(f'Added {len(added)} new records. Total: {len(existing)}')
"@
$p = Start-Process "C:\anaconda3\python.exe" -ArgumentList "-c", $script -PassThru -Wait -NoNewWindow -RedirectStandardOutput "<PROJECT_DIR>\tracker_out.txt" -RedirectStandardError "<PROJECT_DIR>\tracker_err.txt"
Get-Content "<PROJECT_DIR>\tracker_out.txt"
Get-Content "<PROJECT_DIR>\tracker_err.txt"
```

---

## Step 6 — Launch or Refresh Streamlit

Check if Streamlit is already running on port 8501, then start or refresh:

```powershell
$running = netstat -ano | findstr :8501
if ($running) {
    Write-Output "Streamlit already running — data file updated, app will auto-refresh"
} else {
    Start-Process "C:\anaconda3\python.exe" -ArgumentList "-m streamlit run `"<PROJECT_DIR>\job_tracker_app.py`" --server.port 8501" -WindowStyle Normal
    Start-Sleep 4
    Start-Process "http://localhost:8501"
    Write-Output "Streamlit launched at http://localhost:8501"
}
```

---

## Step 7 — Report to User

After completing all steps, give a concise summary:

```
Job tracker updated.

  New emails found:   [N]
  New records added:  [N]  (skipped [M] duplicates)
  Total applications: [N]

  Breakdown of new:
    Confirmed:           [N]
    Rejected:            [N]
    Viewed:              [N]
    Interview/Next Steps:[N]
    Action Required:     [N]
    Applied:             [N]

  Streamlit: http://localhost:8501  [running / just launched]
```

If any Action Required or Interview/Next Steps emails were found, call them out explicitly:
> "ACTION NEEDED: [Company] sent a follow-up on [date] — [snippet summary]"

---

## Edge Cases

- **No new emails**: Report "No new job emails found in the last 30 days. Tracker is up to date." and ensure Streamlit is running.
- **Gmail MCP unavailable**: Tell the user to reconnect Gmail via Claude integrations settings.
- **Windows-MCP unavailable**: Tell the user the local Streamlit app requires the Windows MCP extension to be running.
- **JSON write fails**: Show the error and suggest the user manually run `job_tracker_fetch.py`.
- **Streamlit port in use by another app**: Try port 8502 and report the alternate URL.

---

## Quick Reference — File Locations

| File | Path |
|---|---|
| Data store | `<PROJECT_DIR>\job_tracker_data.json` |
| Streamlit app | `<PROJECT_DIR>\job_tracker_app.py` |
| Gmail fetcher script | `<PROJECT_DIR>\job_tracker_fetch.py` |
| One-click launcher | `<PROJECT_DIR>\launch_dashboard.bat` |
| Python | `C:\anaconda3\python.exe` |
| Streamlit URL | `http://localhost:8501` |
