"""Run with python -m services.refresh. Same pipeline as the UI."""
import argparse
import json
import logging
from logging.handlers import RotatingFileHandler

from config.settings import DEFAULT_SOURCES, ROOT, database_url
from database.storage import Storage
from sources.base import PublicClient
from sources.registry import enabled_sources
from services.hosting import on_vercel

log = logging.getLogger("careerscout")


def setup_logging():
    if log.handlers:
        return
    if on_vercel():
        # Function filesystems are disposable; Vercel captures the process log.
        handler = logging.StreamHandler()
    else:
        (ROOT / "logs").mkdir(exist_ok=True)
        handler = RotatingFileHandler(ROOT / "logs" / "refresh.jsonl", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))
    log.addHandler(handler)
    log.setLevel(logging.INFO)


def refresh(storage, progress=None, sources=None, client=None):
    setup_logging()
    if not storage.acquire_refresh():
        raise RuntimeError("Another refresh is running. Wait for it to finish; abandoned locks expire after two hours.")
    own_client = client is None
    client = client or PublicClient()
    output = []
    try:
        sources = sources if sources is not None else enabled_sources(storage.get_setting("sources", DEFAULT_SOURCES))
        for index, source in enumerate(sources):
            if progress:
                progress(index / max(len(sources), 1), f"Checking {source.name}")
            try:
                result = source.fetch(client)
                added = storage.ingest(source.name, result)
                status = "success" if result.invalid == 0 else "partial"
                message = f"{result.skipped} outside scope; {result.invalid} invalid. " + (
                    "Full board checked." if result.complete else "Partial/rolling feed; absence does not prove expiry."
                )
                row = dict(source=source.name, status=status, found=len(result.jobs), added=added, message=message)
            except Exception as exc:
                # Do not log response bodies, credentials, CVs, connection strings or arbitrary exception text.
                from sources.base import SourceError
                message = str(exc) if isinstance(exc, SourceError) else f"{type(exc).__name__}: source refresh failed; see troubleshooting."
                row = dict(source=source.name, status="error", found=0, added=0, message=message)
            storage.record_run(**row)
            log.info(json.dumps(row, ensure_ascii=False))
            output.append(row)
        if progress:
            progress(1.0, "Refresh complete")
        return output
    finally:
        if own_client:
            client.close()
        storage.release_refresh()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-persistent-db", action="store_true")
    args = parser.parse_args()
    if args.require_persistent_db and not database_url().startswith("postgresql"):
        parser.error("Scheduled cloud refresh requires a persistent PostgreSQL DATABASE_URL.")
    result = refresh(Storage())
    print(json.dumps(result, indent=2))
    if not result or all(row["status"] == "error" for row in result):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
