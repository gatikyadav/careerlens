---
title: CareerLens
emoji: 🔍
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
---

# CareerLens 🔍
> AI-powered job search co-pilot — semantic job matching, skill gap analysis, and LLM-powered application assistance

**🚀 [Live Demo](https://huggingface.co/spaces/gayadav/careerlens)**  &nbsp;|&nbsp; **⭐ [GitHub](https://github.com/gatikyadav/careerlens)**

---

## What It Does

CareerLens takes your resume PDF and puts it to work. Upload once and get four tools instantly:

**📄 Smart Match** — Semantic search over 1,000+ live job postings using sentence-transformers embeddings and ChromaDB vector search. Matches are ranked by cosine similarity against your actual skills and experience, not just keyword overlap.

**📊 Skill Gap Analysis** — Extracts skill demand signals across your top matches and compares them against your resume. Shows you exactly which skills appear in what percentage of postings you're missing, with interactive bar charts.

**✍️ Application Assistant** — Select any matched job and get your resume bullets rewritten to mirror the JD's language, plus a tailored 3-paragraph cover letter. Powered by GPT-4o-mini.

**🤝 Warm Path Finder** — Scores each posting by network proximity: skill overlap %, seniority fit, location match, past company connections, university mentions, referral signals, and direct contact info extracted from JD text.

---

## Demo

![CareerLens Demo](assets/demo.gif)

---

## Architecture

```
PDF Resume Upload
      ↓
pdfplumber parser → structured profile (name, email, skills, experience, education)
      ↓
Sentence-Transformers embeddings → ChromaDB vector search
      ↓
┌─────────────────────────────────────────┐
│  Smart Match  │  Gap Analysis           │
│  App Assistant│  Warm Path Finder       │
└─────────────────────────────────────────┘
      ↓
Streamlit UI → deployed on HuggingFace Spaces
```

**Data pipeline:** Adzuna API → SQLite → ChromaDB (runs on every deploy, fetches fresh postings)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Resume parsing | pdfplumber |
| Job data | Adzuna API |
| Vector DB | ChromaDB |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| LLM | GPT-4o-mini via OpenAI API |
| Database | SQLite |
| UI | Streamlit |
| Deployment | HuggingFace Spaces (Docker) |
| CI/CD | GitHub Actions |

---

## Local Setup

```bash
git clone https://github.com/gatikyadav/careerlens.git
cd careerlens
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Fill in ADZUNA_APP_ID, ADZUNA_API_KEY, OPENAI_API_KEY in .env
python src/ingestion/adzuna.py        # fetch jobs
python -m src.indexing.vector_store   # build index
streamlit run src/app.py              # launch app
```

---

## Project Structure

```
src/
├── ingestion/
│   ├── adzuna.py          # Adzuna API poller + SQLite storage
│   └── resume_parser.py   # PDF resume parser
├── indexing/
│   └── vector_store.py    # ChromaDB vector index + semantic search
├── modules/
│   ├── matcher.py         # Resume-to-job matching
│   ├── gap_analysis.py    # Skill gap analysis
│   ├── app_assistant.py   # LLM bullet rewriter + cover letter
│   └── warm_path.py       # Network proximity scoring
└── app.py                 # Streamlit UI
tests/
└── test_parser.py         # Unit tests (CI/CD via GitHub Actions)
```

---

## API Keys Required

- **Adzuna** — free tier at [developer.adzuna.com](https://developer.adzuna.com)
- **OpenAI** — GPT-4o-mini at [platform.openai.com](https://platform.openai.com)

---

## Author

**Gatik Yadav** — CS + Applied Math & Statistics @ Stony Brook University  
[LinkedIn](https://linkedin.com/in/gatikyadav) · [GitHub](https://github.com/gatikyadav)