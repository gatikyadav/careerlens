import requests
import sqlite3
import json
import os
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

APP_ID = os.getenv("ADZUNA_APP_ID")
API_KEY = os.getenv("ADZUNA_API_KEY")
DB_PATH = "data/jobs.db"
BASE_URL = "https://api.adzuna.com/v1/api/jobs/us/search"

SEARCH_QUERIES = [
    "machine learning engineer",
    "software engineer",
    "data scientist",
    "AI engineer",
    "backend engineer",
    "quantitative analyst",
]


def init_db():
    """Create the jobs table if it doesn't exist."""
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            title TEXT,
            company TEXT,
            location TEXT,
            description TEXT,
            salary_min REAL,
            salary_max REAL,
            url TEXT,
            query TEXT,
            created TEXT,
            fetched_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def fetch_jobs(query: str, results_per_page: int = 20, page: int = 1) -> list[dict]:
    """Fetch jobs from Adzuna API for a given query."""
    params = {
        "app_id": APP_ID,
        "app_key": API_KEY,
        "results_per_page": results_per_page,
        "what": query,
        "content-type": "application/json",
    }

    response = requests.get(
        f"{BASE_URL}/{page}",
        params=params,
        timeout=10,
    )

    if response.status_code != 200:
        print(f"  Error {response.status_code} for query '{query}': {response.text[:200]}")
        return []

    data = response.json()
    return data.get("results", [])


def save_jobs(jobs: list[dict], query: str):
    """Save a list of job results to SQLite, skipping duplicates."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    saved = 0

    for job in jobs:
        job_id = job.get("id", "")
        if not job_id:
            continue

        location = job.get("location", {})
        location_str = ", ".join(location.get("area", [])) if location else ""

        try:
            cursor.execute("""
                INSERT OR IGNORE INTO jobs
                (id, title, company, location, description, salary_min, salary_max, url, query, created, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_id,
                job.get("title", ""),
                job.get("company", {}).get("display_name", ""),
                location_str,
                job.get("description", ""),
                job.get("salary_min"),
                job.get("salary_max"),
                job.get("redirect_url", ""),
                query,
                job.get("created", ""),
                datetime.utcnow().isoformat(),
            ))
            saved += 1
        except sqlite3.Error as e:
            print(f"  DB error for job {job_id}: {e}")

    conn.commit()
    conn.close()
    return saved


def run_pipeline(queries: list[str] = None):
    """Main pipeline — fetch and store jobs for all queries."""
    if queries is None:
        queries = SEARCH_QUERIES

    init_db()
    total_saved = 0

    print(f"\n{'='*50}")
    print(f"Adzuna Pipeline — {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*50}")

    for query in queries:
        print(f"\nFetching: '{query}'...")
        jobs = fetch_jobs(query, results_per_page=20)
        if jobs:
            saved = save_jobs(jobs, query)
            total_saved += saved
            print(f"  Fetched {len(jobs)} → saved {saved} new")
        else:
            print(f"  No results returned")
        time.sleep(1)  # be polite to the API

    print(f"\n{'='*50}")
    print(f"Done. Total new jobs saved: {total_saved}")
    print(f"{'='*50}\n")


def get_all_jobs() -> list[dict]:
    """Return all jobs from the database as a list of dicts."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs ORDER BY fetched_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_job_count() -> int:
    """Return total number of jobs in the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM jobs")
    count = cursor.fetchone()[0]
    conn.close()
    return count


if __name__ == "__main__":
    run_pipeline()
    print(f"Total jobs in DB: {get_job_count()}")