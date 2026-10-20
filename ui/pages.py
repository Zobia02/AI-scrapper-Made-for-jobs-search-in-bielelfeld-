from datetime import date, datetime, timezone

import pandas as pd
import plotly.express as px
import streamlit as st

from config.settings import DEFAULT_SOURCES
from database.storage import STATUSES
from matching.extraction import parse_date
from matching.language_detection import ENGLISH, LANGUAGES, NO_GERMAN
from matching.profile import Profile, WEIGHTS
from services.cv import extract_cv, parsed_skills
from services.exports import applications_frame, csv_bytes, excel_bytes
from sources.base import board_token
from ui.components import job_list, source_health


def discover(jobs, storage, profile, best=False):
    st.header("Best matches" if best else "Your next chapter starts here")
    st.write("Ranked by your skills, role interests and language needs." if best else "Real student opportunities across Germany, with the evidence you need to decide.")
    job_list(jobs, storage, profile, "best" if best else "discover")
    source_health(storage)


def saved(jobs, storage, profile):
    st.header("Your shortlist")
    saved_jobs = [j for j in jobs if j["saved"]]
    collections = sorted({j["collection"] for j in saved_jobs})
    collection = st.selectbox("Collection", ["All collections"] + collections)
    if saved_jobs:
        with st.expander("Organize a saved job"):
            chosen = st.selectbox("Job to organize", saved_jobs, format_func=lambda j: f"{j['company']} · {j['title']}")
            new_collection = st.text_input("Collection name", value=chosen["collection"])
            if st.button("Move to collection"):
                storage.save_job(chosen["id"], True, new_collection or "Shortlist")
                st.rerun()
    visible = [j for j in saved_jobs if collection == "All collections" or j["collection"] == collection]
    job_list(visible, storage, profile, "saved")


def applications(jobs, storage):
    st.header("Application tracker")
    st.write("Keep your next step in view. Every saved edit is retained in your history.")
    if not jobs:
        st.info("Find jobs first, then select Track application on a listing.")
        return
    tracked = storage.applications()
    with st.expander("Add a job to your tracker"):
        job = st.selectbox("Choose a job", jobs, format_func=lambda j: f"{j['company']} · {j['title']}")
        if st.button("Add as interested"):
            if any(a["job_id"] == job["id"] for a in tracked):
                st.info("This job is already tracked.")
            else:
                storage.update_application(job["id"], "Interested")
                st.rerun()
    if not tracked:
        st.info("Your tracker is empty. Add a listing above or use Track application on a job card.")
        return
    frame = applications_frame(tracked, jobs)
    st.dataframe(frame[["company", "title", "status", "applied_date", "followup_date"]], hide_index=True, width="stretch")
    lookup = {j["id"]: j for j in jobs}
    selected = st.selectbox("Update application", tracked,
                            format_func=lambda a: f"{lookup[a['job_id']]['company']} · {lookup[a['job_id']]['title']}")
    with st.form(f"application-{selected['job_id']}"):
        status = st.selectbox("Status", STATUSES, index=STATUSES.index(selected["status"]))
        left, right = st.columns(2)
        applied = left.date_input("Application date", value=date.fromisoformat(selected["applied_date"]) if selected["applied_date"] else None)
        followup = right.date_input("Follow-up date", value=date.fromisoformat(selected["followup_date"]) if selected["followup_date"] else None)
        notes = st.text_area("Notes", selected["notes"], height=160)
        link = st.text_input("Submitted application / confirmation URL", selected["submitted_url"])
        if st.form_submit_button("Save application", type="primary"):
            try:
                storage.update_application(selected["job_id"], status, notes,
                                           applied.isoformat() if applied else None,
                                           followup.isoformat() if followup else None, link)
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
    overdue = [a for a in tracked if a["followup_date"] and a["followup_date"] <= date.today().isoformat() and a["status"] not in {"Offer", "Rejected"}]
    if overdue:
        st.info(f"{len(overdue)} application(s) have a follow-up due.")
    history = applications_frame(storage.applications(history=True), jobs)
    st.download_button("Export application history CSV", csv_bytes(history), "application-history.csv", "text/csv")
    st.download_button("Export application history Excel", excel_bytes(history), "application-history.xlsx")
    with st.expander("Full change history"):
        st.dataframe(history, hide_index=True, width="stretch")


