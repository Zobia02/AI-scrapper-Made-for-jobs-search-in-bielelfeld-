"""Shared hosting checks. Never include secret values in error responses."""
import base64
import binascii
import hmac
import os

from config.settings import configured_database_url, setting


def on_vercel():
    return os.getenv("VERCEL") == "1"


def deployment_issues():
    if not on_vercel():
        return []
    issues = []
    if not setting("APP_PASSWORD"):
        issues.append("Set APP_PASSWORD in Vercel environment variables.")
    if not configured_database_url().startswith(
        ("postgres://", "postgresql://", "postgresql+psycopg://")
    ):
        issues.append("Set DATABASE_URL to a persistent PostgreSQL database.")
    return issues


def authorized_header(header: str, password: str) -> bool:
    """Browser HTTP Basic authentication for the single-owner ASGI workspace."""
    if not password:
        return False
    try:
        scheme, token = header.split(" ", 1)
        if scheme.lower() != "basic":
            return False
        decoded = base64.b64decode(token, validate=True).decode("utf-8")
        username, supplied = decoded.split(":", 1)
    except (ValueError, UnicodeError, binascii.Error):
        return False
    return hmac.compare_digest(username.encode(), b"careerscout") and hmac.compare_digest(
        supplied.encode(), password.encode()
    )


class WorkspaceAccess:
    """Protect HTTP files and WebSockets, not only the Streamlit page."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] not in {"http", "websocket"}:
            return await self.app(scope, receive, send)
        issues = deployment_issues()
        password = setting("APP_PASSWORD")
        header = dict(scope.get("headers", [])).get(b"authorization", b"").decode("latin-1")
        status = 503 if issues else 401 if password and not authorized_header(header, password) else 0
        if status:
            if scope["type"] == "websocket":
                await send({"type": "websocket.close", "code": 1008})
                return
            from starlette.responses import PlainTextResponse
            message = (
                "CareerScout deployment setup required:\n" + "\n".join(issues)
                if issues else "Sign in with username careerscout and your workspace password."
            )
            headers = {"Cache-Control": "no-store"}
            if status == 401:
                headers["WWW-Authenticate"] = 'Basic realm="CareerScout Germany", charset="UTF-8"'
            return await PlainTextResponse(message, status_code=status, headers=headers)(scope, receive, send)
        async def private_response(message):
            if message["type"] == "http.response.start":
                headers = [
                    (key, value) for key, value in message.get("headers", [])
                    if key.lower() != b"cache-control"
                ]
                headers.extend([
                    (b"cache-control", b"private, no-store"),
                    (b"x-content-type-options", b"nosniff"),
                ])
                message = {**message, "headers": headers}
            await send(message)

        return await self.app(scope, receive, private_response)
