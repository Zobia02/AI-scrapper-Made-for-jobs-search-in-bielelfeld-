"""ASGI entrypoint for Vercel; local UI still runs with streamlit run app.py."""
import hashlib
import os

from config.settings import ROOT, setting

# Every instance needs the same cookie-signing secret. Keep it out of Git.
# Environment is set before Streamlit reads its server configuration.
password = setting("APP_PASSWORD")
if password:
    os.environ.setdefault(
        "STREAMLIT_SERVER_COOKIE_SECRET",
        hashlib.sha256(("careerscout-cookie:" + password).encode()).hexdigest(),
    )
if os.getenv("VERCEL") == "1":
    # Stay below Vercel's 4.5 MB HTTP request limit, including multipart overhead.
    os.environ.setdefault("STREAMLIT_SERVER_MAX_UPLOAD_SIZE", "4")
    os.environ.setdefault("STREAMLIT_SERVER_FILE_WATCHER_TYPE", "none")

from fastapi import FastAPI
from streamlit import App

from services.hosting import WorkspaceAccess

workspace = App(ROOT / "app.py")
app = FastAPI(
    lifespan=workspace.lifespan(),
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.add_middleware(WorkspaceAccess)
app.mount("/", workspace)
