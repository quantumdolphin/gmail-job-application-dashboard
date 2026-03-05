import streamlit as st
import pandas as pd
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

st.set_page_config(page_title="Job Application Dashboard", layout="wide", page_icon="💼")

DATA_FILE = Path(__file__).parent / "job_tracker_data.json"
FETCH_SCRIPT = Path(__file__).parent / "job_tracker_fetch.py"

# ── Detect Python path ────────────────────────────────────────────────────────
import shutil
PYTHON = shutil.which("python") or shutil.which("python3") or sys.executable

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=10)
def load_data():
    if not DATA_FILE.exists():
        return pd.DataFrame()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        records = json.load(f)
    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    return df

# ── Status config ─────────────────────────────────────────────────────────────
STATUS_EMOJI = {
    "Action Required":      "⚡",
    "Interview/Next Steps": "🎯",
    "Confirmed":            "✅",
    "Viewed":               "👁",
    "Applied":              "📨",
    "Rejected":             "❌",
}
STATUS_COLOR = {
    "Action Required":      "#c2410c",
    "Interview/Next Steps": "#6b21a8",
    "Confirmed":            "#166534",
    "Viewed":               "#92400e",
    "Applied":              "#1d4ed8",
    "Rejected":             "#991b1b",
}

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 💼 Job Application Dashboard")
    st.divider()

    st.markdown("### 🔄 Gmail Sync")
    days = st.slider("Fetch emails from last N days", 7, 90, 30)

    if st.button("🚀 Fetch & Update from Gmail", use_container_width=True, type="primary"):
        with st.spinner("Fetching job emails from Gmail..."):
            try:
                result = subprocess.run(
                    [PYTHON, str(FETCH_SCRIPT), "--days", str(days)],
                    capture_output=True, text=True, timeout=120
                )
                output = result.stdout + result.stderr
                if result.returncode == 0:
                    st.success("Gmail sync complete!")
                    st.text(output[-1000:] if len(output) > 1000 else output)
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Sync failed")
                    st.text(output[-800:])
            except subprocess.TimeoutExpired:
                st.error("Timeout — Gmail fetch took too long")
            except Exception as e:
                st.error(f"Error: {e}")

    if DATA_FILE.exists():
        mtime = datetime.fromtimestamp(DATA_FILE.stat().st_mtime)
        st.caption(f"Last updated: {mtime.strftime('%b %d, %Y %I:%M %p')}")

    st.divider()

    search = st.text_input("🔍 Search company or role", "")

    st.markdown("**Filter by status**")
    all_statuses = ["All"] + list(STATUS_EMOJI.keys())
    status_filter = st.radio("", all_statuses, label_visibility="collapsed")

    st.divider()
    st.markdown("**Sort by**")
    sort_col = st.selectbox("", ["date", "company", "status", "source"], label_visibility="collapsed")
    sort_asc = st.checkbox("Ascending", value=False)

    st.divider()

# ── Load & filter ─────────────────────────────────────────────────────────────
df = load_data()

if df.empty:
    st.warning("No data found. Add a job_tracker_data.json file or run Gmail sync.")
    st.stop()

counts = df["status"].value_counts()
total = len(df)

st.markdown("### 📊 Overview")
cols = st.columns(7)
metrics = [
    ("Total",          total,                                 None),
    ("⚡ Action Req.", counts.get("Action Required", 0),      "#c2410c"),
    ("🎯 Next Steps",  counts.get("Interview/Next Steps", 0), "#6b21a8"),
    ("✅ Confirmed",   counts.get("Confirmed", 0),            "#166534"),
    ("👁 Viewed",      counts.get("Viewed", 0),               "#92400e"),
    ("📨 Applied",     counts.get("Applied", 0),              "#1d4ed8"),
    ("❌ Rejected",    counts.get("Rejected", 0),             "#991b1b"),
]
for col, (label, val, color) in zip(cols, metrics):
    with col:
        st.metric(label, val)

st.divider()

filtered = df.copy()
if search:
    mask = (
        filtered["company"].str.contains(search, case=False, na=False) |
        filtered["role"].str.contains(search, case=False, na=False)
    )
    filtered = filtered[mask]
if status_filter != "All":
    filtered = filtered[filtered["status"] == status_filter]

filtered = filtered.sort_values(sort_col, ascending=sort_asc)

st.markdown(f"### Applications &nbsp; <span style='color:#888;font-size:14px;font-weight:400'>({len(filtered)} shown)</span>", unsafe_allow_html=True)

if filtered.empty:
    st.info("No applications match the current filters.")
else:
    disp = filtered.copy()
    disp["Status"] = disp["status"].apply(lambda s: f"{STATUS_EMOJI.get(s,'')} {s}")
    disp["Date"]   = disp["date"].dt.strftime("%b %d, %Y")
    disp_show = disp[["company","role","Date","Status","source","link"]].rename(columns={
        "company":"Company","role":"Role","source":"Source","link":"Gmail"
    })
    st.dataframe(
        disp_show,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Gmail":   st.column_config.LinkColumn("Gmail", display_text="Open ↗"),
            "Status":  st.column_config.TextColumn("Status", width="medium"),
            "Company": st.column_config.TextColumn("Company", width="medium"),
            "Role":    st.column_config.TextColumn("Role", width="large"),
        },
        height=480,
    )

st.divider()
st.markdown("### 🔎 Application Detail")
company_list = filtered["company"].unique().tolist()
if company_list:
    selected = st.selectbox("Select company", company_list)
    rows = filtered[filtered["company"] == selected]
    for _, row in rows.iterrows():
        color = STATUS_COLOR.get(row["status"], "#888")
        emoji = STATUS_EMOJI.get(row["status"], "")
        with st.expander(f"{emoji} {row['role']} — {row['date'].strftime('%b %d, %Y')}", expanded=True):
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"**Status:** <span style='color:{color}'>{emoji} {row['status']}</span>", unsafe_allow_html=True)
            c2.markdown(f"**Source:** {row['source']}")
            c3.markdown(f"**[Open in Gmail ↗]({row['link']})**")
            st.markdown(f"> {row['snippet']}")

st.divider()
st.caption(f"Job Application Dashboard · {len(df)} total applications · Built with Streamlit + Claude")
