import sqlite3
import re
from src.ingestion.adzuna import DB_PATH


def extract_universities(text: str) -> list[str]:
    """Extract university names from text using word boundaries."""
    universities = [
        "stony brook", "mit", "stanford", "harvard", "carnegie mellon",
        "cmu", "berkeley", "columbia", "cornell", "nyu", "princeton",
        "yale", "michigan", "georgia tech", "illinois", "purdue",
        "ucla", "uc san diego", "ucsd", "northeastern", "boston university",
        "rutgers", "penn state", "university of washington",
    ]
    text_lower = text.lower()
    found = []
    for uni in universities:
        # Use word boundary for short abbreviations
        if len(uni) <= 4:
            pattern = r'\b' + re.escape(uni) + r'\b'
            if re.search(pattern, text_lower):
                found.append(uni)
        else:
            if uni in text_lower:
                found.append(uni)
    return found


def extract_companies(text: str) -> list[str]:
    """Extract company names from text."""
    companies = [
        "google", "meta", "amazon", "microsoft", "apple", "netflix",
        "openai", "anthropic", "nvidia", "salesforce", "oracle",
        "ibm", "intel", "qualcomm", "linkedin", "twitter", "uber",
        "airbnb", "stripe", "palantir", "databricks", "snowflake",
        "helmerich", "payne", "capital one", "jpmorgan", "goldman",
        "morgan stanley", "bloomberg", "two sigma", "citadel", "jane street",
    ]
    text_lower = text.lower()
    found = []
    for company in companies:
        if company in text_lower:
            found.append(company)
    return found


def extract_cities(text: str) -> list[str]:
    """Extract city names from text."""
    cities = [
        "new york", "san francisco", "seattle", "boston", "chicago",
        "austin", "los angeles", "denver", "atlanta", "miami",
        "washington", "philadelphia", "stony brook", "long island",
    ]
    text_lower = text.lower()
    found = []
    for city in cities:
        if city in text_lower:
            found.append(city)
    return found


def build_candidate_profile(
    resume_text: str,
    education: list[str],
    experience: list[str],
) -> dict:
    """
    Extract network-relevant signals from resume.
    """
    full_text = resume_text + " ".join(education) + " ".join(experience)

    return {
        "universities": extract_universities(full_text),
        "companies": extract_companies(full_text),
        "cities": extract_cities(full_text),
    }


def score_warm_path(
    job: dict,
    candidate_profile: dict,
) -> dict:
    """
    Score a job posting by network proximity to the candidate.

    Scoring:
        +3  shared university in job description
        +2  past company mentioned in job description
        +1  shared city
        +1  shared tech stack (via query match)
    """
    score = 0
    signals = []

    job_text = f"{job.get('title', '')} {job.get('company', '')} {job.get('description', '')} {job.get('location', '')}".lower()

    # University overlap
    for uni in candidate_profile["universities"]:
        if uni in job_text:
            score += 3
            signals.append(f"🎓 Shared university: {uni.title()}")

    # Past company overlap
    for company in candidate_profile["companies"]:
        if company in job_text:
            score += 2
            signals.append(f"🏢 Past company connection: {company.title()}")

    # City overlap
    for city in candidate_profile["cities"]:
        if city in job.get("location", "").lower():
            score += 1
            signals.append(f"📍 Same city: {city.title()}")

    # Tech stack overlap via query
    if job.get("query", "").lower() in ["machine learning engineer", "ai engineer", "data scientist"]:
        score += 1
        signals.append("🔧 Strong tech stack alignment")

    return {
        "job_id": job.get("id", ""),
        "title": job.get("title", ""),
        "company": job.get("company", ""),
        "location": job.get("location", ""),
        "url": job.get("url", ""),
        "warm_score": score,
        "signals": signals,
        "snippet": job.get("description", "")[:200],
    }


def find_warm_paths(
    resume_text: str,
    education: list[str],
    experience: list[str],
    matches: list[dict],
    min_score: int = 1,
) -> list[dict]:
    """
    Given a list of job matches, score each by warm path signals.
    Returns jobs sorted by warm score, filtered to min_score.
    """
    candidate_profile = build_candidate_profile(
        resume_text=resume_text,
        education=education,
        experience=experience,
    )

    scored = []
    for job in matches:
        result = score_warm_path(job, candidate_profile)
        if result["warm_score"] >= min_score:
            scored.append(result)

    return sorted(scored, key=lambda x: x["warm_score"], reverse=True)


if __name__ == "__main__":
    from src.ingestion.adzuna import get_all_jobs
    from src.ingestion.resume_parser import parse_resume
    import sys

    pdf_path = sys.argv[1] if len(sys.argv) > 1 else None
    if not pdf_path:
        print("Usage: python -m src.modules.warm_path <resume.pdf>")
        sys.exit(1)

    profile = parse_resume(pdf_path)
    jobs = get_all_jobs()[:50]

    results = find_warm_paths(
        resume_text=profile["raw_text"],
        education=profile["education"],
        experience=profile["experience"],
        matches=jobs,
        min_score=1,
    )

    print(f"\nFound {len(results)} warm path matches\n")
    for r in results:
        print(f"[Score: {r['warm_score']}] {r['title']} @ {r['company']}")
        for s in r["signals"]:
            print(f"  {s}")
        print()