# Job Application Dashboard

A Gmail-powered job application tracker that automatically fetches, classifies,
and displays your job search emails in a clean Streamlit dashboard.

Built as a Claude skill — say **"update my job tracker"** or **"launch the job dashboard"**
and Claude will sync your Gmail and open the app automatically.

---

## What It Does

- Searches your Gmail for job-related emails (applications, rejections, interviews, etc.)
- Classifies each email into one of 6 status categories automatically
- Stores everything in a local JSON file — no database needed
- Displays a clean, filterable dashboard at `http://localhost:8501`
- Deduplicates by Gmail message ID — syncing never adds duplicates

### Status Categories

| Status | Meaning |
|--------|---------|
| ⚡ Action Required | Platform follow-ups needing a response |
| 🎯 Interview / Next Steps | Interview invites, scheduling requests |
| ✅ Confirmed | Application acknowledged by employer |
| 👁 Viewed | Employer viewed your LinkedIn application |
| 📨 Applied | Application sent (LinkedIn/Lensa notifications) |
| ❌ Rejected | Rejection emails |

---

## Requirements

- Python 3.9+ (Anaconda recommended)
- Streamlit: `pip install streamlit`
- Gmail API libraries: `pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client`

---

## Quick Start

### Step 1 — Gmail OAuth Setup (one time only)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select an existing one)
3. Go to **APIs & Services** → **Enable APIs** → search for and enable **Gmail API**
4. Go to **APIs & Services** → **Credentials** → **Create Credentials** → **OAuth 2.0 Client ID**
5. Choose **Desktop app** as the application type
6. Download the JSON file → rename it to `credentials.json`
7. Place `credentials.json` in the same folder as these scripts
8. Run `python job_tracker_fetch.py` once → your browser opens → sign in with your Gmail account
9. A `token.json` file is saved automatically — future runs need no browser

### Step 2 — Launch the Dashboard

**Windows (double-click):**
```
launch_dashboard.bat
```

**Any OS (terminal):**
```bash
streamlit run job_tracker_app.py
```

Then open `http://localhost:8501` in your browser.

### Step 3 — Sync Gmail

Click **"Fetch & Update from Gmail"** in the sidebar, or run:
```bash
python job_tracker_fetch.py --days 30
```

---

## Files

| File | Purpose |
|------|---------|
| `job_tracker_app.py` | Streamlit dashboard app |
| `job_tracker_fetch.py` | Gmail fetcher + classifier + JSON merger |
| `job_tracker_data.json` | Your application records (auto-created on first sync) |
| `launch_dashboard.bat` | Windows one-click launcher |
| `SKILL.md` | Claude skill definition — lets Claude run this automatically |
| `credentials.json` | Your Google OAuth credentials **(not included — see setup)** |
| `token.json` | Auto-saved after first login **(not included — auto-generated)** |

---

## Claude Skill Setup

To let Claude launch and update this dashboard automatically:

1. Copy `SKILL.md` to your Claude skills folder:
   - **macOS/Linux:** `/mnt/skills/user/job-application-dashboard/SKILL.md`
   - **Windows:** Ask Claude to install it for you
2. In any Claude session, just say:
   - *"update my job tracker"*
   - *"sync my job emails"*
   - *"launch the job dashboard"*
   - *"did I get any new job emails?"*

---

## Customization

The fetch script and app use relative paths — they work from any folder.
The only thing you may want to customize in `job_tracker_app.py`:

```python
# Line 14 — update this caption with your name/email
st.caption("your-email@gmail.com · [start date] – present")
```

---

## Privacy

- `credentials.json` and `token.json` are in `.gitignore` — never committed
- `job_tracker_data.json` contains your application history — excluded from git by default
  (remove the comment in `.gitignore` if you want to share it)
- The app runs entirely locally — no data is sent anywhere

---

## Troubleshooting

**"Sync failed — UnicodeEncodeError"**
Windows console encoding issue. Run from Anaconda Prompt or add this to the top of `main()`:
```python
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
```
(already included in this version)

**"credentials.json not found"**
Complete the Gmail OAuth setup in Step 1 above.

**"No module named streamlit"**
Run: `pip install streamlit`

**Streamlit won't start on port 8501**
Try: `streamlit run job_tracker_app.py --server.port 8502`
