import pdfplumber
import re
import json


SKILL_KEYWORDS = [
    # Languages
    "python", "java", "c++", "c", "javascript", "typescript", "r", "sql",
    "html", "css", "matlab", "scala", "go", "rust", "swift", "kotlin",
    "mips", "flutter",
    # ML / AI
    "machine learning", "deep learning", "nlp", "computer vision",
    "tensorflow", "keras", "pytorch", "scikit-learn", "xgboost",
    "langchain", "rag", "llm", "openai", "huggingface", "transformers",
    "artificial intelligence", "retrieval augmented generation",
    "convolutional neural network", "cnn",
    # Data
    "pandas", "numpy", "matplotlib", "plotly", "spark", "hadoop",
    "tableau", "power bi", "pdfplumber",
    # Backend / Infra
    "fastapi", "flask", "django", "springboot", "nodejs",
    "docker", "kubernetes", "aws", "gcp", "azure", "git",
    "postgresql", "mysql", "mongodb", "redis", "sqlite",
    "android studio", "fusion 360",
    # Other
    "streamlit", "rest api", "graphql", "ci/cd", "linux",
    "ocr", "prompt engineering",
]

# Lines that are clearly bullet content, not titles
NOISE_PATTERNS = [
    r"^●", r"^•", r"^-", r"^\d+\.",   # bullet characters
    r"improving|developing|building|leading|managing|utilizing",
    r"enhancing|achieving|reducing|increasing|designing",
]


def extract_text(pdf_path: str) -> str:
    """Extract raw text from a PDF file."""
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text


def extract_email(text: str) -> str:
    match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    return match.group(0) if match else ""


def extract_phone(text: str) -> str:
    # Handle hyphens, en-dashes, em-dashes, and spaces in phone numbers
    match = re.search(
        r"\(?\d{3}\)?[\s\-\.\u2013\u2014]+\d{3}[\s\-\.\u2013\u2014]+\d{4}",
        text
    )
    return match.group(0).strip() if match else ""


def extract_skills(text: str) -> list[str]:
    """Match skills from keyword list against resume text."""
    text_lower = text.lower()
    found = []
    for skill in SKILL_KEYWORDS:
        if skill.lower() in text_lower:
            found.append(skill)
    return sorted(set(found))


def extract_education(text: str) -> list[str]:
    """Extract lines that look like education entries."""
    edu_keywords = ["university", "college", "bachelor", "master", "b.s", "m.s",
                    "b.a", "m.a", "ph.d", "associate", "institute of technology"]
    lines = text.split("\n")
    edu_lines = []
    for line in lines:
        if any(kw in line.lower() for kw in edu_keywords):
            cleaned = line.strip()
            if cleaned:
                edu_lines.append(cleaned)
    return edu_lines


def is_noise_line(line: str) -> bool:
    """Return True if the line is a bullet point or filler, not a title."""
    for pattern in NOISE_PATTERNS:
        if re.search(pattern, line.strip(), re.IGNORECASE):
            return True
    return False


def extract_experience(text: str) -> list[str]:
    """Extract job titles and company names only — no bullet content."""
    exp_keywords = ["intern", "engineer", "developer", "analyst", "scientist",
                    "manager", "researcher", "assistant", "lead", "architect",
                    "founder", "consultant", "director", "officer"]
    lines = text.split("\n")
    exp_lines = []
    for line in lines:
        cleaned = line.strip()
        if not cleaned or len(cleaned) < 8:
            continue
        if is_noise_line(cleaned):
            continue
        if any(kw in cleaned.lower() for kw in exp_keywords):
            exp_lines.append(cleaned)
    return exp_lines[:10]


def extract_name(text: str) -> str:
    """First non-empty line is usually the candidate's name."""
    for line in text.split("\n"):
        cleaned = line.strip()
        if cleaned:
            return cleaned
    return ""


def parse_resume(pdf_path: str) -> dict:
    """
    Main function — takes a PDF path, returns a structured profile dict.
    """
    text = extract_text(pdf_path)

    profile = {
        "raw_text": text,
        "name": extract_name(text),
        "email": extract_email(text),
        "phone": extract_phone(text),
        "skills": extract_skills(text),
        "education": extract_education(text),
        "experience": extract_experience(text),
    }
    return profile


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python resume_parser.py <path_to_resume.pdf>")
        sys.exit(1)

    path = sys.argv[1]
    profile = parse_resume(path)

    print("\n===== PARSED RESUME PROFILE =====")
    print(f"Name:   {profile['name']}")
    print(f"Email:  {profile['email']}")
    print(f"Phone:  {profile['phone']}")
    print(f"\nSkills ({len(profile['skills'])}):")
    for s in profile['skills']:
        print(f"  - {s}")
    print(f"\nEducation:")
    for e in profile['education']:
        print(f"  - {e}")
    print(f"\nExperience:")
    for ex in profile['experience']:
        print(f"  - {ex}")
    print("\n===== RAW TEXT PREVIEW (first 300 chars) =====")
    print(profile['raw_text'][:300])
