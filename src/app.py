import streamlit as st
import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.modules.matcher import match_jobs
from src.indexing.vector_store import build_index, get_collection

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CareerLens",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 800;
        color: #1E3A5F;
        margin-bottom: 0;
    }
    .sub-header {
        font-size: 1rem;
        color: #64748B;
        margin-bottom: 2rem;
    }
    .match-card {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.75rem;
    }
    .score-badge {
        background: #2563EB;
        color: white;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .skill-tag {
        background: #EFF6FF;
        color: #1D4ED8;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.8rem;
        margin-right: 4px;
        display: inline-block;
    }
    .section-title {
        font-size: 1.2rem;
        font-weight: 700;
        color: #1E3A5F;
        border-bottom: 2px solid #2563EB;
        padding-bottom: 4px;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔍 CareerLens")
    st.markdown("---")

    st.markdown("### Upload Resume")
    uploaded_file = st.file_uploader(
        "Drop your resume PDF here",
        type=["pdf"],
        help="Your resume is parsed locally and never stored"
    )

    st.markdown("### Filters")
    role_filter = st.text_input(
        "Role type",
        placeholder="e.g. machine learning",
        help="Filter matches by job title keyword"
    )
    location_filter = st.text_input(
        "Location",
        placeholder="e.g. New York",
        help="Filter by city or state"
    )
    n_results = st.slider("Number of results", 5, 20, 10)

    st.markdown("---")

    # DB stats
    try:
        collection = get_collection()
        job_count = collection.count()
        st.markdown(f"**Jobs in index:** {job_count}")
    except Exception:
        st.markdown("**Jobs in index:** —")

    if st.button("🔄 Refresh Job Index", use_container_width=True):
        with st.spinner("Re-indexing jobs..."):
            build_index()
        st.success("Index refreshed!")


# ── Main content ──────────────────────────────────────────────────────────────
st.markdown('<p class="main-header">🔍 CareerLens</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">AI-powered job search co-pilot — upload your resume to get started</p>',
            unsafe_allow_html=True)

if not uploaded_file:
    # Landing state
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("📄 **Smart Match**\n\nUpload your resume and get ranked job matches based on your actual skills and experience")
    with col2:
        st.info("📊 **Gap Analysis**\n\nSee which skills your top matches require that you're currently missing")
    with col3:
        st.info("✍️ **Application Assistant**\n\nGet your resume bullets rewritten and cover letters drafted for any posting")
    st.markdown("---")
    st.markdown("#### 👈 Upload your resume PDF in the sidebar to get started")

else:
    # Save uploaded file to a temp location
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name

    # Run matching
    with st.spinner("Parsing resume and finding matches..."):
        filters = {}
        if role_filter:
            filters["query_type"] = role_filter
        if location_filter:
            filters["location"] = location_filter

        result = match_jobs(tmp_path, n_results=n_results, filters=filters)

    # Clean up temp file
    os.unlink(tmp_path)

    if "error" in result:
        st.error(f"Error: {result['error']}")
    else:
        profile = result["profile"]
        matches = result["matches"]

        # ── Profile summary ──
        st.markdown('<p class="section-title">Your Profile</p>', unsafe_allow_html=True)
        col1, col2 = st.columns([1, 2])

        with col1:
            st.markdown(f"**Name:** {profile['name']}")
            st.markdown(f"**Email:** {profile['email']}")
            st.markdown(f"**Skills detected:** {len(profile['skills'])}")

        with col2:
            st.markdown("**Skills:**")
            skills_html = " ".join(
                [f'<span class="skill-tag">{s}</span>' for s in profile["skills"]]
            )
            st.markdown(skills_html, unsafe_allow_html=True)

        st.markdown("---")

        # ── Match results ──
        st.markdown(f'<p class="section-title">Top {len(matches)} Job Matches</p>',
                    unsafe_allow_html=True)

        if not matches:
            st.warning("No matches found. Try adjusting your filters.")
        else:
            for i, job in enumerate(matches, 1):
                score_pct = int(job["score"] * 100)
                score_color = "#16A34A" if score_pct >= 50 else "#D97706" if score_pct >= 40 else "#DC2626"

                with st.container():
                    col1, col2 = st.columns([5, 1])
                    with col1:
                        st.markdown(f"**#{i} {job['title']}**")
                        st.markdown(f"🏢 {job['company']}  &nbsp; 📍 {job['location']}")
                        st.markdown(f"_{job['snippet'][:180]}..._")
                        st.markdown(f"[View Job →]({job['url']})")
                    with col2:
                        st.markdown(
                            f"<div style='text-align:center; padding-top:10px;'>"
                            f"<span style='font-size:1.5rem; font-weight:800; color:{score_color}'>"
                            f"{score_pct}%</span><br>"
                            f"<span style='font-size:0.75rem; color:#64748B'>match</span>"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                    st.markdown("---")