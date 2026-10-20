import html
import math
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from config.settings import DISABLED_SOURCES
from matching.extraction import CATEGORIES, parse_date
from matching.language_detection import ENGLISH, LANGUAGES, NO_GERMAN
from services.exports import csv_bytes, excel_bytes, jobs_frame
from services.filters import default_filters
from services.llm import advice_payload, request_advice

TYPES = ["Werkstudent / Working Student", "Internship / Praktikum", "Research Assistant / HiWi"]
AGES = {"All available": None, "Last 24 hours": 1, "Last 3 days": 3, "Last 7 days": 7, "Last 14 days": 14, "Last 30 days": 30}


def styling():
    st.markdown("""<style>
    .block-container {max-width:1280px;padding-top:2rem;padding-bottom:3rem}
    h1 {letter-spacing:-.045em;font-weight:750!important}
    h2,h3 {letter-spacing:-.025em}
    [data-testid="stMetric"] {background:var(--secondary-background-color);padding:1rem;border-radius:14px}
    [data-testid="stVerticalBlockBorderWrapper"] {border-radius:16px}
    .hero {padding:1.8rem 2rem;border-radius:20px;background:linear-gradient(115deg,#192b58,#5445ac);color:white;margin-bottom:1.4rem}
    .hero h1 {color:white;margin:0;font-size:2.5rem}
    .hero p {color:#e0e7ff;margin:.65rem 0 0;max-width:700px}
    .eyebrow {font-size:.76rem;font-weight:700;letter-spacing:.16em;text-transform:uppercase;color:#c9d5ff}
    .company {font-size:.8rem;font-weight:650;letter-spacing:.05em;text-transform:uppercase;color:#7976c9}
    .pill {display:inline-block;padding:.2rem .6rem;margin:.15rem .25rem .15rem 0;border-radius:20px;background:#eae8ff;color:#443f93;font-size:.78rem}
    .score {font-size:1.8rem;font-weight:750;color:#635bff;text-align:right}
    .subtle {font-size:.8rem;opacity:.75}
    @media(max-width:640px) {.hero{padding:1.3rem}.hero h1{font-size:2rem}.block-container{padding:1rem}}
    </style>""", unsafe_allow_html=True)


def summary(jobs, storage):
    now = datetime.now(timezone.utc)
    recent = sum(bool((dt := parse_date(j.get("first_seen"))) and 0 <= (now-dt).days < 7) for j in jobs)
    submitted_ids = {
        a["job_id"] for a in storage.applications(history=True)
        if a.get("applied_date") or a["status"] in {"Applied", "Assessment", "Interview", "Offer"}
    }
    applied = len(submitted_ids)
    values = [
        ("Jobs discovered", len(jobs)), ("English confirmed", sum(j["language"] == ENGLISH for j in jobs)),
        ("Discovered this week", recent), ("High matches · 70+", sum(j["match"]["score"] >= 70 for j in jobs)),
        ("Saved jobs", sum(j["saved"] for j in jobs)), ("Applications submitted", applied),
    ]
    for offset in (0, 3):
        for col, (label, value) in zip(st.columns(3), values[offset:offset+3]):
            col.metric(label, value)
    st.caption("Summary covers the entire stored collection. A match score is a heuristic, not a hiring probability.")