def analytics(jobs, storage):
    st.header("Your search, at a glance")
    if not jobs:
        st.info("Refresh jobs to build your analytics from real listings.")
        return
    st.caption("All stored jobs; includes potentially expired listings. City and skill charts can count a job more than once.")
    palette = ["#635BFF", "#2697BB", "#B39AF4", "#9CDAD5", "#D7C4FA"]
    def bar(values, title, column):
        counts = pd.Series(values, dtype=str).value_counts().head(15).rename_axis(column).reset_index(name="Jobs")
        fig = px.bar(counts, x="Jobs", y=column, orientation="h", title=title, color_discrete_sequence=palette)
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, margin=dict(l=0, r=15, t=45, b=0))
        st.plotly_chart(fig, width="stretch")
    a, b = st.columns(2)
    with a:
        bar([c for j in jobs for c in j.get("cities", [])] or ["Unknown"], "Where the opportunities are", "City")
        bar([s for j in jobs for s in j["skills"]], "Most advertised skills", "Skill")
    with b:
        bar([j["company"] for j in jobs], "Companies hiring students", "Company")
        languages = pd.Series([j["language"] for j in jobs]).value_counts().rename_axis("Language").reset_index(name="Jobs")
        st.plotly_chart(px.pie(languages, names="Language", values="Jobs", hole=.58,
                               title="Language evidence", color_discrete_sequence=palette), width="stretch")
    now = datetime.now(timezone.utc)
    ages = []
    for j in jobs:
        dt = parse_date(j.get("posted_at"))
        days = (now-dt).days if dt else None
        ages.append("Unknown" if days is None or days < 0 else "0–7 days" if days < 7 else "7–30 days" if days <= 30 else "Over 30 days")
    a, b = st.columns(2)
    with a:
        bar(ages, "Posting age", "Age")
    with b:
        apps = storage.applications()
        if apps:
            bar([a["status"] for a in apps], "Application progress", "Status")
        else:
            st.info("Track applications to see progress here.")


