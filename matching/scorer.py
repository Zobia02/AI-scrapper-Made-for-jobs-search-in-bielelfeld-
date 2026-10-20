import re
from datetime import datetime, timezone

from matching.extraction import cities_in, contains, parse_date, skills_in
from matching.language_detection import ENGLISH, NO_GERMAN, OPTIONAL, REQUIRED, UNKNOWN, sentences
from matching.profile import Profile


def score_job(job: dict, profile: Profile, now=None) -> dict:
    now = now or datetime.now(timezone.utc)
    text = job["description"]
    advertised = set(job.get("skills", []))
    available = set(skills_in(" ; ".join(profile.skills))) | set(profile.skills)
    matched, missing = sorted(advertised & available), sorted(advertised - available)
    obstacles, reasons, evidence = [], [], {}
    components = {"skills": round(100 * len(matched) / len(advertised), 1) if advertised else 0}
    if matched:
        reasons.append("Your profile overlaps with " + ", ".join(matched[:6]) + ".")
    else:
        obstacles.append("No recognized skill overlap; review the original description.")
    evidence["skills"] = [s for s in sentences(text) if any(contains(s, x) for x in matched)][:4]
    title_tokens = set(re.findall(r"[a-z0-9+#.]+", job["title"].lower()))
    stop = {"student", "working", "werkstudent", "intern", "internship", "m", "f", "d", "w", "the", "and", "of"}
    best = 0
    for role in profile.roles:
        tokens = set(re.findall(r"[a-z0-9+#.]+", role.lower())) - stop
        if tokens:
            best = max(best, len(tokens & title_tokens) / len(tokens))
    components["role"] = round(best * 100, 1)
    evidence["role"] = [job["title"]]
    if best:
        reasons.append("Title overlaps with your preferred roles.")
    language = job.get("language", UNKNOWN)
    components["language"] = {ENGLISH: 100, NO_GERMAN: 45, OPTIONAL: 65, REQUIRED: 0, UNKNOWN: 0}[language]
    if profile.english.strip().lower() in {"", "unknown", "none", "not stated"}:
        components["language"] = 0
        obstacles.append("Your English proficiency is unknown; confirm it in the profile.")
    elif re.fullmatch(r"A[12]", profile.english.strip(), re.I):
        components["language"] = min(components["language"], 20)
        obstacles.append("Your stated English level may be below the role's communication needs.")
    if language == REQUIRED and profile.german in {"B2", "C1", "C2", "Native"}:
        components["language"] = 55  # Exact required level still needs manual verification.
    if language != ENGLISH:
        obstacles.append({
            REQUIRED: f"German is required; your profile says {profile.german}. Verify the exact level.",
            OPTIONAL: "German is preferred; English sufficiency still needs checking.",
            NO_GERMAN: "No explicit German requirement found; this is not proof that English is sufficient.",
            UNKNOWN: "Language requirements are unknown or ambiguous.",
        }[language])
    evidence["language"] = job.get("language_evidence", [])
    requirement_lines = [s for s in sentences(text) if re.search(
        r"enroll|student|studier|immatrik|bachelor|master|ph\.?d|years?.{0,25}experience|\d.{0,15}jahre", s, re.I)]
    components["experience"] = 0
    if requirement_lines:
        joined = " ".join(requirement_lines)
        if re.search(r"\b[3-9]\+?\s*(years?|jahre)|\bph\.?d\b|doctorate|promotion", joined, re.I):
            components["experience"] = 20
            obstacles.append("Possible advanced-degree or multi-year experience requirement; inspect the evidence.")
        elif profile.student and re.search(r"student|enroll|studier|immatrik|bachelor|master", joined, re.I):
            components["experience"] = 85
            reasons.append("The listing mentions student or degree requirements relevant to your profile; exact eligibility needs review.")
        else:
            obstacles.append("Experience/education compatibility needs manual review.")
    else:
        obstacles.append("Experience/education requirements unknown.")
    evidence["experience"] = requirement_lines[:4]
    job_cities = set(job.get("cities", []))
    preferred = set(cities_in("; ".join(profile.locations))) | set(profile.locations)
    components["location"] = 100 if job_cities & preferred else 60
    evidence["location"] = [job["location"]]
    dt = parse_date(job.get("posted_at"))
    if dt and dt <= now:
        days = max(0, (now - dt).total_seconds() / 86400)
        components["recency"] = round(max(0, 100 * (1 - days / 30)), 1)
    else:
        components["recency"] = 0
        obstacles.append("Posting date unknown or in the future; discovery date does not count as posting recency.")
    evidence["recency"] = [job.get("posted_at") or "Unknown"]
    if job.get("paid") != "Confirmed paid":
        obstacles.append("Compensation is " + job.get("paid", "Unknown").lower() + "; confirm payment with the employer.")
    if job.get("authorization"):
        obstacles.append("Work-authorization wording is present; review it before applying.")
    if missing:
        obstacles.append("Advertised skills absent from your profile: " + ", ".join(missing[:8]) + ".")
    project_advice = []
    if set(matched) & {"RAG", "Azure OpenAI", "LLM", "Azure AI Search"} and re.search(r"rag|chatbot|azure openai", profile.experience, re.I):
        project_advice.append("Mention your Azure OpenAI chatbot: embeddings, retrieval quality and RAG evaluation.")
    if set(matched) & {"Angular", "C#", "ASP.NET Core", "React"} and re.search(r"angular|\.net|full.stack", profile.experience, re.I):
        project_advice.append("Discuss your Angular/.NET or full-stack project and explain your own implementation decisions.")
    total = round(sum(components[k] * profile.weights[k] / 100 for k in components), 1)
    return dict(score=total, components=components, matched=matched, missing=missing,
                reasons=reasons, obstacles=obstacles, evidence=evidence,
                advice={"emphasize": matched[:8], "projects": project_advice,
                        "learn": missing[:5], "interview": (matched[:4] + missing[:2])})
