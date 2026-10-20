from sources.base import FetchResult, SourceError, append_job, board_token


class Lever:
    def __init__(self, board, eu=False):
        self.board = board_token(board)
        self.eu = eu
        self.name = f"lever{'-eu' if eu else ''}:{board}"

    def fetch(self, client):
        result = FetchResult(complete=False)
        host = "api.eu.lever.co" if self.eu else "api.lever.co"
        for page in range(20):
            rows = client.get_json(f"https://{host}/v0/postings/{self.board}", {"mode": "json", "skip": page * 100, "limit": 100})
            if not isinstance(rows, list):
                raise SourceError("Lever response schema changed.")
            for row in rows:
                cat = row.get("categories") or {}
                description = row.get("descriptionPlain") or row.get("description", "")
                description += "\n" + "\n".join(x.get("text", "") + "\n" + x.get("content", "") for x in row.get("lists", []))
                description += "\n" + (row.get("additionalPlain") or row.get("additional", ""))
                pay = row.get("salaryRange") or {}
                salary = f"{pay['min']}–{pay.get('max', pay['min'])} {pay.get('currency', '')} / {pay.get('interval', 'unspecified period')}" if pay.get("min") else None
                append_job(
                    result, source=self.name, source_id=str(row.get("id", "")),
                    title=row.get("text", ""), company=self.board, country=row.get("country"),
                    location="; ".join(cat.get("allLocations") or [cat.get("location", "")]),
                    description=description, source_url=row.get("hostedUrl"),
                    apply_url=row.get("applyUrl") or row.get("hostedUrl"),
                    types=cat.get("commitment", ""), salary=salary,
                    workplace={"remote": "Remote", "hybrid": "Hybrid", "on-site": "On-site"}.get(row.get("workplaceType"), "Unknown"),
                )
            if len(rows) < 100:
                result.complete = result.invalid == 0
                break
        return result