def settings(storage, current):
    st.header("Make CareerScout yours")
    st.caption("Profiles and preferences belong to this single-user database. Raw uploaded files are processed in memory and are not saved.")
    modes = ["My default profile", "My uploaded CV", "My manually edited profile"]
    mode = st.selectbox("Matching profile", modes, index=modes.index(storage.get_setting("profile_mode", {"value": modes[0]})["value"]))
    if st.button("Use this profile"):
        key = {"My uploaded CV": "cv_profile", "My manually edited profile": "manual_profile"}.get(mode)
        if key and not storage.get_setting(key):
            st.error("Save that profile below first.")
        else:
            storage.set_setting("profile_mode", {"value": mode})
            st.rerun()
    with st.expander("Upload & review a CV", expanded=False):
        st.write("PDF and DOCX are parsed on the app server. When running locally, that is your computer. No external AI receives the file.")
        uploaded = st.file_uploader("Choose your CV", type=["pdf", "docx"])
        if uploaded and st.button("Extract CV text"):
            try:
                st.session_state["cv_text"] = extract_cv(uploaded.getvalue(), uploaded.name)
            except Exception as exc:
                st.error(str(exc) if isinstance(exc, ValueError) else "Could not parse this file. Re-export it as a text PDF or DOCX.")
        cv_text = st.text_area("Preview / correct extracted text (or paste text)", key="cv_text", height=220)
        st.caption("The skill parser does not infer degrees, experience or language levels. Review and enter those fields below.")
        if st.button("Build editable CV profile"):
            st.session_state["cv_draft"] = Profile(
                skills=parsed_skills(cv_text), education="", experience="", english="Unknown", german="Unknown", student=False,
                roles=current.roles, locations=current.locations,
            ).model_dump()
        if st.session_state.get("cv_draft"):
            profile_form(storage, Profile(**st.session_state["cv_draft"]), "cv_profile")
    with st.expander("Edit your profile & matching weights", expanded=True):
        existing = storage.get_setting("manual_profile")
        profile_form(storage, Profile(**existing) if existing else current, "manual_profile")
    with st.expander("Default search preferences"):
        pref = storage.get_setting("search_preferences", {})
        with st.form("preferences"):
            langs = st.multiselect("Default languages", LANGUAGES, default=pref.get("languages", [ENGLISH, NO_GERMAN]))
            paid = st.checkbox("Only confirmed paid by default", value=pref.get("paid_only", False))
            score = st.slider("Default minimum score", 0, 100, int(pref.get("min_score", 0)))
            if st.form_submit_button("Save search preferences"):
                storage.set_setting("search_preferences", {"languages": langs, "paid_only": paid, "min_score": score})
                st.success("Saved. Used when the search widgets are next initialized.")
    with st.expander("Job sources & coverage"):
        config = storage.get_setting("sources", DEFAULT_SOURCES)
        st.write("Enter ATS board names from official career pages. These APIs search configured employers, not every employer in Germany.")
        with st.form("sources"):
            arbeitnow = st.checkbox("Enable Arbeitnow", value=config.get("arbeitnow", True))
            pages = st.number_input("Arbeitnow pages per refresh", 1, 10, int(config.get("arbeitnow_pages", 5)))
            values = {}
            for key, label in [("greenhouse", "Greenhouse"), ("lever", "Lever global"), ("lever_eu", "Lever EU"), ("ashby", "Ashby")]:
                values[key] = st.text_area(f"{label} board names (one per line)", "\n".join(config.get(key, [])))
            if st.form_submit_button("Save sources"):
                try:
                    parsed = {key: list(dict.fromkeys(board_token(x.strip()) for x in text.splitlines() if x.strip())) for key, text in values.items()}
                    if sum(len(v) for v in parsed.values()) > 40:
                        raise ValueError("Use at most 40 boards per refresh.")
                    storage.set_setting("sources", {**parsed, "arbeitnow": arbeitnow, "arbeitnow_pages": pages})
                    st.success("Sources saved. Use Refresh Jobs to query them.")
                except ValueError as exc:
                    st.error(str(exc))
    st.info("SQLite persists on this local computer. Streamlit Community Cloud local disk is temporary. Configure DATABASE_URL for hosted PostgreSQL before relying on cloud saves or scheduled refreshes.")
    st.caption("Notifications are not implemented or sent. Refresh is manual unless you enable the included scheduler.")


def profile_form(storage, profile, key):
    with st.form(key):
        name = st.text_input("Profile name", profile.name)
        skills = st.text_area("Skills (comma separated)", ", ".join(profile.skills))
        roles = st.text_area("Preferred roles (one per line)", "\n".join(profile.roles))
        locations = st.text_area("Preferred locations (comma separated)", ", ".join(profile.locations))
        english = st.text_input("English level", profile.english)
        german_options = ["Unknown", "A1", "A2", "B1", "B2", "C1", "C2", "Native"]
        german = st.selectbox("German level", german_options, index=german_options.index(profile.german) if profile.german in german_options else 0)
        student = st.checkbox("Currently enrolled as a student", profile.student)
        education = st.text_area("Education (reviewed facts)", profile.education)
        experience = st.text_area("Experience & projects (reviewed facts)", profile.experience)
        st.caption("Weights must total 100. Missing evidence receives no positive match, except the explicitly labelled cautious language prior.")
        cols = st.columns(3)
        weights = {k: cols[i % 3].number_input(k.title() + " weight", 0, 100, profile.weights[k], key=f"{key}-{k}")
                   for i, k in enumerate(WEIGHTS)}
        if st.form_submit_button("Save and use this profile", type="primary"):
            try:
                updated = Profile(name=name, skills=[x.strip() for x in skills.split(",") if x.strip()],
                                  roles=[x.strip() for x in roles.splitlines() if x.strip()],
                                  locations=[x.strip() for x in locations.split(",") if x.strip()],
                                  english=english, german=german, student=student, education=education,
                                  experience=experience, weights=weights)
                storage.set_setting(key, updated.model_dump())
                storage.set_setting("profile_mode", {"value": "My uploaded CV" if key == "cv_profile" else "My manually edited profile"})
                st.rerun()
            except ValueError:
                st.error("Check the profile fields and make sure the six weights total 100.")
