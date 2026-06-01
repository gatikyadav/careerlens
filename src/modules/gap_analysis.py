import sqlite3
import re
from collections import Counter
from src.ingestion.adzuna import DB_PATH
from src.ingestion.resume_parser import SKILL_KEYWORDS


def extract_skills_from_text(text: str) -> list[str]:
    """Extract skill keywords from a job description using word boundaries."""
    text_lower = text.lower()
    found = []
    for skill in SKILL_KEYWORDS:
        # Use word boundary for short/common terms to avoid false matches
        if len(skill) <= 3 or skill in ["scala", "rust", "go"]:
            pattern = r'\b' + re.escape(skill.lower()) + r'\b'
            if re.search(pattern, text_lower):
                found.append(skill)
        else:
            if skill.lower() in text_lower:
                found.append(skill)
    return found


def get_top_job_descriptions(job_ids: list[str] = None, limit: int = 100) -> list[str]:
    """
    Fetch job descriptions from SQLite.
    If job_ids provided, fetch only those. Otherwise fetch most recent.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if job_ids:
        placeholders = ",".join("?" * len(job_ids))
        cursor.execute(
            f"SELECT description FROM jobs WHERE id IN ({placeholders})",
            job_ids
        )
    else:
        cursor.execute(
            "SELECT description FROM jobs ORDER BY fetched_at DESC LIMIT ?",
            (limit,)
        )

    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows if r[0]]


def run_gap_analysis(
    resume_skills: list[str],
    job_ids: list[str] = None,
    top_n: int = 15,
) -> dict:
    """
    Compare resume skills against skills demanded in job postings.

    Returns:
        gaps: skills in postings not on resume, ranked by frequency
        covered: skills on resume that also appear in postings
        all_skill_counts: full frequency dict of all skills in postings
        coverage_pct: % of top demanded skills already on resume
    """
    descriptions = get_top_job_descriptions(job_ids=job_ids, limit=100)

    if not descriptions:
        return {
            "gaps": [],
            "covered": [],
            "all_skill_counts": {},
            "coverage_pct": 0,
            "total_postings_analyzed": 0,
        }

    # Count skill frequency across all postings
    skill_counter = Counter()
    for desc in descriptions:
        skills_in_desc = extract_skills_from_text(desc)
        for skill in skills_in_desc:
            skill_counter[skill] += 1

    total_postings = len(descriptions)
    resume_skills_lower = [s.lower() for s in resume_skills]

    # Split into gaps and covered
    gaps = []
    covered = []

    for skill, count in skill_counter.most_common(top_n * 2):
        freq_pct = round((count / total_postings) * 100, 1)
        entry = {
            "skill": skill,
            "count": count,
            "frequency_pct": freq_pct,
        }
        if skill.lower() in resume_skills_lower:
            covered.append(entry)
        else:
            gaps.append(entry)

    # Coverage score: what % of top-N demanded skills are on resume
    top_demanded = [s for s, _ in skill_counter.most_common(top_n)]
    covered_count = sum(1 for s in top_demanded if s.lower() in resume_skills_lower)
    coverage_pct = round((covered_count / len(top_demanded)) * 100, 1) if top_demanded else 0

    return {
        "gaps": gaps[:top_n],
        "covered": covered[:top_n],
        "all_skill_counts": dict(skill_counter.most_common(30)),
        "coverage_pct": coverage_pct,
        "total_postings_analyzed": total_postings,
    }


if __name__ == "__main__":
    # Quick test
    sample_skills = ["python", "machine learning", "pandas", "git", "tensorflow"]
    result = run_gap_analysis(sample_skills)

    print(f"\nAnalyzed {result['total_postings_analyzed']} postings")
    print(f"Coverage score: {result['coverage_pct']}%")

    print(f"\n--- TOP SKILL GAPS ---")
    for g in result["gaps"][:10]:
        print(f"  {g['skill']:<30} {g['frequency_pct']}% of postings")

    print(f"\n--- SKILLS YOU HAVE ---")
    for c in result["covered"][:10]:
        print(f"  {c['skill']:<30} {c['frequency_pct']}% of postings")