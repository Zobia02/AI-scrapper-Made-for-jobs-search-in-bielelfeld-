import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from matching.extraction import cities_in, normalized


def canonical_url(url: str) -> str:
    parts = urlsplit(str(url))
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if not k.lower().startswith("utm_") and k.lower() not in {"source", "ref", "referrer", "gh_src", "lever-source"}]
    # Preserve identity parameters such as gh_jid and jobId.
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), urlencode(sorted(query)), ""))


def fingerprint(company: str, title: str, location: str) -> str:
    company = re.sub(r"\b(gmbh|ag|se|inc|ltd)\b", "", normalized(company))
    city = "|".join(sorted(cities_in(location))) or normalized(location)
    value = "|".join(re.sub(r"[^a-z0-9]+", "", normalized(x)) for x in [company, title, city])
    return hashlib.sha256(value.encode()).hexdigest()
