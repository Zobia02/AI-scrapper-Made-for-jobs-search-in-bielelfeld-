import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx
from pydantic import BaseModel, Field, HttpUrl

from config.settings import setting
from matching.extraction import (
    categories_in, cities_in, germany_location, job_type, pay_evidence, plain_text, skills_in,
)
from matching.language_detection import assess_language, sentences

ALLOWED_HOSTS = {
    "www.arbeitnow.com", "boards-api.greenhouse.io",
    "api.lever.co", "api.eu.lever.co", "api.ashbyhq.com",
}


class SourceError(Exception):
    pass


class JobData(BaseModel):
    source: str
    source_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    company: str = Field(min_length=1)
    location: str
    country: str = "Germany"
    description: str
    source_url: HttpUrl
    apply_url: HttpUrl
    posted_at: datetime | None = None
    date_label: str = "Posted"
    job_type: str
    workplace: str = "Unknown"
    salary: str | None = None
    paid: str = "Unknown"
    skills: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    cities: list[str] = Field(default_factory=list)
    language: str = "Unknown"
    language_evidence: list[str] = Field(default_factory=list)
    authorization: list[str] = Field(default_factory=list)


@dataclass
class FetchResult:
    jobs: list[JobData] = field(default_factory=list)
    complete: bool = True
    skipped: int = 0
    invalid: int = 0


class PublicClient:
    """Allowlisted, identified API requests with robots checks, bounded retries and pacing."""
    def __init__(self, client=None, delay=1.1, sleep=time.sleep):
        self.agent = setting("CAREERSCOUT_USER_AGENT", "CareerScoutGermany/1.0 (personal job discovery)")
        self.client = client or httpx.Client(
            timeout=httpx.Timeout(25, connect=10), follow_redirects=False,
            headers={"User-Agent": self.agent, "Accept": "application/json"},
        )
        self.delay, self.sleep = delay, sleep
        self.robots = {}
        self.last_request = {}

    def close(self):
        self.client.close()

    def _request(self, url, params=None, delay=None):
        host = urlsplit(url).hostname
        if urlsplit(url).scheme != "https" or host not in ALLOWED_HOSTS:
            raise SourceError("Only reviewed public API hosts are allowed.")
        for attempt in range(3):
            self.sleep(max(0, (delay or self.delay) - (time.monotonic() - self.last_request.get(host, 0))))
            self.last_request[host] = time.monotonic()
            try:
                response = self.client.get(url, params=params)
            except httpx.TransportError:
                if attempt == 2:
                    raise SourceError("Network timeout or connection failure; retry later.") from None
                self.sleep(2 ** attempt)
                continue
            if response.status_code == 429 or response.status_code >= 500:
                retry = response.headers.get("Retry-After", "")
                # Never retry sooner than a server's requested delay.
                if retry and (not retry.isdigit() or int(retry) > 30):
                    raise SourceError("Server requested a longer backoff; retry on a later refresh.")
                if attempt < 2:
                    self.sleep(max(int(retry or 0), 2 ** (attempt + 1)))
                    continue
            return response
        raise SourceError("Source temporarily unavailable.")

    def get_json(self, url, params=None):
        origin = f"https://{urlsplit(url).netloc}"
        if origin not in self.robots:
            response = self._request(origin + "/robots.txt")
            parser = RobotFileParser()
            if response.status_code in (404, 410):
                parser.parse([])  # Documented API; no robots file.
            elif response.status_code == 200:
                if "<html" in response.text.lower():
                    raise SourceError("Robots policy returned an HTML challenge; access stopped.")
                parser.parse(response.text.splitlines())
            else:
                raise SourceError(f"Unable to verify robots policy (HTTP {response.status_code}).")
            self.robots[origin] = parser
        parser = self.robots[origin]
        if not parser.can_fetch(self.agent, url):
            raise SourceError("robots.txt disallows this API path; source skipped.")
        delay = max(self.delay, parser.crawl_delay(self.agent) or 0)
        rate = parser.request_rate(self.agent)
        if rate:
            delay = max(delay, rate.seconds / rate.requests)
        if delay > 30:
            raise SourceError("Published crawl delay exceeds this interactive refresh budget.")
        response = self._request(url, params, delay)
        if response.status_code != 200:
            raise SourceError(f"Public API returned HTTP {response.status_code}; no access controls bypassed.")
        if len(response.content) > 20_000_000:
            raise SourceError("API response exceeds the 20 MB limit.")
        try:
            return response.json()
        except ValueError:
            raise SourceError("Source returned invalid JSON or an access challenge.") from None


def board_token(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", value):
        raise ValueError("Board names can contain only letters, digits, underscores and hyphens.")
    return value


def build_job(*, types="", country=None, **data) -> JobData | None:
    location = data.get("location") or "Unknown"
    kind = job_type(data["title"], types)
    if not kind or not germany_location(location, country):
        return None
    text = plain_text(data.get("description", ""))
    skills = skills_in(data["title"] + "\n" + text)
    cats = categories_in(data["title"] + "\n" + text, skills)
    if not cats:
        return None
    language = assess_language(data["title"] + "\n" + text)
    paid, salary = pay_evidence(text)
    if data.get("salary"):
        salary = data["salary"]
        if paid != "Unpaid":
            paid = "Confirmed paid"
    auth = [s for s in sentences(text) if re.search(
        r"visa|work (permit|authorization|authorisation)|right to work|arbeitserlaubnis|aufenthaltstitel|sponsorship", s, re.I
    )]
    if data.get("workplace", "Unknown") == "Unknown":
        if re.search(r"\bhybrid\b|hybrides arbeiten", text, re.I):
            data["workplace"] = "Hybrid"
        elif re.search(r"\b(?:fully remote|100% remote|remote within germany|remote in germany)\b", text, re.I):
            data["workplace"] = "Remote"
        elif re.search(r"\b(?:on-site role|onsite role|on-site position|on site position)\b", text, re.I):
            data["workplace"] = "On-site"
    data.update(description=text, location=location, job_type=kind, skills=skills, categories=cats,
                cities=cities_in(location), paid=paid, salary=salary, language=language.label,
                language_evidence=language.evidence, authorization=auth[:5])
    return JobData(**data)


def append_job(result, **fields):
    try:
        job = build_job(**fields)
        if job:
            result.jobs.append(job)
        else:
            result.skipped += 1
    except (ValueError, TypeError, KeyError):
        result.invalid += 1
        result.complete = False
