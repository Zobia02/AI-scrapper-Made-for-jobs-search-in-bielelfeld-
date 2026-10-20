"""Conservative rules: evidence is quoted; missing information is not confirmation."""
import re
from dataclasses import dataclass

ENGLISH = "Confirmed English-only or English-sufficient"
NO_GERMAN = "No explicit German requirement found"
OPTIONAL = "German preferred but optional"
REQUIRED = "German required"
UNKNOWN = "Unknown"
LANGUAGES = [ENGLISH, NO_GERMAN, OPTIONAL, REQUIRED, UNKNOWN]


@dataclass
class LanguageAssessment:
    label: str
    evidence: list[str]


def sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"[\n;!?]+|(?<=[.])\s+(?=[A-ZÄÖÜ])", text) if s.strip()]


def assess_language(text: str) -> LanguageAssessment:
    if len(text.strip()) < 80:
        return LanguageAssessment(UNKNOWN, [])
    german, optional, english, ambiguous, other_required = [], [], [], [], []
    for sentence in sentences(text):
        s = sentence.lower()
        if re.search(r"\b(german|deutsch\w*)\b", s):
            if re.search(r"(no|without).{0,25}german|german.{0,35}(not required|not necessary)|kein\w*.{0,20}deutsch|deutsch.{0,35}nicht (erforderlich|notwendig)", s):
                english.append(sentence)
            elif re.search(r"(?:german|deutsch\w*)[^,;.!?\n]{0,65}(?:optional|nice.to.have|is a plus|are a plus|bonus|preferred|von vorteil|wünschenswert)|(?:idealerweise|optional)[^,;.!?\n]{0,35}(?:german|deutsch)", s) and not re.search(r"(?:german|deutsch\w*)[^,;.!?\n]{0,30}(?:required|must|erforderlich|zwingend)", s):
                optional.append(sentence)
            elif re.search(r"required|must|fluent|fluency|proficien|native|excellent|good|strong|command|speak|sprachig|[bc][12]|verhandlungssicher|fließend|fliessend|gute|kenntnisse|beherrsch|erforderlich|voraussetz|zwingend", s):
                german.append(sentence)
            else:
                ambiguous.append(sentence)
        if re.search(r"english|englisch", s) and re.search(
            r"fluent|fluency|proficien|excellent|good|strong|working language|company language|business language|communication|command|speak|[bc][12]|verhandlungssicher|fließend|kenntnisse|arbeitssprache", s
        ):
            english.append(sentence)
        if re.search(r"\b(russian|french|spanish|dutch|italian|polish|chinese|arabic|russisch|französisch)\b", s):
            if re.search(r"fluent|fluency|required|must|proficien|native|verhandlungssicher|fließend", s) and not re.search(r"optional|a plus|preferred|von vorteil", s):
                other_required.append(sentence)
    # Explicit mandatory German wins over English and optional statements elsewhere.
    if german:
        return LanguageAssessment(REQUIRED, german[:3])
    if optional:
        return LanguageAssessment(OPTIONAL, optional[:3])
    if other_required:
        return LanguageAssessment(UNKNOWN, other_required[:3])
    if ambiguous:
        return LanguageAssessment(UNKNOWN, ambiguous[:3])
    if english:
        return LanguageAssessment(ENGLISH, english[:3])
    return LanguageAssessment(NO_GERMAN, [])
