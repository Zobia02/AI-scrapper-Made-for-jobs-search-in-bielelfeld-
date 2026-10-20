from pathlib import Path

from streamlit.testing.v1 import AppTest

from database.storage import Storage
from sources.base import FetchResult

ROOT = Path(__file__).resolve().parents[1]


def test_all_pages_and_save(tmp_path, monkeypatch, job):
    url = f"sqlite:///{(tmp_path / 'ui.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.delenv("APP_PASSWORD", raising=False)
    db = Storage(url)
    db.ingest(job.source, FetchResult(jobs=[job]))
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    assert not app.exception
    save = next(b for b in app.button if b.label == "Save job")
    save.click().run()
    assert not app.exception
    assert db.jobs()[0]["saved"]
    track = next(b for b in app.button if b.label == "Track application")
    track.click().run()
    assert db.applications()[0]["status"] == "Interested"
    for page in ["Best Matches", "Saved Jobs", "Application Tracker", "Analytics", "Settings / My Profile"]:
        app.sidebar.radio[0].set_value(page).run()
        assert not app.exception, f"{page}: {app.exception}"
    app.sidebar.radio[0].set_value("Application Tracker").run()
    next(s for s in app.selectbox if s.label == "Status").set_value("Applied")
    next(t for t in app.text_area if t.label == "Notes").set_value("TEST ONLY: submitted application")
    next(b for b in app.button if b.label == "Save application").click().run()
    assert not app.exception
    assert db.applications()[0]["status"] == "Applied"
    assert len(db.applications(history=True)) == 2
    next(s for s in app.selectbox if s.label == "Status").set_value("Rejected")
    next(b for b in app.button if b.label == "Save application").click().run()
    assert not app.exception
    assert next(m for m in app.metric if m.label == "Applications submitted").value == "1"
    app.sidebar.radio[0].set_value("Settings / My Profile").run()
    next(t for t in app.text_area if t.label == "Skills (comma separated)").set_value("Python, SQL")
    next(b for b in app.button if b.label == "Save and use this profile").click().run()
    assert not app.exception
    assert db.get_setting("manual_profile")["skills"] == ["Python", "SQL"]
    db.engine.dispose()


def test_empty_first_run(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{(tmp_path / 'empty.db').as_posix()}")
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    assert not app.exception
    assert any(b.label == "Find Jobs" for b in app.button)
