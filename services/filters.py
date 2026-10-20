from datetime import datetime, timezone

from matching.extraction import parse_date
from matching.language_detection import ENGLISH, NO_GERMAN


def filter_jobs(jobs, filters, now=None):
    now = now or datetime.now(timezone.utc)
    results = []
    for job in jobs:
        if job.get("potentially_expired") and not filters.get("include_expired", False):
            continue
        if filters.get("query"):
            searchable = " ".join(str(job.get(k, "")) for k in ["title", "company", "description"]).lower()
            if not all(term in searchable for term in filters["query"].lower().split()):
                continue
        if filters.get("category") and filters["category"] != "All categories" and filters["category"] not in job.get("categories", []):
            continue
        if filters.get("types") is not None and job["job_type"] not in filters["types"]:
            continue
        if filters.get("languages") is not None and job["language"] not in filters["languages"]:
            continue
        if filters.get("city") and filters["city"] != "All Germany":
            if filters["city"] not in job.get("cities", []) and filters["city"].lower() not in job["location"].lower():
                continue
        if filters.get("workplace", "Any") != "Any" and job["workplace"] != filters["workplace"]:
            continue
        if filters.get("days") is not None:
            dt = parse_date(job.get("posted_at"))
            if not dt or not 0 <= (now - dt).total_seconds() <= filters["days"] * 86400:
                continue
        if filters.get("paid_only") and job["paid"] != "Confirmed paid":
            continue
        if filters.get("salary_only") and not job.get("salary"):
            continue
        if filters.get("salary_query") and filters["salary_query"].lower() not in (job.get("salary") or "").lower():
            continue
        if filters.get("skills") and not set(filters["skills"]) <= set(job.get("skills", [])):
            continue
        if filters.get("companies") and job["company"] not in filters["companies"]:
            continue
        if filters.get("sources") and not set(filters["sources"]) & {x["source"] for x in job.get("source_links", [{"source": job["source"]}])}:
            continue
        if job["match"]["score"] < filters.get("min_score", 0):
            continue
        if filters.get("authorization") == "Explicit wording present" and not job.get("authorization"):
            continue
        if filters.get("authorization") == "Unknown / not stated" and job.get("authorization"):
            continue
        if filters.get("authorization_query") and filters["authorization_query"].lower() not in " ".join(job.get("authorization", [])).lower():
            continue
        results.append(job)
    return sorted(results, key=lambda j: j["match"]["score"], reverse=True)


def default_filters():
    return {"languages": [ENGLISH, NO_GERMAN], "min_score": 0, "paid_only": False, "include_expired": False}
