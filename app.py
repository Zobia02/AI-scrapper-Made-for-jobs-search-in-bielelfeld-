"""CareerScout Germany: run `python -m streamlit run app.py`."""
import hmac
import json

import streamlit as st

from config.settings import database_url, setting
from database.storage import Storage
from matching.profile import Profile
from matching.scorer import score_job
from services.filters import filter_jobs
from services.refresh import refresh
from ui import pages
from ui.components import sidebar_filters, styling, summary

st.set_page_config(page_title="CareerScout Germany", page_icon="✦", layout="wide")
styling()

# Optional single-user gate. For internet hosting use platform access controls as well.
password = setting("APP_PASSWORD")
if password and not st.session_state.get("authenticated"):
    st.title("CareerScout Germany")
    with st.form("login"):
        supplied = st.text_input("Workspace password", type="password")
        if st.form_submit_button("Open workspace"):
            if hmac.compare_digest(supplied.encode(), password.encode()):
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Incorrect password.")
    st.stop()


@st.cache_resource
def get_storage(url):
    return Storage(url)


@st.cache_data(ttl=900, max_entries=8, show_spinner=False)
def score_collection(serialized_jobs, serialized_profile):
    profile = Profile.model_validate_json(serialized_profile)
    return [{**j, "match": score_job(j, profile)} for j in json.loads(serialized_jobs)]


try:
    storage = get_storage(database_url())
    mode = storage.get_setting("profile_mode", {"value": "My default profile"})["value"]
    key = {"My uploaded CV": "cv_profile", "My manually edited profile": "manual_profile"}.get(mode)
    profile = Profile(**storage.get_setting(key)) if key and storage.get_setting(key) else Profile()
    raw_jobs = storage.jobs()
except Exception:
    st.error("Could not open the database. Check DATABASE_URL, database availability and write permissions. Secrets are not shown here.")
    st.stop()

with st.sidebar:
    st.title("✦ CareerScout")
    st.caption("GERMANY · YOUR STUDENT CAREER")
    navigation = st.radio("Workspace", ["Discover Jobs", "Best Matches", "Saved Jobs", "Application Tracker", "Analytics", "Settings / My Profile"], label_visibility="collapsed")
    st.divider()
    if st.button("Find Jobs" if not raw_jobs else "Refresh Jobs", type="primary", width="stretch"):
        progress = st.progress(0.0, text="Connecting to public job APIs…")
        try:
            result = refresh(storage, lambda value, message: progress.progress(value, text=message))
            st.session_state["last_refresh_report"] = result
            score_collection.clear()
            st.rerun()
        except RuntimeError as exc:
            st.warning(str(exc))
        except Exception:
            st.error("Refresh could not finish. Check database connectivity and source health.")
    runs = storage.runs()
    successful = next((r for r in runs if r["status"] == "success"), None)
    st.caption(f"Last successful source refresh: {successful['started_at']:%d %b %Y %H:%M} UTC" if successful else "No successful refresh yet")
    st.caption(f"Profile: {profile.name} · German {profile.german}")

jobs = score_collection(json.dumps(raw_jobs), profile.model_dump_json())
st.markdown("""<div class="hero"><div class="eyebrow">Built for your next step</div>
<h1>CareerScout Germany</h1><p>Find your place in AI & software. Discover student roles, understand the requirements, and turn promising matches into applications.</p></div>""", unsafe_allow_html=True)
if "last_refresh_report" in st.session_state:
    report = st.session_state.pop("last_refresh_report")
    failures = sum(r["status"] == "error" for r in report)
    st.info(f"Refresh finished: {sum(r['added'] for r in report)} new jobs, {failures} source errors. Review Source health for details.")
summary(jobs, storage)
st.divider()
if navigation in {"Discover Jobs", "Best Matches"}:
    filters = sidebar_filters(jobs, storage)
    visible = filter_jobs(jobs, filters)
    pages.discover(visible, storage, profile, best=navigation == "Best Matches")
elif navigation == "Saved Jobs":
    pages.saved(jobs, storage, profile)
elif navigation == "Application Tracker":
    pages.applications(jobs, storage)
elif navigation == "Analytics":
    pages.analytics(jobs, storage)
else:
    pages.settings(storage, profile)
st.caption("CareerScout Germany · Original listings remain the authority. Verify availability, pay, language and eligibility before applying.")
