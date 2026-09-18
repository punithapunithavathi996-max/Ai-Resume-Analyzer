# AI Resume Analyzer

A full-stack web app that analyzes a resume against a chosen job role and gives
an AI-style match score, missing-skill breakdown, resume-quality feedback, and
personalized course/certification recommendations.

**Stack:** Python (Flask) backend + HTML/CSS/JavaScript frontend.

## Features
- Upload resume as **PDF, DOCX, or TXT**
- Choose from 10 built-in job roles (Data Scientist, Web Developer, Software
  Engineer, Data Analyst, DevOps Engineer, UI/UX Designer, Product Manager,
  ML Engineer, Digital Marketing Specialist, Cybersecurity Analyst)
- Match score (%) based on required skills detected in the resume
- List of matched vs. missing skills (core + "nice to have")
- Resume-quality checks: length, contact info, quantified achievements,
  action verbs, section structure
- Personalized recommendations: a suggested course/resource for every missing
  skill

## How it works
1. The Flask backend (`app.py`) extracts raw text from the uploaded file using
   `pdfplumber` (PDF) or `python-docx` (DOCX), or reads it directly (TXT).
2. It compares the resume text against a skill profile defined in
   `job_roles.json` for the selected role.
3. Rule-based heuristics score resume quality (numbers found, action verbs,
   section headers, contact info, word count).
4. The frontend (`templates/index.html`, `static/css/style.css`,
   `static/js/script.js`) sends the file via `fetch()`/`FormData` to the
   `/analyze` endpoint and renders the JSON response as a score ring, tag
   lists, and recommendation cards.

## Setup

```bash
cd ai-resume-analyzer
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open **http://127.0.0.1:5000** in your browser.

## Project structure
```
ai-resume-analyzer/
├── app.py                 # Flask backend + analysis logic
├── job_roles.json         # Skill database per job role + learning resources
├── requirements.txt
├── templates/
│   └── index.html
└── static/
    ├── css/style.css
    └── js/script.js
```

## Extending it
- Add more job roles / skills by editing `job_roles.json` — no code changes
  needed.
- Swap the rule-based skill matching in `app.py` for an actual LLM call (e.g.
  the Anthropic API) if you want free-text, context-aware suggestions instead
  of keyword matching — the `/analyze` route is the place to plug that in.
- Add a resume-rewrite feature that sends the extracted text + missing skills
  to an LLM to generate suggested bullet-point rewrites.
