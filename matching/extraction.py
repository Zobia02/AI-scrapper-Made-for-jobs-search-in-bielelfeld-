import re
import unicodedata
from datetime import datetime, timezone
from html import unescape

from bs4 import BeautifulSoup

SKILLS = {
    "Python": ["python"], "C#": ["c#", "c sharp"], "JavaScript": ["javascript"],
    "TypeScript": ["typescript"], "Angular": ["angular"], "React": ["react", "react.js"],
    "Next.js": ["next.js", "nextjs"], "ASP.NET Core": ["asp.net", ".net", "dotnet"],
    "Entity Framework": ["entity framework"], "Flask": ["flask"],
    "Machine Learning": ["machine learning", "maschinelles lernen", "ml"],
    "Deep Learning": ["deep learning"], "NLP": ["nlp", "natural language processing"],
    "Generative AI": ["generative ai", "genai", "generative artificial intelligence"],
    "LLM": ["llm", "llms", "large language model"], "RAG": ["rag", "retrieval augmented", "retrieval-augmented"],
    "Azure OpenAI": ["azure openai"], "Azure AI Search": ["azure ai search", "azure cognitive search"],
    "Azure": ["azure"], "PyTorch": ["pytorch"], "TensorFlow": ["tensorflow"],
    "Keras": ["keras"], "REST API": ["rest api", "restful"], "SQL": ["sql", "postgresql", "mysql"],
    "Git": ["git"], "GitHub": ["github"], "CI/CD": ["ci/cd", "continuous integration"],
    "Docker": ["docker"], "Kubernetes": ["kubernetes", "k8s"], "AWS": ["aws", "amazon web services"],
    "Java": ["java"], "C++": ["c++"], "Go": ["golang"], "Linux": ["linux"],
    "Spark": ["spark"], "Django": ["django"], "FastAPI": ["fastapi"], "GCP": ["gcp", "google cloud"],
}
CATEGORIES = {
    "AI / ML": ["Machine Learning", "Deep Learning", "PyTorch", "TensorFlow", "Keras"],
    "NLP / LLM / GenAI": ["NLP", "LLM", "Generative AI", "RAG", "Azure OpenAI"],
    "Python": ["Python", "Flask", "Django", "FastAPI"],
    "Angular / React": ["Angular", "React", "Next.js", "JavaScript", "TypeScript"],
    ".NET / C#": ["C#", "ASP.NET Core", "Entity Framework"],
    "Full Stack": ["full stack", "fullstack", "full-stack"],
    "Cloud / DevOps": ["Azure", "AWS", "Docker", "Kubernetes", "CI/CD", "GCP", "devops", "cloud"],
    "Research Assistant / HiWi": ["research assistant", "hiwi", "wissenschaftliche hilfskraft", "studentische hilfskraft"],
}
CITY_ALIASES = {
    "Bielefeld": ["bielefeld"], "Düsseldorf": ["dusseldorf", "duesseldorf"],
    "Cologne": ["cologne", "koln", "koeln"], "Dortmund": ["dortmund"],
    "Münster": ["munster", "muenster"], "Hamburg": ["hamburg"], "Berlin": ["berlin"],
    "Munich": ["munich", "munchen", "muenchen"], "Stuttgart": ["stuttgart"],
    "Frankfurt": ["frankfurt"], "Bonn": ["bonn"], "Darmstadt": ["darmstadt"],
    "Karlsruhe": ["karlsruhe"], "Aachen": ["aachen"], "Dresden": ["dresden"],
    "Leipzig": ["leipzig"], "Heidelberg": ["heidelberg"], "Potsdam": ["potsdam"],
    "Nuremberg": ["nuremberg", "nurnberg"], "Essen": ["essen"], "Bochum": ["bochum"],
    "Hannover": ["hannover", "hanover"], "Bremen": ["bremen"], "Freiburg": ["freiburg"],
    "Walldorf": ["walldorf"], "Ulm": ["ulm"], "Wolfsburg": ["wolfsburg"],
    "Kassel": ["kassel"], "Tübingen": ["tubingen", "tuebingen"], "Gilching": ["gilching"],
}