def sidebar_filters(jobs, storage):
    preferences = storage.get_setting("search_preferences", default_filters())
    with st.sidebar:
        st.subheader("Refine your search")
        query = st.text_input("Keywords", placeholder="Python, RAG, software…")
        category = st.selectbox("Job category", ["All categories"] + list(CATEGORIES))
        types = st.multiselect("Job type", TYPES, default=TYPES)
        cities = sorted({c for j in jobs for c in j.get("cities", [])})
        city = st.selectbox("City", ["All Germany"] + cities)
        workplace = st.selectbox("Work arrangement", ["Any", "Remote", "Hybrid", "On-site", "Unknown"])
        languages = st.multiselect("Language requirements", LANGUAGES, default=preferences.get("languages", [ENGLISH, NO_GERMAN]))
        st.caption("Missing German wording does not confirm English sufficiency.")
        age = st.selectbox("Posting age", list(AGES))
        if AGES[age]:
            st.caption("Jobs with unknown posting dates are excluded.")
        min_score = st.slider("Minimum relevance score", 0, 100, int(preferences.get("min_score", 0)))
        paid = st.checkbox("Confirmed paid opportunities only", value=preferences.get("paid_only", False))
        st.caption("Internships with unknown pay remain visible unless this is checked.")
        with st.expander("More filters"):
            salary_only = st.checkbox("Published salary only")
            salary_query = st.text_input("Salary contains", placeholder="EUR, hour, month…")
            skills = st.multiselect("Required skills in advert (all)", sorted({s for j in jobs for s in j["skills"]}))
            companies = st.multiselect("Companies", sorted({j["company"] for j in jobs}))
            sources = st.multiselect("Sources", sorted({x["source"] for j in jobs for x in j["source_links"]}))
            authorization = st.selectbox("Work authorization", ["Any", "Explicit wording present", "Unknown / not stated"])
            authorization_query = st.text_input("Authorization wording contains", placeholder="sponsorship, permit…")
            expired = st.checkbox("Include potentially expired jobs", value=preferences.get("include_expired", False))
    return dict(query=query, category=category, types=types, city=city, workplace=workplace,
                languages=languages, days=AGES[age], min_score=min_score, paid_only=paid,
                salary_only=salary_only, salary_query=salary_query, skills=skills, companies=companies,
                sources=sources, authorization=authorization, authorization_query=authorization_query, include_expired=expired)


def export_buttons(jobs, prefix):
    frame = jobs_frame(jobs)
    left, right, _ = st.columns([1, 1, 3])
    left.download_button("↓ Download CSV", csv_bytes(frame), f"careerscout-{prefix}.csv", "text/csv", key=f"csv-{prefix}")
    right.download_button("↓ Download Excel", excel_bytes(frame), f"careerscout-{prefix}.xlsx",
                          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"xlsx-{prefix}")


def details(job, profile):
    match = job["match"]
    st.markdown("**How this score was calculated**")
    st.dataframe(pd.DataFrame([
        {"Component": key.title(), "Score / 100": score, "Weight %": profile.weights[key],
         "Contribution": round(score * profile.weights[key] / 100, 2)}
        for key, score in match["components"].items()
    ]), hide_index=True, width="stretch")
    left, right = st.columns(2)
    with left:
        st.markdown("**Why it fits**")
        for reason in match["reasons"]:
            st.write("• " + reason)
        st.markdown("**Emphasize in your CV**")
        st.write(", ".join(match["advice"]["emphasize"]) or "No recognized overlap yet.")
        for project in match["advice"]["projects"]:
            st.write(project)
    with right:
        st.markdown("**Potential obstacles**")
        for obstacle in match["obstacles"]:
            st.write("• " + obstacle)
        st.markdown("**Learning & interview preparation**")
        st.write("Explore: " + (", ".join(match["advice"]["learn"]) or "No additional recognized skills detected."))
        st.write("Prepare examples for: " + (", ".join(match["advice"]["interview"]) or "the role's responsibilities."))
    st.markdown("**Evidence from the advert**")
    for key, snippets in match["evidence"].items():
        st.caption(key.title())
        if snippets:
            for snippet in snippets:
                st.text(snippet)
        else:
            st.write("Unknown / no explicit evidence found.")
    st.markdown("**Work authorization wording**")
    st.text("\n".join(job.get("authorization", [])) or "Unknown / not stated. No eligibility inference is made.")
    st.markdown("**Original listing text**")
    st.text(job["description"])
    st.caption(f"First discovered: {job['first_seen']} · Last seen in API: {job['last_verified']}")
    for link in job["source_links"]:
        st.link_button("Original source · " + link["source"], link["url"])
    st.divider()
    st.markdown("**Optional AI-assisted advice**")
    st.caption("Local scoring is already complete. The optional request uses your own API key and may incur a provider charge.")
    payload = advice_payload(job, profile)
    if st.checkbox("Preview the data for AI advice", key=f"preview-{job['id']}"):
        st.json(payload)
        consent = st.checkbox("I authorize sending this displayed profile and listing to OpenAI for this request.", key=f"consent-{job['id']}")
        if st.button("Generate AI advice", key=f"llm-{job['id']}", disabled=not consent):
            try:
                with st.spinner("Preparing advice…"):
                    advice = request_advice(payload, consent=consent)
                st.text(advice)
                st.caption("AI-generated advice may be inaccurate. Check against the original advert.")
            except Exception as exc:
                st.error(str(exc) if isinstance(exc, ValueError) else "AI request failed; local matching remains available.")


