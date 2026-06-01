import pytest
from src.ingestion.resume_parser import (
    extract_email,
    extract_phone,
    extract_skills,
    extract_name,
)

SAMPLE_TEXT = """Gatik Yadav
Stony Brook, New York | gatikyadav@gmail.com | (631) 676 – 0537 | LinkedIn
EDUCATION
Stony Brook University Stony Brook, New York
Bachelor of Science in Computer Science
TECHNICAL SKILLS
Python, Java, Machine Learning, TensorFlow, pandas, Git
"""

def test_extract_name():
    assert extract_name(SAMPLE_TEXT) == "Gatik Yadav"

def test_extract_email():
    assert extract_email(SAMPLE_TEXT) == "gatikyadav@gmail.com"

def test_extract_phone():
    assert extract_phone(SAMPLE_TEXT) == "(631) 676 – 0537"

def test_extract_skills():
    skills = extract_skills(SAMPLE_TEXT)
    assert "python" in skills
    assert "java" in skills
    assert "machine learning" in skills
    assert "tensorflow" in skills
    assert "pandas" in skills
    assert "git" in skills

def test_extract_skills_case_insensitive():
    skills = extract_skills("Expert in PYTHON and PyTorch")
    assert "python" in skills
    assert "pytorch" in skills