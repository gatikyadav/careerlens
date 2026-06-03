import re
import sqlite3
import requests
from src.ingestion.adzuna import DB_PATH
from src.ingestion.resume_parser import SKILL_KEYWORDS


# ── Seniority detection ───────────────────────────────────────────────────────
SENIOR_KEYWORDS = ["senior", "sr.", "lead", "principal", "staff", "distinguished",
                   "director", "vp", "head of", "manager"]
ENTRY_KEYWORDS = ["junior", "entry", "associate", "new grad", "intern",
                  "early career", "0-2 years", "1-2 years", "recent graduate"]

# ── Company type signals ──────────────────────────────────────────────────────
ENTERPRISE_COMPANIES = [
    "google", "meta", "amazon", "microsoft", "apple", "netflix", "ibm",
    "oracle", "salesforce", "intel", "nvidia", "qualcomm", "jpmorgan",
    "goldman sachs", "morgan stanley", "bloomberg", "capital one",
    "bank of america", "citigroup", "fidelity", "wells fargo",
]
STARTUP_SIGNALS = ["series a", "series b", "seed", "startup", "early stage",
                   "founded in 20", "we're a small", "fast-growing", "venture"]

# ── Wikipedia cache ───────────────────────────────────────────────────────────
_wiki_cache = {}


def extract_jd_skills(text: str) -> list[str]:
    """Extract skills from a job description using the same keyword list."""
    text_lower = text.lower()
    found = []
    for skill in SKILL_KEYWORDS:
        if len(skill) <= 3:
            pattern = r'\b' + re.escape(skill.lower()) + r'\b'
            if re.search(pattern, text_lower):
                found.append(skill)
        else:
            if skill.lower() in text_lower:
                found.append(skill)
    return found


def detect_seniority(title: str, description: str) -> str:
    """Return 'entry', 'mid', or 'senior' based on title and JD."""
    text = (title + " " + description[:500]).lower()
    if any(kw in text for kw in SENIOR_KEYWORDS):
        return "senior"
    if any(kw in text for kw in ENTRY_KEYWORDS):
        return "entry"
    return "mid"


def detect_company_type(company: str, description: str) -> str:
    """Return 'enterprise', 'startup', or 'unknown'."""
    text = (company + " " + description[:500]).lower()
    if any(c in text for c in ENTERPRISE_COMPANIES):
        return "enterprise"
    if any(s in text for s in STARTUP_SIGNALS):
        return "startup"
    return "unknown"


def extract_cities(text: str) -> list[str]:
    """Extract city names from text."""
    cities = [
        "new york", "san francisco", "seattle", "boston", "chicago",
        "austin", "los angeles", "denver", "atlanta", "miami",
        "washington", "philadelphia", "stony brook", "long island",
        "new jersey", "remote",
    ]
    text_lower = text.lower()
    return [city for city in cities if city in text_lower]


def extract_companies_from_resume(text: str) -> list[str]:
    """
    Dynamically extract company and organization names from resume text.
    Works for any resume, not just a hardcoded list.
    """
    all_companies = set()

    # Pattern 1: Known company suffixes
    suffix_pattern = re.findall(
        r'\b([A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)*)\s+(?:Inc|LLC|Corp|Ltd|Co|Group|Technologies|Solutions|Systems|Labs|Studio|Institute|Academy|University|College)\b',
        text
    )
    for name in suffix_pattern:
        all_companies.add(name.lower())

    # Pattern 2: Lines with date ranges are job entries — extract company name
    for line in text.split('\n'):
        line = line.strip()
        if re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|20\d\d)', line):
            match = re.match(r'^([A-Z][a-zA-Z\s&,\.]+?)(?:\s{2,}|\t|$)', line)
            if match:
                name = match.group(1).strip()
                if len(name) > 3:
                    all_companies.add(name.lower())

    # Pattern 3: Known hardcoded list as fallback
    known = [
        "google", "meta", "amazon", "microsoft", "apple", "netflix",
        "openai", "anthropic", "nvidia", "salesforce", "oracle", "ibm",
        "intel", "qualcomm", "linkedin", "uber", "airbnb", "stripe",
        "palantir", "databricks", "snowflake", "helmerich", "payne",
        "capital one", "jpmorgan", "goldman", "morgan stanley", "bloomberg",
        "two sigma", "citadel", "jane street",
    ]
    text_lower = text.lower()
    for c in known:
        if c in text_lower:
            all_companies.add(c)

    return list(all_companies)


