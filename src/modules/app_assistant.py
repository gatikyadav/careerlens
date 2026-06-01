import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def rewrite_resume_bullets(
    resume_experience: list[str],
    job_title: str,
    job_description: str,
    candidate_skills: list[str],
) -> list[str]:
    """
    Rewrite resume bullet points to better align with a target job posting.
    Returns a list of rewritten bullets.
    """
    skills_str = ", ".join(candidate_skills[:15])
    bullets_str = "\n".join([f"- {b}" for b in resume_experience])

    prompt = f"""You are an expert resume coach helping a candidate tailor their resume for a specific job.

TARGET ROLE: {job_title}

JOB DESCRIPTION:
{job_description[:1500]}

CANDIDATE'S CURRENT EXPERIENCE BULLETS:
{bullets_str}

CANDIDATE'S SKILLS: {skills_str}

TASK: Rewrite each bullet point to better align with the target role. 
- Mirror the language and keywords from the job description
- Keep the same achievements and metrics but reframe them for this role
- Make each bullet start with a strong action verb
- Keep bullets concise (1-2 lines each)
- Return ONLY the rewritten bullets, one per line, starting with •
- Do not add bullets that weren't in the original
- Preserve all quantified achievements (%, numbers, etc.)

REWRITTEN BULLETS:"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=600,
    )

    raw = response.choices[0].message.content.strip()
    bullets = [line.strip().lstrip("•").strip()
               for line in raw.split("\n") if line.strip()]
    return bullets


def generate_cover_letter(
    candidate_name: str,
    candidate_email: str,
    candidate_skills: list[str],
    candidate_experience: list[str],
    candidate_education: list[str],
    job_title: str,
    company: str,
    job_description: str,
) -> str:
    """
    Generate a tailored cover letter for a specific job posting.
    """
    skills_str = ", ".join(candidate_skills[:15])
    exp_str = "\n".join(candidate_experience[:5])
    edu_str = candidate_education[0] if candidate_education else ""

    prompt = f"""Write a professional, compelling cover letter for the following:

CANDIDATE: {candidate_name}
EMAIL: {candidate_email}
EDUCATION: {edu_str}
KEY SKILLS: {skills_str}
EXPERIENCE HIGHLIGHTS:
{exp_str}

TARGET ROLE: {job_title} at {company}

JOB DESCRIPTION:
{job_description[:1500]}

INSTRUCTIONS:
- Write exactly 3 paragraphs
- Paragraph 1: Strong opening hook that connects candidate's background to this specific role
- Paragraph 2: 2-3 specific achievements/experiences that directly match the JD requirements  
- Paragraph 3: Forward-looking close expressing genuine interest and next steps
- Use a professional but confident tone — not generic
- Mirror keywords from the job description naturally
- Do NOT include date, address headers, or sign-off — just the 3 paragraphs
- Keep it under 300 words total

COVER LETTER:"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=500,
    )

    return response.choices[0].message.content.strip()


if __name__ == "__main__":
    # Quick test
    test_bullets = [
        "Engineered full-stack ML pipelines for sensor data anomaly detection using NumPy and pandas, reducing false positives by 25%",
        "Developed LLM-powered PDF-to-JSON pipeline with OCR fallback using pdfplumber, boosting extraction accuracy by 40%",
        "Spearheaded automated code review system using Kimi K2, achieving 95% bug detection accuracy",
    ]

    test_skills = ["python", "machine learning", "llm", "pandas", "numpy", "git", "openai"]

    test_jd = """We are looking for a Machine Learning Engineer to join our team.
    You will build and deploy ML models at scale, work with large datasets,
    and collaborate with cross-functional teams. Requirements: Python, TensorFlow/PyTorch,
    MLOps experience, strong background in NLP and LLMs preferred."""

    print("Testing bullet rewriter...")
    bullets = rewrite_resume_bullets(
        resume_experience=test_bullets,
        job_title="Machine Learning Engineer",
        job_description=test_jd,
        candidate_skills=test_skills,
    )
    print("\nRewritten bullets:")
    for b in bullets:
        print(f"  • {b}")

    print("\nTesting cover letter generator...")
    letter = generate_cover_letter(
        candidate_name="Gatik Yadav",
        candidate_email="gatikyadav@gmail.com",
        candidate_skills=test_skills,
        candidate_experience=test_bullets,
        candidate_education=["Bachelor of Science in Computer Science, Stony Brook University"],
        job_title="Machine Learning Engineer",
        company="Acme Corp",
        job_description=test_jd,
    )
    print("\nCover letter:")
    print(letter)