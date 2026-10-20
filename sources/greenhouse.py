from sources.base import FetchResult, SourceError, append_job, board_token


class Greenhouse:
    def __init__(self, board):
        self.board = board_token(board)
        self.name = f"greenhouse:{board}"

    def fetch(self, client):
        payload = client.get_json(f"https://boards-api.greenhouse.io/v1/boards/{self.board}/jobs", {"content": "true"})
        if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
            raise SourceError("Greenhouse response schema changed.")
        result = FetchResult()
        for row in payload["jobs"]:
            append_job(
                result, source=self.name, source_id=str(row.get("id", "")),
                title=row.get("title", ""), company=self.board,
                location=(row.get("location") or {}).get("name", ""),
                description=row.get("content", ""), source_url=row.get("absolute_url"),
                apply_url=row.get("absolute_url"),
                # updated_at is NOT a posting date. Keep publication date unknown.
            )
        return result