def extract_universities_from_resume(text: str) -> list[str]:
    """
    Dynamically extract university names from resume text.
    Works for any school, not just a hardcoded list.
    """
    universities = set()

    # Pattern 1: "X University" or "X College" or "X Institute of Technology"
    uni_pattern = re.findall(
        r'\b([A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)*\s+(?:University|College|Institute of Technology|School of|Academy))\b',
        text
    )
    for u in uni_pattern:
        universities.add(u.lower())

    # Pattern 2: "University of X" format
    uni_of_pattern = re.findall(
        r'\b(University of [A-Z][a-zA-Z\s]+)\b',
        text
    )
    for u in uni_of_pattern:
        universities.add(u.lower().strip())

    # Pattern 3: Known abbreviations
    known_abbrevs = {
        "mit": "massachusetts institute of technology",
        "cmu": "carnegie mellon",
        "nyu": "new york university",
        "ucla": "university of california los angeles",
        "ucsd": "university of california san diego",
        "usc": "university of southern california",
    }
    text_lower = text.lower()
    for abbrev, full in known_abbrevs.items():
        if re.search(r'\b' + abbrev + r'\b', text_lower):
            universities.add(abbrev)
            universities.add(full)

    return list(universities)


def get_company_intel(company_name: str) -> dict:
    """
    Fetch basic company intel from Wikipedia API.
    Cached to avoid repeat calls.
    """
    if company_name in _wiki_cache:
        return _wiki_cache[company_name]

    try:
        search_url = "https://en.wikipedia.org/w/api.php"

        search_params = {
            "action": "query",
            "list": "search",
            "srsearch": company_name,
            "format": "json",
            "srlimit": 1,
        }
        resp = requests.get(search_url, params=search_params, timeout=5)
        results = resp.json().get("query", {}).get("search", [])

        if not results:
            _wiki_cache[company_name] = {"found": False}
            return {"found": False}

        page_title = results[0]["title"]
        extract_params = {
            "action": "query",
            "titles": page_title,
            "prop": "extracts",
            "exintro": True,
            "explaintext": True,
            "format": "json",
        }
        resp2 = requests.get(search_url, params=extract_params, timeout=5)
        pages = resp2.json().get("query", {}).get("pages", {})
        extract = next(iter(pages.values())).get("extract", "")

        if not extract:
            _wiki_cache[company_name] = {"found": False}
            return {"found": False}

        extract_lower = extract.lower()

        # Detect size
        if any(w in extract_lower for w in ["fortune 500", "multinational",
                                             "global company", "publicly traded",
                                             "nasdaq", "nyse"]):
            size = "large"
        elif any(w in extract_lower for w in ["startup", "founded in 20",
                                               "series a", "series b", "venture"]):
            size = "startup"
        else:
            size = "unknown"

        # Detect school mentions
        school_signals = []
        schools = ["stony brook", "mit", "stanford", "carnegie mellon",
                   "cornell", "columbia", "nyu", "georgia tech"]
        for school in schools:
            if school in extract_lower:
                school_signals.append(school)

        result = {
            "found": True,
            "title": page_title,
            "summary": extract[:300],
            "size": size,
            "school_signals": school_signals,
        }
        _wiki_cache[company_name] = result
        return result

    except Exception:
        _wiki_cache[company_name] = {"found": False}
        return {"found": False}


def extract_referral_signals(description: str) -> dict:
    """Extract referral and hiring manager signals from JD text."""
    text_lower = description.lower()
    signals = {}

    referral_phrases = [
        "employee referral", "referred by", "referral preferred",
        "referral bonus", "refer a friend", "internal referral",
    ]
    signals["referral_mentioned"] = any(p in text_lower for p in referral_phrases)

    direct_phrases = ["apply directly", "email your resume", "send resume to",
                      "contact us directly", "reach out to"]
    signals["direct_apply"] = any(p in text_lower for p in direct_phrases)

    email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", description)
    signals["contact_email"] = email_match.group(0) if email_match else None

    manager_match = re.search(
        r"(?:hiring manager|contact|recruiter|reach out to)[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)",
        description
    )
    signals["hiring_manager"] = manager_match.group(1) if manager_match else None

    urgent_phrases = ["immediate", "asap", "urgent", "start immediately",
                      "immediate opening", "immediate hire"]
    signals["urgent"] = any(p in text_lower for p in urgent_phrases)

    return signals


