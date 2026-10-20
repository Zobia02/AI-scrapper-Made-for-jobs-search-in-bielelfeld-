from matching.extraction import parse_date
from sources.base import FetchResult, SourceError, append_job


class Arbeitnow:
    name = "arbeitnow"

    def __init__(self, pages=5):
        self.pages = min(max(int(pages), 1), 10)

    def fetch(self, client):
        result = FetchResult(complete=False)  # Rolling feed is never an authoritative full inventory.
        for page in range(1, self.pages + 1):
            payload = client.get_json("https://www.arbeitnow.com/api/job-board-api", {"page": page})
            if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
                raise SourceError("Arbeitnow response schema changed.")
            for row in payload["data"]:
                append_job(
                    result, source=self.name, source_id=str(row.get("slug", "")),
                    title=row.get("title", ""), company=row.get("company_name", ""),
                    location=row.get("location", ""), description=row.get("description", ""),
                    source_url=row.get("url"), apply_url=row.get("url"),
                    posted_at=parse_date(row.get("created_at")),
                    types=" ".join(row.get("job_types", [])),
                    workplace="Remote" if row.get("remote") else "Unknown",
                )
            if not payload["data"] or not payload.get("links", {}).get("next"):
                break
        return result
