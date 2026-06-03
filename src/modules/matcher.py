from src.ingestion.resume_parser import parse_resume
from src.indexing.vector_store import search_jobs


def build_resume_query(profile: dict) -> str:
    """
    Convert a parsed resume profile into a search query string
    that captures the candidate's skills and experience.
    """
    parts = []

    # Lead with target role intent based on strongest signals
    ml_skills = {"machine learning", "tensorflow", "keras", "pytorch",
                 "llm", "rag", "openai", "artificial intelligence",
                 "convolutional neural network", "deep learning"}
    has_ml = any(s in ml_skills for s in profile.get("skills", []))

    if has_ml:
        parts.append("Machine Learning Engineer AI Python")

    # Add top ML/AI skills only — exclude generic ones like java, c, html
    noise_skills = {"c", "html", "css", "mips", "flutter", "android studio",
                    "fusion 360", "scala", "go", "matlab", "r", "javascript"}
    clean_skills = [s for s in profile.get("skills", [])
                    if s not in noise_skills][:10]

    if clean_skills:
        parts.append(", ".join(clean_skills))

    # Add experience lines
    if profile.get("experience"):
        exp_str = " | ".join(profile["experience"][:2])
        parts.append(f"Experience: {exp_str}")

    return ". ".join(parts)


def match_jobs(pdf_path: str, n_results: int = 10, filters: dict = None) -> dict:
    """
    Main matching function.
    Takes a resume PDF path, returns ranked job matches.
    """
    # Step 1: Parse resume
    print("Parsing resume...")
    profile = parse_resume(pdf_path)

    if not profile:
        return {"error": "Failed to parse resume", "matches": []}

    # Step 2: Build search query from profile
    query = build_resume_query(profile)
    print(f"Search query built ({len(query)} chars)")

    # Step 3: Search vector index — fetch more to account for deduplication
    print("Searching job index...")
    matches = search_jobs(query, n_results=50)

    # Step 4: Deduplicate by company + title
    seen = set()
    deduped = []
    for m in matches:
        key = f"{m['company'].lower()}|{m['title'].lower()}"
        if key not in seen:
            seen.add(key)
            deduped.append(m)
    matches = deduped

    # Step 5: Apply filters if provided
    if filters:
        if filters.get("query_type"):
            term = filters["query_type"].lower()
            matches = [m for m in matches if term in m["title"].lower()
                      or term in m["query"].lower()]

        if filters.get("location"):
            loc = filters["location"].lower()
            matches = [m for m in matches if loc in m["location"].lower()]

    # Trim to requested number
    matches = matches[:n_results]

    return {
        "profile": {
            "name": profile.get("name", ""),
            "email": profile.get("email", ""),
            "skills": profile.get("skills", []),
            "education": profile.get("education", []),
            "experience": profile.get("experience", []),
        },
        "query_used": query,
        "total_matches": len(matches),
        "matches": matches,
    }


if __name__ == "__main__":
    import sys

    pdf_path = sys.argv[1] if len(sys.argv) > 1 else None

    if not pdf_path:
        print("Usage: python -m src.modules.matcher <path_to_resume.pdf>")
        sys.exit(1)

    result = match_jobs(pdf_path, n_results=10)

    print(f"\n{'='*55}")
    print(f"Matches for: {result['profile']['name']}")
    print(f"Skills detected: {', '.join(result['profile']['skills'][:8])}...")
    print(f"{'='*55}")

    for i, job in enumerate(result["matches"], 1):
        print(f"\n#{i} [{job['score']}] {job['title']}")
        print(f"    {job['company']} — {job['location']}")
        print(f"    {job['url']}")