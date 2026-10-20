from matching.extraction import parse_date
from sources.base import FetchResult, SourceError, append_job, board_token


class Ashby:
    def __init__(self, board):
        self.board = board_token(board)
        self.name = f"ashby:{board}"

    def fetch(self, client):
        payload = client.get_json(f"https://api.ashbyhq.com/posting-api/job-board/{self.board}", {"includeCompensation": "true"})
        if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
            raise SourceError("Ashby response schema changed.")
        result = FetchResult()
        for row in payload["jobs"]:
            if row.get("isListed") is not True:
                continue
            comp = row.get("compensation") or {}
            locations = [row.get("location", "")] + [x.get("location", "") for x in row.get("secondaryLocations", [])]
            append_job(
                result, source=self.name, source_id=row.get("id") or row.get("jobUrl", ""),
                title=row.get("title", ""), company=self.board, location="; ".join(locations),
                country=((row.get("address") or {}).get("postalAddress") or {}).get("addressCountry"),
                description=row.get("descriptionPlain") or row.get("descriptionHtml", ""),
                source_url=row.get("jobUrl"), apply_url=row.get("applyUrl") or row.get("jobUrl"),
                posted_at=parse_date(row.get("publishedAt")), date_label="Last published",
                types=row.get("employmentType", ""),
                salary=comp.get("scrapeableCompensationSalarySummary"),
                workplace={"Remote": "Remote", "Hybrid": "Hybrid", "OnSite": "On-site"}.get(row.get("workplaceType"), "Unknown"),
            )
        return result
