import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def setting(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value:
        return value
    if os.getenv("VERCEL") == "1":
        # Hosted secrets come from Vercel, never a local Streamlit secrets file.
        return default
    try:
        import streamlit as st
        return str(st.secrets.get(name, default))
    except (FileNotFoundError, KeyError):
        return default


def configured_database_url() -> str:
    # Vercel PostgreSQL integrations may supply POSTGRES_URL automatically.
    return setting("DATABASE_URL") or setting("POSTGRES_URL")


def database_url() -> str:
    url = configured_database_url()
    if os.getenv("VERCEL") == "1" and not url.startswith(
        ("postgres://", "postgresql://", "postgresql+psycopg://")
    ):
        raise RuntimeError("Vercel requires a persistent PostgreSQL DATABASE_URL.")
    if not url:
        (ROOT / "data").mkdir(exist_ok=True)
        return f"sqlite:///{(ROOT / 'data' / 'careerscout.db').as_posix()}"
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return url.replace(prefix, "postgresql+psycopg://", 1)
    return url


DEFAULT_SOURCES = {
    "arbeitnow": True,
    "arbeitnow_pages": 5,
    "greenhouse": ["agilerobotsse", "planetlabs", "axon", "celonis", "hellofresh", "contentful"],
    "lever": ["quantco-", "novaspace"],
    "lever_eu": ["quantinuum"],
    "ashby": [],
}

DISABLED_SOURCES = {
    "Ashby": "Adapter implemented but disabled by default: robots.txt returned HTTP 401 during live verification; no policy bypass.",
    "Bundesagentur für Arbeit": "Disabled: no verified public reuse permission for the Jobsuche endpoint; unofficial API descriptions are insufficient.",
    "StepStone": "Disabled: partner feeds require a contract.",
    "Indeed": "Disabled: no approved publisher/search API credentials.",
    "LinkedIn": "Disabled: automated scraping prohibited; no approved search API access.",
    "Glassdoor": "Disabled: no verified open collection API or permission.",
    "JOIN": "Direct collection disabled: no verified public aggregation permission. Listings may arrive through Arbeitnow's authorized API.",
    "University portals": "Disabled until a specific institution publishes a permitted feed/API.",
}
