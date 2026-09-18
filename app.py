"""
AI Resume Analyzer
-------------------
A Flask backend that:
  1. Accepts an uploaded resume (PDF, DOCX, or TXT)
  2. Extracts and cleans the text
  3. Compares it against a required-skill profile for a chosen job role
  4. Scores the match, flags missing skills, checks resume "quality" heuristics
     (quantified achievements, action verbs, length, contact info, etc.)
  5. Returns tailored recommendations (courses / certifications / writing tips)

Run:
    pip install -r requirements.txt
    python app.py
Then open http://127.0.0.1:5000
"""

import io
import json
import os
import re

from flask import Flask, jsonify, render_template, request

import docx
import pdfplumber

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(BASE_DIR, "job_roles.json"), "r", encoding="utf-8") as f:
    JOB_ROLES = json.load(f)

ACTION_VERBS = [
    "led", "built", "developed", "designed", "implemented", "managed", "created",
    "improved", "increased", "reduced", "launched", "optimized", "automated",
    "architected", "delivered", "achieved", "streamlined", "spearheaded",
    "coordinated", "analyzed", "engineered", "deployed", "mentored"
]

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_REGEX = re.compile(r"(\+?\d[\d\-\s()]{8,}\d)")
NUMBER_REGEX = re.compile(r"\b\d+(\.\d+)?%?\b")


def extract_text_from_pdf(file_stream):
    text = []
    with pdfplumber.open(file_stream) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text.append(page_text)
    return "\n".join(text)


def extract_text_from_docx(file_stream):
    document = docx.Document(file_stream)
    return "\n".join(p.text for p in document.paragraphs)


def extract_text(file_storage):
    filename = file_storage.filename.lower()
    stream = io.BytesIO(file_storage.read())

    if filename.endswith(".pdf"):
        return extract_text_from_pdf(stream)
    elif filename.endswith(".docx"):
        return extract_text_from_docx(stream)
    elif filename.endswith(".txt"):
        return stream.read().decode("utf-8", errors="ignore")
    else:
        raise ValueError("Unsupported file type. Please upload a PDF, DOCX, or TXT file.")


def find_skill_matches(resume_text_lower, skills):
    matched, missing = [], []
    for skill in skills:
        # word-boundary-ish match so "r" doesn't match everywhere, etc.
        pattern = r"(?<![a-zA-Z0-9])" + re.escape(skill.lower()) + r"(?![a-zA-Z0-9])"
        if re.search(pattern, resume_text_lower):
            matched.append(skill)
        else:
            missing.append(skill)
    return matched, missing


def analyze_resume_quality(raw_text):
    """Heuristic, rule-based resume-writing quality checks."""
    checks = []
    word_count = len(raw_text.split())
    lower = raw_text.lower()

    # Length
    if word_count < 150:
        checks.append({"label": "Length", "status": "warning",
                        "message": f"Resume looks short ({word_count} words). Consider adding more detail on projects and achievements."})
    elif word_count > 1200:
        checks.append({"label": "Length", "status": "warning",
                        "message": f"Resume is quite long ({word_count} words). Aim for 1-2 pages of focused content."})
    else:
        checks.append({"label": "Length", "status": "good",
                        "message": f"Resume length looks reasonable ({word_count} words)."})

    # Contact info
    has_email = bool(EMAIL_REGEX.search(raw_text))
    has_phone = bool(PHONE_REGEX.search(raw_text))
    if has_email and has_phone:
        checks.append({"label": "Contact Info", "status": "good", "message": "Email and phone number detected."})
    else:
        missing_bits = []
        if not has_email:
            missing_bits.append("email")
        if not has_phone:
            missing_bits.append("phone number")
        checks.append({"label": "Contact Info", "status": "warning",
                        "message": f"Could not detect: {', '.join(missing_bits)}. Make sure contact details are clearly visible."})

    # Quantified achievements
    numbers_found = len(NUMBER_REGEX.findall(raw_text))
    if numbers_found >= 3:
        checks.append({"label": "Quantified Impact", "status": "good",
                        "message": f"Found {numbers_found} numeric/quantified results — good use of metrics."})
    else:
        checks.append({"label": "Quantified Impact", "status": "warning",
                        "message": "Few or no numbers detected. Try quantifying achievements (e.g., 'reduced load time by 30%')."})

    # Action verbs
    verbs_used = [v for v in ACTION_VERBS if re.search(r"\b" + v + r"\b", lower)]
    if len(verbs_used) >= 5:
        checks.append({"label": "Action Verbs", "status": "good",
                        "message": f"Strong use of action verbs ({', '.join(verbs_used[:6])}...)."})
    else:
        checks.append({"label": "Action Verbs", "status": "warning",
                        "message": "Try starting bullet points with strong action verbs like 'led', 'built', 'improved', 'automated'."})

    # Sections
    section_keywords = ["experience", "education", "skills", "projects", "summary"]
    found_sections = [s for s in section_keywords if s in lower]
    if len(found_sections) >= 3:
        checks.append({"label": "Structure", "status": "good",
                        "message": f"Detected common sections: {', '.join(found_sections)}."})
    else:
        checks.append({"label": "Structure", "status": "warning",
                        "message": "Consider adding clear section headers: Summary, Experience, Education, Skills, Projects."})

    return checks


@app.route("/")
def index():
    return render_template("index.html", job_roles=sorted(JOB_ROLES.keys()))


@app.route("/analyze", methods=["POST"])
def analyze():
    if "resume" not in request.files:
        return jsonify({"error": "No resume file uploaded."}), 400

    job_role = request.form.get("job_role")
    if not job_role or job_role not in JOB_ROLES:
        return jsonify({"error": "Please select a valid job role."}), 400

    resume_file = request.files["resume"]
    try:
        raw_text = extract_text(resume_file)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    if not raw_text.strip():
        return jsonify({"error": "Could not extract any text from this file."}), 400

    lower_text = raw_text.lower()
    role_profile = JOB_ROLES[job_role]

    matched_required, missing_required = find_skill_matches(lower_text, role_profile["required_skills"])
    matched_nice, missing_nice = find_skill_matches(lower_text, role_profile.get("nice_to_have", []))

    total_required = len(role_profile["required_skills"])
    score = round((len(matched_required) / total_required) * 100) if total_required else 0

    quality_checks = analyze_resume_quality(raw_text)

    resources = role_profile.get("resources", {})
    recommendations = [
        {"skill": skill, "resource": resources.get(skill, "Search for an intro course on this topic.")}
        for skill in missing_required
    ]
    stretch_recommendations = [
        {"skill": skill, "resource": resources.get(skill, "Search for an intro course on this topic.")}
        for skill in missing_nice
    ]

    if score >= 80:
        verdict = "Strong match! Your resume already covers most of the core skills for this role."
    elif score >= 50:
        verdict = "Decent match — filling a few skill gaps could meaningfully strengthen your application."
    else:
        verdict = "Significant gaps detected for this role. Focus on the missing core skills below before applying."

    return jsonify({
        "job_role": job_role,
        "score": score,
        "verdict": verdict,
        "matched_required": matched_required,
        "missing_required": missing_required,
        "matched_nice_to_have": matched_nice,
        "missing_nice_to_have": missing_nice,
        "recommendations": recommendations,
        "stretch_recommendations": stretch_recommendations,
        "quality_checks": quality_checks,
        "word_count": len(raw_text.split()),
    })


@app.route("/job-roles")
def job_roles():
    return jsonify(sorted(JOB_ROLES.keys()))


if __name__ == "__main__":
    app.run(debug=True)
