import chromadb
import os
import sqlite3
from sentence_transformers import SentenceTransformer
from src.ingestion.adzuna import get_all_jobs
from src.ingestion.adzuna import DB_PATH

CHROMA_PATH = "chroma_db"
COLLECTION_NAME = "job_postings"

# Load the embedding model once at module level
print("Loading embedding model...")
model = SentenceTransformer("all-MiniLM-L6-v2")
print("Model loaded.")


def get_chroma_client():
    """Return a persistent ChromaDB client."""
    return chromadb.PersistentClient(path=CHROMA_PATH)


def get_collection():
    """Return the job postings collection."""
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def embed_text(text: str) -> list[float]:
    """Embed a single string using sentence-transformers."""
    return model.encode(text, normalize_embeddings=True).tolist()


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a list of strings in batch."""
    return model.encode(texts, normalize_embeddings=True).tolist()


def build_index():
    """
    Fetch all jobs from SQLite and index them into ChromaDB.
    Skips jobs already in the index.
    """
    collection = get_collection()
    jobs = get_all_jobs()

    if not jobs:
        print("No jobs found in database. Run the Adzuna pipeline first.")
        return

    # Get already-indexed IDs
    existing = collection.get(include=[])
    existing_ids = set(existing["ids"])

    new_jobs = [j for j in jobs if j["id"] not in existing_ids]

    if not new_jobs:
        print(f"All {len(jobs)} jobs already indexed.")
        return

    print(f"Indexing {len(new_jobs)} new jobs...")

    # Build text to embed: title + company + description
    texts = []
    ids = []
    metadatas = []

    for job in new_jobs:
        text = f"{job['title']} at {job['company']}. {job['description']}"
        texts.append(text[:1000])  # cap at 1000 chars for speed
        ids.append(job["id"])
        metadatas.append({
            "title": job["title"] or "",
            "company": job["company"] or "",
            "location": job["location"] or "",
            "url": job["url"] or "",
            "query": job["query"] or "",
            "salary_min": str(job["salary_min"] or ""),
            "salary_max": str(job["salary_max"] or ""),
        })

    # Embed in batches of 32
    batch_size = 32
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        embeddings = embed_batch(batch)
        all_embeddings.extend(embeddings)
        print(f"  Embedded {min(i + batch_size, len(texts))}/{len(texts)}")

    collection.add(
        ids=ids,
        embeddings=all_embeddings,
        documents=texts,
        metadatas=metadatas,
    )

    print(f"Done. Total jobs in index: {collection.count()}")


def search_jobs(query_text: str, n_results: int = 10) -> list[dict]:
    """
    Search for jobs similar to a query string.
    Returns a list of matches with metadata, similarity score, and full description.
    """
    collection = get_collection()

    if collection.count() == 0:
        print("Index is empty. Run build_index() first.")
        return []

    query_embedding = embed_text(query_text)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["metadatas", "distances", "documents"],
    )

    # Fetch full descriptions from SQLite
    ids = results["ids"][0]
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    placeholders = ",".join("?" * len(ids))
    cursor.execute(f"SELECT id, description FROM jobs WHERE id IN ({placeholders})", ids)
    desc_map = {row["id"]: row["description"] for row in cursor.fetchall()}
    conn.close()

    matches = []
    for i in range(len(ids)):
        job_id = ids[i]
        full_desc = desc_map.get(job_id, "")
        match = {
            "id": job_id,
            "score": round(1 - results["distances"][0][i], 3),
            "title": results["metadatas"][0][i]["title"],
            "company": results["metadatas"][0][i]["company"],
            "location": results["metadatas"][0][i]["location"],
            "url": results["metadatas"][0][i]["url"],
            "query": results["metadatas"][0][i]["query"],
            "snippet": full_desc[:200],
            "description": full_desc,
        }
        matches.append(match)

    return sorted(matches, key=lambda x: x["score"], reverse=True)


if __name__ == "__main__":
    build_index()