def plain_text(value: str | None) -> str:
    soup = BeautifulSoup(unescape(unescape(value or "")), "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    # Keep inline emphasis in the same sentence; separate only structural blocks.
    for tag in soup.find_all(["p", "li", "div", "br", "h1", "h2", "h3", "h4", "tr"]):
        tag.insert_before("\n")
        tag.insert_after("\n")
    return "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in soup.get_text(" ").splitlines() if line.strip())


def normalized(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text.lower()) if not unicodedata.combining(c))


def contains(text: str, term: str) -> bool:
    return bool(re.search(r"(?<!\w)" + re.escape(term.lower()) + r"(?!\w)", text.lower()))


def skills_in(text: str) -> list[str]:
    return [name for name, aliases in SKILLS.items() if any(contains(text, a) for a in aliases)]


def categories_in(text: str, skills: list[str]) -> list[str]:
    return [name for name, terms in CATEGORIES.items() if any(t in skills or contains(text, t) for t in terms)]


def cities_in(location: str) -> list[str]:
    text = normalized(location)
    return [city for city, aliases in CITY_ALIASES.items() if any(contains(text, a) for a in aliases)]


def germany_location(location: str, country: str | None = None) -> bool:
    if country and country.upper() in {"DE", "DEU", "GERMANY", "DEUTSCHLAND"}:
        return True
    if re.search(r"\b(germany|deutschland)\b", location, re.I):
        return True
    if country and country.upper() not in {"DE", "DEU", "GERMANY", "DEUTSCHLAND"}:
        return False
    return bool(cities_in(location)) and not re.search(r"\b(USA|UK|Canada|United States)\b", location, re.I)


def job_type(title: str, types: str = "") -> str | None:
    text = title + " " + types
    if re.search(r"werkstudent|working[\s-]*student|student[\s-]*worker", text, re.I):
        return "Werkstudent / Working Student"
    if re.search(r"\b(intern|internship|praktikum|praktikant\w*)\b", text, re.I):
        return "Internship / Praktikum"
    if re.search(r"hiwi|hilfskraft|research assistant|student assistant", text, re.I):
        return "Research Assistant / HiWi"
    return None


def parse_date(value) -> datetime | None:
    if not value:
        return None
    try:
        if isinstance(value, (int, float)):
            dt = datetime.fromtimestamp(value / 1000 if value > 10**11 else value, timezone.utc)
        else:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
    except (ValueError, OverflowError, OSError):
        return None


def pay_evidence(text: str) -> tuple[str, str | None]:
    if re.search(r"\bunpaid\b|unvergütet|unbezahlt", text, re.I):
        return "Unpaid", None
    period = r"(?:\s*(?:gross|net|brutto)?\s*(?:per|/|pro)\s*(?:hour|month|year|Stunde|Monat|Jahr))?"
    money_pattern = r"(?:€|EUR)\s*\d[\d.,]*(?:\s*[-–]\s*(?:€|EUR)?\s*\d[\d.,]*)?" + period + r"|\d[\d.,]*(?:\s*[-–]\s*\d[\d.,]*)?\s*(?:€|EUR)" + period
    money = None
    for candidate in re.finditer(money_pattern, text, re.I):
        context = text[max(0, candidate.start()-100):candidate.end()+60]
        if re.search(r"salary|compensation|remuneration|hourly|wage|gehalt|vergütung|stundenlohn|brutto|per hour|pro stunde|gross\s*(?:/|per)\s*(?:hour|month|year)", context, re.I):
            if not re.search(r"learning budget|training budget|referral|sign.on|reisebudget|weiterbildungsbudget", context, re.I):
                money = candidate
                break
    explicit = re.search(r"\bpaid (internship|position|role)\b|bezahlte[rsn]? (praktikum|stelle)|vergütete[rsn]? praktikum|hourly (pay|wage)|stundenlohn", text, re.I)
    return ("Confirmed paid" if money or explicit else "Unknown", money.group(0) if money else None)
