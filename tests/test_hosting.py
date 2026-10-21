"""Hosting regressions use only synthetic credentials and temporary databases."""
import base64
import os
from pathlib import Path
import subprocess
import sys

import pytest
from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from config.settings import database_url, setting
from services.hosting import WorkspaceAccess, authorized_header


def basic(password="test-only-password", username="careerscout"):
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


@pytest.fixture
def hosted(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("APP_PASSWORD", "test-only-password")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@db.invalid/test")
    monkeypatch.delenv("POSTGRES_URL", raising=False)
    app = FastAPI()
    app.add_middleware(WorkspaceAccess)

    @app.get("/{path:path}")
    def private_file(path: str):
        return {"private": path}

    @app.websocket("/_stcore/stream")
    async def stream(websocket: WebSocket):
        await websocket.accept()
        await websocket.send_text("private workspace")
        await websocket.close()

    with TestClient(app) as client:
        yield client


@pytest.mark.parametrize("path", ["/", "/_stcore/health", "/media/private.csv", "/_stcore/upload_file/session/file"])
def test_files_require_authentication(hosted, path):
    response = hosted.get(path)
    assert response.status_code == 401
    assert response.headers["www-authenticate"].startswith("Basic")
    assert response.headers["cache-control"] == "no-store"
    assert "test-only-password" not in response.text
    assert hosted.get(path, headers=basic("wrong-password")).status_code == 401
    response = hosted.get(path, headers=basic())
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"


def test_websocket_requires_authentication(hosted):
    with pytest.raises(WebSocketDisconnect) as exc:
        with hosted.websocket_connect("/_stcore/stream"):
            pass
    assert exc.value.code == 1008
    with hosted.websocket_connect("/_stcore/stream", headers=basic()) as socket:
        assert socket.receive_text() == "private workspace"


@pytest.mark.parametrize("missing", ["APP_PASSWORD", "DATABASE_URL"])
def test_incomplete_deployment_is_closed(hosted, monkeypatch, missing):
    monkeypatch.delenv(missing)
    response = hosted.get("/", headers=basic())
    assert response.status_code == 503
    assert missing in response.text
    assert "test-only-password" not in response.text
    assert "db.invalid" not in response.text
    with pytest.raises(WebSocketDisconnect):
        with hosted.websocket_connect("/_stcore/stream", headers=basic()):
            pass


@pytest.mark.parametrize("url", ["", "sqlite:///temporary.db", "mysql://test:test@db.invalid/test"])
def test_vercel_rejects_nonpersistent_database(hosted, monkeypatch, url):
    monkeypatch.setenv("DATABASE_URL", url)
    assert hosted.get("/", headers=basic()).status_code == 503
    with pytest.raises(RuntimeError, match="persistent PostgreSQL"):
        database_url()


def test_vercel_integration_database_url(hosted, monkeypatch):
    monkeypatch.delenv("DATABASE_URL")
    monkeypatch.setenv("POSTGRES_URL", "postgres://test:test@db.invalid/test?sslmode=require")
    assert database_url() == "postgresql+psycopg://test:test@db.invalid/test?sslmode=require"
    assert hosted.get("/", headers=basic()).status_code == 200
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@preferred.invalid/test")
    assert "preferred.invalid" in database_url()


def test_hosted_secrets_do_not_fall_back_to_local_files(monkeypatch):
    import streamlit as st

    class ForbiddenSecrets:
        def get(self, *args):
            raise AssertionError("Hosted settings must not read local secrets")

    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.delenv("APP_PASSWORD", raising=False)
    monkeypatch.setattr(st, "secrets", ForbiddenSecrets())
    assert setting("APP_PASSWORD", "default") == "default"


@pytest.mark.parametrize("header", ["", "Basic ???", "Bearer abc", "Basic YWJj", "Basic /w=="])
def test_malformed_credentials_are_denied(header):
    assert not authorized_header(header, "test-only-password")


def test_unicode_password_and_username():
    password = "test-only:p\u00e4ssword"
    assert authorized_header(basic(password)["Authorization"], password)
    assert not authorized_header(basic(password, "other")["Authorization"], password)
    assert not authorized_header(basic()["Authorization"], "")


def test_real_asgi_entrypoint(tmp_path):
    # Streamlit has a process-wide runtime. Isolate this from AppTest's runtime.
    env = dict(os.environ)
    env.pop("VERCEL", None)
    env["APP_PASSWORD"] = "test-only-password"
    env["DATABASE_URL"] = f"sqlite:///{(tmp_path / 'asgi.db').as_posix()}"
    script = '''
from fastapi.testclient import TestClient
from streamlit.proto.BackMsg_pb2 import BackMsg
from streamlit.proto.ForwardMsg_pb2 import ForwardMsg
from server import app

with TestClient(app) as client:
    assert client.get('/').status_code == 401
    client.auth = ('careerscout', 'test-only-password')
    response = client.get('/')
    assert response.status_code == 200 and '<html' in response.text.lower()
    assert client.get('/_stcore/health').status_code == 200
    # Use the same auth handshake as the browser and request the actual UI.
    import base64
    token = base64.b64encode(b'careerscout:test-only-password').decode()
    with client.websocket_connect('/_stcore/stream', headers={'Authorization': 'Basic ' + token}, subprotocols=['streamlit']) as socket:
        request = BackMsg()
        request.rerun_script.query_string = ''
        socket.send_bytes(request.SerializeToString())
        saw_ui = False
        for _ in range(300):
            message = ForwardMsg()
            message.ParseFromString(socket.receive_bytes())
            if message.HasField('delta'):
                assert not message.delta.new_element.HasField('exception'), str(message.delta)
                saw_ui = True
            if message.HasField('script_finished'):
                assert saw_ui
                break
        else:
            raise AssertionError('Streamlit UI did not finish rendering')
'''
    result = subprocess.run(
        [sys.executable, "-c", script], env=env,
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
