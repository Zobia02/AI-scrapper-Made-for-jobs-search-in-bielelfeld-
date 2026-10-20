"""Synthetic fixtures are exclusively for tests; never loaded by the application."""
import pytest

from database.storage import Storage
from sources.base import build_job


@pytest.fixture
def storage(tmp_path):
    db = Storage(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    yield db
    db.engine.dispose()


@pytest.fixture
def job():
    return build_job(
        source="test-board", source_id="test-1", title="Working Student Python Developer",
        company="TEST ONLY Company", location="Bielefeld, Germany",
        description=(
            "Build Python and SQL applications with Docker. You are enrolled in a master's degree. "
            "Our working language is English. German is not required. This is a paid position."
        ),
        source_url="https://example.org/jobs/1", apply_url="https://example.org/jobs/1?utm_source=test",
    )
