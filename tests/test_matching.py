from datetime import datetime, timezone

import pytest

from matching.extraction import germany_location, job_type, skills_in
from matching.language_detection import ENGLISH, NO_GERMAN, OPTIONAL, REQUIRED, UNKNOWN, assess_language
from matching.profile import Profile
from matching.scorer import score_job

BASE = "Build reliable Python software and develop data tools alongside our collaborative engineering team. "


@pytest.mark.parametrize("text,label", [
    ("Fluent English required. German is not required.", ENGLISH),
    ("No German required; fluent English is essential.", ENGLISH),
    ("English is our working language.", ENGLISH),
    ("Fluent English and German required.", REQUIRED),
    ("Sehr gute Deutschkenntnisse und Englischkenntnisse.", REQUIRED),
    ("German B2 required. English is our working language.", REQUIRED),
    ("German is a plus. Fluent English required.", OPTIONAL),
    ("Deutschkenntnisse sind von Vorteil.", OPTIONAL),
    ("German optional. German B2 required for customer communication.", REQUIRED),
    ("International and diverse team.", NO_GERMAN),
    ("German office in Berlin.", UNKNOWN),
    ("Fluent written and spoken Russian and English.", UNKNOWN),
    ("German required, Python optional.", REQUIRED),
])
def test_language_evidence(text, label):
    result = assess_language(BASE + text)
    assert result.label == label
    if label not in {NO_GERMAN, UNKNOWN}:
        assert result.evidence


def test_short_unknown():
    assert assess_language("Python developer").label == UNKNOWN


def test_skills_boundaries():
    assert "Java" not in skills_in("JavaScript development")
    assert set(skills_in("C#, .NET, PyTorch and SQL")) >= {"C#", "ASP.NET Core", "PyTorch", "SQL"}


def test_working_student_not_all_students():
    assert job_type("Senior Engineer mentoring students") is None
    assert job_type("Praktikant Machine Learning") == "Internship / Praktikum"


def test_germany_not_remote_world():
    assert not germany_location("Remote")
    assert not germany_location("Berlin", "US")
    assert germany_location("Köln")
    assert germany_location("Remote, Germany")


def test_score_formula_and_missing_dates(job):
    profile = Profile()
    result = score_job(job.model_dump(mode="json"), profile)
    assert result["components"]["skills"] == 100
    assert result["components"]["recency"] == 0
    assert result["score"] == round(sum(result["components"][k] * profile.weights[k] / 100 for k in profile.weights), 1)
    assert result["components"]["language"] == 100
    assert result["components"]["location"] == 100


def test_language_penalty(job):
    data = job.model_dump(mode="json")
    good = score_job(data, Profile())
    data["language"] = REQUIRED
    bad = score_job(data, Profile())
    assert good["score"] - bad["score"] == 20


def test_profile_change_recalculates(job):
    data = job.model_dump(mode="json")
    assert score_job(data, Profile(skills=[]))["score"] < score_job(data, Profile())["score"]
    assert score_job(data, Profile(english="Unknown"))["components"]["language"] == 0


def test_bad_weights():
    with pytest.raises(ValueError):
        Profile(weights={"skills": 100})


def test_future_is_not_new(job):
    data = job.model_dump(mode="json")
    data["posted_at"] = "2099-01-01T00:00:00Z"
    assert score_job(data, Profile(), datetime(2026, 1, 1, tzinfo=timezone.utc))["components"]["recency"] == 0


def test_pay_does_not_use_funding_or_benefits():
    from matching.extraction import pay_evidence
    assert pay_evidence("We raised EUR 2000000. Annual learning budget EUR 2000.")[0] == "Unknown"
    assert pay_evidence("Salary: EUR 18 per hour")[0] == "Confirmed paid"
    assert pay_evidence("Fulltime 35h/week | €2,108 gross/month") == ("Confirmed paid", "€2,108 gross/month")
    assert pay_evidence("Unpaid internship. Travel budget EUR 500.")[0] == "Unpaid"


def test_inline_html_language():
    from matching.extraction import plain_text
    result = assess_language(plain_text("<p>" + BASE + "</p><p>Fluent <b>German</b> is required.</p>"))
    assert result.label == REQUIRED
