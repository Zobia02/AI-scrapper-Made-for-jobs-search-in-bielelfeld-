from pydantic import BaseModel, Field, model_validator

WEIGHTS = {"skills": 35, "role": 20, "language": 20, "experience": 10, "location": 10, "recency": 5}


class Profile(BaseModel):
    name: str = "AI master's student"
    skills: list[str] = Field(default_factory=lambda: [
        "Python", "C#", "JavaScript", "TypeScript", "Angular", "React", "Next.js",
        "ASP.NET Core", "Entity Framework", "Flask", "Machine Learning", "Deep Learning",
        "NLP", "Generative AI", "LLM", "RAG", "Azure OpenAI", "Azure AI Search", "Azure",
        "PyTorch", "TensorFlow", "Keras", "REST API", "SQL", "Git", "GitHub", "CI/CD", "Docker",
    ])
    roles: list[str] = Field(default_factory=lambda: [
        "AI Engineer", "Generative AI Engineer", "Machine Learning Engineer", "NLP Engineer",
        "LLM Engineer", "Software Engineer", "Software Developer", "Python Developer",
        "Full Stack Developer", "Frontend Developer", "Backend Developer",
        "Cloud Engineer", "DevOps Engineer", "Research Assistant", "HiWi",
    ])
    locations: list[str] = Field(default_factory=lambda: [
        "Bielefeld", "Düsseldorf", "Cologne", "Dortmund", "Münster", "Hamburg",
        "Berlin", "Munich", "Stuttgart", "Frankfurt",
    ])
    english: str = "IELTS Academic 6.5"
    german: str = "A1"
    student: bool = True
    education: str = (
        "M.Sc. Artificial Intelligence, University of Bologna, Italy (2025–2027); "
        "Erasmus, Bielefeld University, Germany (2026–2027); "
        "B.E. Computer Systems Engineering, NED University, Pakistan (2020–2024), CGPA 3.896/4.00."
    )
    experience: str = (
        "Frontend Software Engineer Trainee; Angular and .NET development; "
        "AI chatbot with Azure OpenAI, embeddings, vector/hybrid retrieval and RAG; full-stack projects."
    )
    weights: dict[str, int] = Field(default_factory=lambda: WEIGHTS.copy())

    @model_validator(mode="after")
    def valid_weights(self):
        if set(self.weights) != set(WEIGHTS) or sum(self.weights.values()) != 100:
            raise ValueError("The six matching weights must add up to 100.")
        if any(v < 0 or v > 100 for v in self.weights.values()):
            raise ValueError("Weights must be between 0 and 100.")
        return self
