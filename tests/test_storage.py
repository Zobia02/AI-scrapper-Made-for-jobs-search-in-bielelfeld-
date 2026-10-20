from sqlalchemy import select

from database.models import SourceLink
from services.deduplication import canonical_url
from sources.base import FetchResult


def test_url_identity_preserved():
    assert canonical_url("https://example.org/jobs?gh_jid=12&utm_source=x#about") == "https://example.org/jobs?gh_jid=12"
    assert canonical_url("https://example.org/jobs?gh_jid=13") != canonical_url("https://example.org/jobs?gh_jid=12")


def test_dedup_cross_source_and_history(storage, job):
    assert storage.ingest(job.source, FetchResult(jobs=[job])) == 1
    first = storage.jobs()[0]["first_seen"]
    assert storage.ingest(job.source, FetchResult(jobs=[job])) == 0
    alternate = type(job).model_validate({**job.model_dump(), "source": "alternate", "source_id": "other", "apply_url": "https://example.net/role/2"})
    assert storage.ingest(alternate.source, FetchResult(jobs=[alternate])) == 0
    rows = storage.jobs()
    assert len(rows) == 1 and len(rows[0]["source_links"]) == 2
    assert rows[0]["first_seen"] == first
    job_id = rows[0]["id"]
    storage.save_job(job_id)
    storage.update_application(job_id, "Applied", "Original note", "2026-01-01")
    storage.update_application(job_id, "Interview", "New note", "2026-01-01")
    storage.save_job(job_id, False)
    assert len(storage.applications(history=True)) == 2
    assert any(x["notes"] == "Original note" for x in storage.applications(history=True))
    assert storage.applications()[0]["status"] == "Interview"


def test_distinct_same_board_requisitions(storage, job):
    storage.ingest(job.source, FetchResult(jobs=[job]))
    second = type(job).model_validate({**job.model_dump(), "source_id": "test-2", "apply_url": "https://example.org/jobs/2"})
    storage.ingest(job.source, FetchResult(jobs=[second]))
    assert len(storage.jobs()) == 2


def test_expiry_requires_complete_snapshots(storage, job):
    storage.ingest(job.source, FetchResult(jobs=[job]))
    for _ in range(3):
        storage.ingest(job.source, FetchResult(complete=False))
    assert not storage.jobs()[0]["potentially_expired"]
    storage.ingest(job.source, FetchResult())
    assert not storage.jobs()[0]["potentially_expired"]
    storage.ingest(job.source, FetchResult())
    assert storage.jobs()[0]["potentially_expired"]
    storage.ingest(job.source, FetchResult(jobs=[job]))
    assert not storage.jobs()[0]["potentially_expired"]


def test_lock(storage):
    assert storage.acquire_refresh()
    assert not storage.acquire_refresh()
    storage.release_refresh()
    assert storage.acquire_refresh()
    storage.release_refresh()


def test_persistence(storage, job):
    storage.ingest(job.source, FetchResult(jobs=[job]))
    storage.set_setting("profile", {"skills": ["Python"]})
    from database.storage import Storage
    reopened = Storage(str(storage.engine.url))
    assert len(reopened.jobs()) == 1
    assert reopened.get_setting("profile")["skills"] == ["Python"]
    reopened.engine.dispose()
