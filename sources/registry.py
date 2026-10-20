from config.settings import DEFAULT_SOURCES
from sources.arbeitnow import Arbeitnow
from sources.ashby import Ashby
from sources.greenhouse import Greenhouse
from sources.lever import Lever


def enabled_sources(config=None):
    config = config or DEFAULT_SOURCES
    sources = [Arbeitnow(config.get("arbeitnow_pages", 5))] if config.get("arbeitnow") else []
    for key, cls in [("greenhouse", Greenhouse), ("lever", Lever), ("ashby", Ashby)]:
        for board in config.get(key, []):
            sources.append(cls(board))
    for board in config.get("lever_eu", []):
        sources.append(Lever(board, eu=True))
    return sources