def job_card(job, storage, profile, prefix):
    match = job["match"]
    with st.container(border=True):
        left, right = st.columns([5, 1])
        with left:
            st.markdown(f'<div class="company">{html.escape(job["company"])}</div>', unsafe_allow_html=True)
            st.subheader(job["title"])
            st.caption(f"{job['location']} · {job['workplace']} · {job['job_type']}")
        right.markdown(f'<div class="score">{match["score"]:.0f}<div class="subtle">/ 100 match</div></div>', unsafe_allow_html=True)
        st.markdown("".join(f'<span class="pill">{html.escape(s)}</span>' for s in job["skills"][:9]), unsafe_allow_html=True)
        st.write(job["language"])
        date = parse_date(job.get("posted_at"))
        when = f"{job.get('date_label', 'Posted')}: {date:%d %b %Y}" if date else f"Discovered: {job['first_seen'][:10]} · posting date unknown"
        st.caption(f"{job.get('salary') or 'Salary not published'} · Pay: {job['paid']} · {when} · {job['source']}")
        if job["potentially_expired"]:
            st.warning("Potentially expired or stale. Check the original page before applying.")
        a, b, c = st.columns(3)
        a.link_button("Apply ↗", job["apply_url"], width="stretch", type="primary")
        if b.button("✓ Saved" if job["saved"] else "Save job", key=f"save-{prefix}-{job['id']}", width="stretch"):
            storage.save_job(job["id"], not job["saved"])
            st.rerun()
        if c.button("Track application", key=f"track-{prefix}-{job['id']}", width="stretch"):
            if not job["application_status"]:
                storage.update_application(job["id"], "Interested")
            st.toast("Added to Application Tracker.")
        with st.expander("View details & match evidence"):
            details(job, profile)


def job_list(jobs, storage, profile, prefix):
    if not jobs:
        st.info("No listings match these filters yet. Try All available, include Unknown language, or lower the score. Check source health below and use Refresh Jobs. No sample jobs are substituted.")
        return
    export_buttons(jobs, prefix)
    count = st.selectbox("Results per page", [10, 20, 50], key=f"size-{prefix}")
    pages = max(1, math.ceil(len(jobs) / count))
    page_key = f"page-{prefix}"
    if st.session_state.get(page_key, 1) > pages:
        st.session_state[page_key] = 1
    page = st.number_input("Page", 1, pages, key=page_key)
    st.caption(f"{len(jobs)} opportunities · page {page} of {pages}")
    for job in jobs[(page-1)*count:page*count]:
        job_card(job, storage, profile, prefix)


def source_health(storage):
    with st.expander("Source health & coverage"):
        runs = storage.runs()
        if runs:
            st.dataframe(pd.DataFrame(runs).drop(columns=["id"]), hide_index=True, width="stretch")
        else:
            st.write("No refresh has run yet. Click Find Jobs to query the configured public APIs.")
        st.caption("Success means the API was reached. Zero results can mean no current German student roles in the covered boards.")
        for name, reason in DISABLED_SOURCES.items():
            st.write(f"**{name}:** {reason}")
        st.markdown("[Arbeitnow API attribution](https://www.arbeitnow.com/blog/job-board-api) · More access notes in docs/SOURCES.md")
