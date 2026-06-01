# CareerLens 🔍
> AI-powered job search co-pilot — semantic job matching, skill gap analysis, and LLM-powered application assistance

## Features
- 📄 **Smart Match** — Upload your resume, get ranked live job matches
- 📊 **Gap Analysis** — See which skills your top matches require that you're missing
- ✍️ **Application Assistant** — Rewrite your resume bullets and generate cover letters for any posting
- 🤝 **Warm Path Finder** — Surface postings with network overlap (shared school, company, city)

## Demo
*(coming soon)*

## Quick Start
```bash
git clone https://github.com/gatikyadav/careerlens.git
cd careerlens
pip install -r requirements.txt
cp .env.example .env
make run
```

## Tech Stack
`Python` · `LangChain` · `ChromaDB` · `sentence-transformers` · `pdfplumber` · `Streamlit` · `Adzuna API` · `SQLite`

## Project Structure
```
src/
├── ingestion/     # Adzuna API poller + SQLite storage
├── indexing/      # ChromaDB vector store
├── modules/       # Feature modules (matcher, gap analysis, etc.)
└── app.py         # Streamlit entry point
```