from datetime import timedelta
from urllib.parse import urlsplit

from sqlalchemy import create_engine, delete, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from config.settings import database_url
from database.models import (
    Application, ApplicationEvent, Base, Job, RefreshLock, RefreshRun, SavedJob,
    Setting, SourceLink, utcnow,
)
from services.deduplication import canonical_url, fingerprint

STATUSES = ["Interested", "Applied", "Assessment", "Interview", "Offer", "Rejected"]


class Storage:
    def __init__(self, url=None):
        url = url or database_url()
        kwargs = {"pool_pre_ping": True}
        if url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False, "timeout": 30}
        self.engine = create_engine(url, **kwargs)
        if url.startswith("sqlite"):
            @event.listens_for(self.engine, "connect")
            def configure_sqlite(connection, _):
                connection.execute("PRAGMA foreign_keys=ON")
                connection.execute("PRAGMA journal_mode=WAL")
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(self.engine, expire_on_commit=False)

    def get_setting(self, key, default=None):
        with self.session() as s:
            row = s.get(Setting, key)
            return row.value if row else default

    def set_setting(self, key, value):
        with self.session.begin() as s:
            s.merge(Setting(key=key, value=value))

    def acquire_refresh(self):
        with self.session.begin() as s:
            # Crash recovery after a deliberately generous lease.
            s.execute(delete(RefreshLock).where(RefreshLock.acquired_at < utcnow() - timedelta(hours=2)))
        try:
            with self.session.begin() as s:
                s.add(RefreshLock(key="discovery"))
            return True
        except IntegrityError:
            return False

    def release_refresh(self):
        with self.session.begin() as s:
            s.execute(delete(RefreshLock).where(RefreshLock.key == "discovery"))

    def ingest(self, source, result):
        now, added, seen = utcnow(), 0, set()
        with self.session.begin() as s:
            for incoming in result.jobs:
                data = incoming.model_dump(mode="json")
                url = canonical_url(str(incoming.apply_url))
                fp = fingerprint(incoming.company, incoming.title, incoming.location)
                link = s.scalar(select(SourceLink).where(SourceLink.source == source, SourceLink.source_id == incoming.source_id))
                job = s.get(Job, link.job_id) if link else s.scalar(select(Job).where(Job.canonical_url == url))
                if job is None:
                    candidates = list(s.scalars(select(Job).where(Job.fingerprint == fp)))
                    # Do not merge two distinct requisitions from the same board by title alone.
                    for candidate in candidates:
                        same_board = s.scalar(select(SourceLink).where(SourceLink.job_id == candidate.id, SourceLink.source == source))
                        if same_board is None:
                            job = candidate
                            break
                if job is None:
                    job = Job(canonical_url=url, fingerprint=fp, data=data, first_seen=now, last_verified=now)
                    s.add(job)
                    s.flush()
                    added += 1
                else:
                    # Keep the richest description when another source only returns a summary.
                    if len(data["description"]) >= len(job.data.get("description", "")) or job.data.get("source") == source:
                        job.data = data
                    job.last_verified = now
                    job.potentially_expired = False
                if link is None:
                    link = SourceLink(job_id=job.id, source=source, source_id=incoming.source_id, url=str(incoming.source_url))
                    s.add(link)
                link.last_seen, link.missing_runs = now, 0
                link.url = str(incoming.source_url)
                seen.add(incoming.source_id)
            if result.complete:
                for link in s.scalars(select(SourceLink).where(SourceLink.source == source)):
                    if link.source_id not in seen:
                        link.missing_runs += 1
            # Mark uncertain expiry only; never remove saved jobs/applications.
            for job in s.scalars(select(Job)):
                links = list(s.scalars(select(SourceLink).where(SourceLink.job_id == job.id)))
                job.potentially_expired = (
                    job.last_verified < now - timedelta(days=30)
                    or bool(links) and all(x.missing_runs >= 2 for x in links)
                )
        return added

    def jobs(self):
        with self.session() as s:
            saved = {x.job_id: x.collection for x in s.scalars(select(SavedJob))}
            apps = {x.job_id: x.status for x in s.scalars(select(Application))}
            links = {}
            for link in s.scalars(select(SourceLink)):
                links.setdefault(link.job_id, []).append({"source": link.source, "url": link.url})
            return [
                {**j.data, "id": j.id, "first_seen": j.first_seen.isoformat() + "Z",
                 "last_verified": j.last_verified.isoformat() + "Z",
                 "potentially_expired": j.potentially_expired or j.last_verified < utcnow() - timedelta(days=30),
                 "saved": j.id in saved, "collection": saved.get(j.id, ""),
                 "application_status": apps.get(j.id, ""), "source_links": links.get(j.id, [])}
                for j in s.scalars(select(Job).order_by(Job.first_seen.desc()))
            ]

    def save_job(self, job_id, saved=True, collection="Shortlist"):
        with self.session.begin() as s:
            if saved:
                s.merge(SavedJob(job_id=job_id, collection=collection[:100]))
            else:
                s.execute(delete(SavedJob).where(SavedJob.job_id == job_id))

    def update_application(self, job_id, status, notes="", applied_date=None, followup_date=None, submitted_url=""):
        if status not in STATUSES:
            raise ValueError("Unknown application status.")
        if submitted_url and urlsplit(submitted_url).scheme not in {"http", "https"}:
            raise ValueError("Application link must begin with https:// or http://.")
        values = dict(status=status, notes=notes, applied_date=applied_date,
                      followup_date=followup_date, submitted_url=submitted_url)
        with self.session.begin() as s:
            s.merge(Application(job_id=job_id, **values, updated_at=utcnow()))
            s.add(ApplicationEvent(job_id=job_id, snapshot=values))

    def applications(self, history=False):
        with self.session() as s:
            if history:
                return [dict(job_id=x.job_id, **x.snapshot, recorded_at=x.created_at.isoformat())
                        for x in s.scalars(select(ApplicationEvent).order_by(ApplicationEvent.created_at.desc()))]
            return [{c.name: getattr(x, c.name) for c in Application.__table__.columns}
                    for x in s.scalars(select(Application))]

    def record_run(self, source, status, found=0, added=0, message=""):
        with self.session.begin() as s:
            s.add(RefreshRun(source=source, status=status, found=found, added=added, message=message))

    def runs(self, limit=100):
        with self.session() as s:
            return [{c.name: getattr(x, c.name) for c in RefreshRun.__table__.columns}
                    for x in s.scalars(select(RefreshRun).order_by(RefreshRun.id.desc()).limit(limit))]
