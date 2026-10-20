"""Optional checks; no assertions that a particular employer must be hiring."""
import os

import pytest

from sources.arbeitnow import Arbeitnow
from sources.greenhouse import Greenhouse
from sources.lever import Lever
from sources.base import PublicClient


@pytest.mark.live
@pytest.mark.skipif(os.getenv("RUN_LIVE_TESTS") != "1", reason="Set RUN_LIVE_TESTS=1 to contact real APIs.")
@pytest.mark.parametrize("source", [Arbeitnow(1), Greenhouse("agilerobotsse"), Lever("quantinuum", eu=True)])
def test_live_api(source):
    client = PublicClient()
    try:
        result = source.fetch(client)
        assert result.invalid == 0
        for job in result.jobs:
            assert str(job.source_url).startswith("https://")
            assert job.country == "Germany"
    finally:
        client.close()