def score_warm_path(
    job: dict,
    resume_skills: list[str],
    resume_cities: list[str],
    resume_companies: list[str],
    resume_universities: list[str] = None,
    candidate_level: str = "entry",
    use_wiki: bool = False,
) -> dict:
    """Score a job by multiple warm path signals."""
    score = 0
    signals = []
    overlap_pct = 0

    title = job.get("title", "")
    company = job.get("company", "")
    location = job.get("location", "")
    description = job.get("description", "") or job.get("snippet", "")
    full_text = f"{title} {company} {description}".lower()

    # ── 1. Skill overlap ──────────────────────────────────────────────────────
    jd_skills = extract_jd_skills(description)
    if jd_skills:
        resume_lower = [s.lower() for s in resume_skills]
        matched_skills = [s for s in jd_skills if s.lower() in resume_lower]
        overlap_pct = round(len(matched_skills) / len(jd_skills) * 100, 1)
        if overlap_pct >= 50:
            score += 3
            signals.append(f"🎯 Strong skill match: {overlap_pct}% overlap ({len(matched_skills)}/{len(jd_skills)} skills)")
        elif overlap_pct >= 25:
            score += 2
            signals.append(f"🎯 Good skill match: {overlap_pct}% overlap ({len(matched_skills)}/{len(jd_skills)} skills)")
        elif overlap_pct >= 10:
            score += 1
            signals.append(f"🎯 Partial skill match: {overlap_pct}% overlap")

    # ── 2. Location overlap ───────────────────────────────────────────────────
    job_location = location.lower()
    for city in resume_cities:
        if city in job_location:
            score += 1
            signals.append(f"📍 Same city: {city.title()}")
            break

    # ── 3. Past company connection ────────────────────────────────────────────
    city_noise = {"new york", "new jersey", "san francisco", "los angeles",
                  "stony brook", "long island", "remote", "united states"}
    for rc in resume_companies:
        if len(rc) > 4 and rc not in city_noise and rc in full_text and rc not in company.lower():
            score += 2
            signals.append(f"🏢 Past company connection: {rc.title()}")
            break

    # ── 3b. University connection ─────────────────────────────────────────────
    for uni in (resume_universities or []):
        if len(uni) > 4 and uni in full_text:
            score += 2
            signals.append(f"🎓 University connection: {uni.title()}")
            break

    # ── 4. Seniority fit ──────────────────────────────────────────────────────
    seniority = detect_seniority(title, description)
    company_type = detect_company_type(company, description)

    if candidate_level == "entry" and seniority == "entry":
        score += 2
        signals.append("✅ Seniority fit: entry-level role matches your experience")
    elif candidate_level == "entry" and seniority == "mid":
        score += 1
        signals.append("⚡ Slight reach: mid-level role (good stretch opportunity)")
    elif candidate_level == "entry" and seniority == "senior":
        score -= 1
        signals.append("⚠️ Overqualified requirement: senior role may be hard to land")

    # ── 5. Company type ───────────────────────────────────────────────────────
    if company_type == "enterprise":
        signals.append("🏦 Enterprise company")
    elif company_type == "startup":
        signals.append("🚀 Startup")

    # ── 6. Remote friendly ────────────────────────────────────────────────────
    if "remote" in job_location or "remote" in description[:300].lower():
        score += 1
        signals.append("🌐 Remote friendly")

    # ── 7. Referral signals ───────────────────────────────────────────────────
    referral = extract_referral_signals(description)
    if referral["referral_mentioned"]:
        score += 2
        signals.append("🤝 Employee referral program mentioned")
    if referral["direct_apply"]:
        score += 1
        signals.append("📧 Direct application path available")
    if referral["contact_email"]:
        score += 1
        signals.append(f"📬 Contact email found: {referral['contact_email']}")
    if referral["hiring_manager"]:
        score += 1
        signals.append(f"👤 Hiring manager identified: {referral['hiring_manager']}")
    if referral["urgent"]:
        signals.append("⚡ Urgent hire — apply immediately")

    # ── 8. Wikipedia company intel (optional) ─────────────────────────────────
    if use_wiki and company:
        intel = get_company_intel(company)
        if intel.get("found"):
            if intel.get("size") == "large":
                signals.append(f"📊 Large/public company ({intel['title']})")
            elif intel.get("size") == "startup":
                signals.append(f"🚀 Confirmed startup ({intel['title']})")
            if intel.get("school_signals"):
                for school in intel["school_signals"]:
                    score += 2
                    signals.append(f"🎓 {school.title()} mentioned in company profile")

    return {
        "job_id": job.get("id", ""),
        "title": title,
        "company": company,
        "location": location,
        "url": job.get("url", ""),
        "warm_score": max(score, 0),
        "signals": signals,
        "seniority": seniority,
        "company_type": company_type,
        "skill_overlap_pct": overlap_pct,
        "snippet": description[:200],
        "referral_signals": referral,
    }


def find_warm_paths(
    resume_text: str,
    education: list[str],
    experience: list[str],
    matches: list[dict],
    resume_skills: list[str] = None,
    candidate_level: str = "entry",
    min_score: int = 1,
    use_wiki: bool = False,
) -> list[dict]:
    """Score all matched jobs by warm path signals."""
    full_text = resume_text + " ".join(education) + " ".join(experience)
    resume_cities = extract_cities(full_text)
    resume_companies = extract_companies_from_resume(full_text)
    resume_universities = extract_universities_from_resume(full_text)

    scored = []
    for job in matches:
        result = score_warm_path(
            job=job,
            resume_skills=resume_skills or [],
            resume_cities=resume_cities,
            resume_companies=resume_companies,
            resume_universities=resume_universities,
            candidate_level=candidate_level,
            use_wiki=use_wiki,
        )
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
        resume_skills=profile["skills"],
        candidate_level="entry",
        min_score=1,
        use_wiki=False,
    )

    print(f"\nFound {len(results)} warm path matches\n")
    for r in results[:10]:
        print(f"[Score: {r['warm_score']}] {r['title']} @ {r['company']} ({r['seniority']})")
        for s in r["signals"]:
            print(f"  {s}")
        print()