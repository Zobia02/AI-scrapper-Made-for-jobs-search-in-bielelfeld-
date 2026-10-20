import httpx
import pytest

from sources.arbeitnow import Arbeitnow
from sources.ashby import Ashby
from sources.base import PublicClient, SourceError
from sources.greenhouse import Greenhouse
from sources.lever import Lever
from services.refresh import refresh


def mock_client(handler):
    return PublicClient(httpx.Client(transport=httpx.MockTransport(handler)), delay=0, sleep=lambda _: None)


def test_robots_blocks():
    calls = []
    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(200, text="User-agent: *\nDisallow: /api/")
    client = mock_client(handler)
    with pytest.raises(SourceError, match="disallows"):
        client.get_json("https://www.arbeitnow.com/api/job-board-api")
    assert len(calls) == 1


def test_429_retry_and_host_allowlist():
    calls = []
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        calls.append(request)
        return httpx.Response(429, headers={"Retry-After": "0"}) if len(calls) == 1 else httpx.Response(200, json={"data": []})
    client = mock_client(handler)
    assert client.get_json("https://www.arbeitnow.com/api/job-board-api") == {"data": []}
    assert len(calls) == 2
    with pytest.raises(SourceError):
        client.get_json("https://127.0.0.1/private")


def test_arbeitnow_pagination(job):
    pages = []
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        page = request.url.params["page"]
        pages.append(page)
        return httpx.Response(200, json={"data": [{
            "slug": "test-"+page, "title": job.title, "company_name": job.company,
            "description": job.description, "location": job.location,
            "url": f"https://example.org/jobs/{page}", "created_at": 1760000000,
        }], "links": {"next": "https://www.arbeitnow.com/api/job-board-api?page=2" if page == "1" else None}})
    result = Arbeitnow().fetch(mock_client(handler))
    assert len(result.jobs) == 2 and pages == ["1", "2"]
    assert not result.complete


def test_greenhouse_updated_is_not_posted(job):
    class Client:
        def get_json(self, *args):
            return {"jobs": [dict(id=1, title=job.title, location={"name": job.location},
                                 content=job.description, absolute_url=str(job.apply_url), updated_at="2026-01-01")]}
    result = Greenhouse("test").fetch(Client())
    assert len(result.jobs) == 1
    assert result.jobs[0].posted_at is None


def test_ashby_unlisted_never_displayed(job):
    class Client:
        def get_json(self, *args):
            return {"jobs": [dict(title=job.title, location=job.location, descriptionPlain=job.description,
                                 jobUrl=str(job.source_url), applyUrl=str(job.apply_url), isListed=False)]}
    assert Ashby("test").fetch(Client()).jobs == []


def test_lever_lists_and_country(job):
    class Client:
        def get_json(self, *args):
            return [dict(id="test", text=job.title, country="DE",
                         categories={"location": job.location}, descriptionPlain="Python developer role.",
                         lists=[{"text": "Requirements", "content": job.description}],
                         hostedUrl=str(job.source_url), applyUrl=str(job.apply_url))]
    result = Lever("test").fetch(Client())
    assert result.jobs[0].language == job.language


def test_failed_source_does_not_erase_jobs(storage, job):
    from sources.base import FetchResult
    storage.ingest(job.source, FetchResult(jobs=[job]))
    class Broken:
        name = "broken"
        def fetch(self, client):
            raise SourceError("Test source unavailable")
    result = refresh(storage, sources=[Broken()], client=object())
    assert result[0]["status"] == "error"
    assert len(storage.jobs()) == 1
    assert storage.acquire_refresh()
    storage.release_refresh()
