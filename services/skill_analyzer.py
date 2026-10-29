import re

from services.job_catalog import JOB_ROLES
from services.learning_recommender import build_learning_plan

SKILLS = {
    "Programming languages": ["python", "java", "javascript", "typescript", "c++", "c#", "php", "go", "ruby"],
    "Web and frameworks": ["html", "css", "react", "node.js", "flask", "django", "express", "bootstrap"],
    "Data and databases": ["sql", "mysql", "postgresql", "mongodb", "pandas", "excel", "statistics"],
    "Cloud and systems": ["cloud", "aws", "azure", "linux", "networking", "docker", "kubernetes"],
    "Tools and quality": ["git", "github", "testing", "selenium", "api design", "scikit-learn"],
    "Methods and domain": ["machine learning", "data visualization", "security", "problem solving", "communication", "leadership", "teamwork"],
}


def _contains(text, phrase):
    pattern = r"(?<![a-z0-9+#])" + re.escape(phrase.lower()) + r"(?![a-z0-9+#])"
    return re.search(pattern, text.lower()) is not None


def detect_skills(text):
    detected = []
    lower = text.lower()
    for category, skills in SKILLS.items():
        for skill in skills:
            match = re.search(
                r"(?<![a-z0-9+#])" + re.escape(skill.lower()) + r"(?![a-z0-9+#])",
                lower,
            )
            if match:
                context = lower[max(0, match.start() - 100):match.end() + 100]
                supported = re.search(
                    r"\b(project|built|developed|implemented|designed|created|"
                    r"used|using|experience|internship|deployed|analyzed|tested)\b",
                    context,
                )
                evidence = (
                    "Nearby project or experience wording; verify the specific contribution."
                    if supported
                    else "Mentioned without nearby project or experience evidence."
                )
                detected.append({
                    "name": skill,
                    "category": category,
                    "evidence": evidence,
                    "evidence_level": "supported" if supported else "mentioned",
                })
    return detected


def _quality_score(text, skills):
    lower = text.lower()
    sections = {
        "Skills relevance": (30, min(30, len(skills) * 4), "Skills found by keyword matching; relevant skills should be supported by truthful examples."),
        "Projects and experience": (25, 20 if "project" in lower and ("experience" in lower or "intern" in lower) else 13 if "project" in lower or "experience" in lower or "intern" in lower else 5, "A project or experience section makes applied work easier to evaluate."),
        "Education and certifications": (15, 15 if "education" in lower and "certification" in lower else 10 if "education" in lower or "certification" in lower else 3, "Add education and certifications only when applicable and accurate."),
        "Achievements": (15, 15 if re.search(r"\b\d+%|\b\d+\+|\b\d+\s+(users|customers|projects|hours)\b", lower) else 6 if "achievement" in lower else 3, "Quantified impact can add context; use only metrics you can verify."),
        "Structure and readability": (15, 15 if len(text.splitlines()) >= 8 and len(text.split()) >= 150 else 9 if len(text.split()) >= 80 else 4, "A clear, extractable structure helps readers and text-based screening tools."),
    }
    return {
        "score": round(sum(item[1] for item in sections.values())),
        "maximum": 100,
        "criteria": [{"name": name, "weight": weight, "score": score, "feedback": feedback} for name, (weight, score, feedback) in sections.items()],
        "method": "Heuristic guidance score, not a hiring score or ATS simulation.",
    }


def _match_score(skills, required):
    have = {skill["name"] for skill in skills}
    covered = [name for name in required if name in have]
    score = round(100 * len(covered) / len(required)) if required else 0
    return score, covered


def _suggestions(text):
    lower = text.lower()
    suggestions = []
    checks = [
        ("Contact details", any(token in lower for token in ["email", "@", "phone", "linkedin"])),
        ("Education", "education" in lower),
        ("Projects", "project" in lower),
        ("Skills", "skills" in lower),
        ("Experience or internship", "experience" in lower or "intern" in lower),
    ]
    for section, present in checks:
        if not present:
            suggestions.append({
                "issue": f"{section} section was not detected",
                "why": "This section is commonly useful, depending on your experience and target role.",
                "recommendation": f"Add a concise {section.lower()} section if it applies to you.",
                "example": "",
            })
    if re.search(r"\bseeking (a |an )?(challenging|opportunity|position)", lower):
        suggestions.append({
            "issue": "The objective statement may be generic",
            "why": "Broad objective wording uses space without showing role-specific evidence.",
            "recommendation": "Replace it with a short profile focused on demonstrated strengths and the target role.",
            "example": "Example format: Student with experience in [verified area], demonstrated through [project or internship].",
        })
    if "project" in lower and not re.search(r"\b(improved|reduced|increased|automated|implemented|built|developed)\b", lower):
        suggestions.append({
            "issue": "Project contribution may need more detail",
            "why": "Readers need to understand what you personally built and which tools you used.",
            "recommendation": "Describe your action, the tools you used, and a verifiable outcome.",
            "example": "Built [feature] using [tools]; add a verified result or use a placeholder such as [measured outcome].",
        })
    if len(text.split()) < 80:
        suggestions.append({
            "issue": "The extracted resume text is brief",
            "why": "A short or incomplete document can hide useful qualifications and make analysis less reliable.",
            "recommendation": "Check that the uploaded file contains selectable text and include relevant education, projects, and experience.",
            "example": "",
        })
    if not re.search(r"\b(20\d{2}|19\d{2})\b", text):
        suggestions.append({
            "issue": "No year or date was detected",
            "why": "Dates help readers understand the timing of education, projects, and experience.",
            "recommendation": "Add accurate dates to relevant entries using a consistent format.",
            "example": "Example format: Project name — Jan 2025 to Apr 2025.",
        })
    return suggestions


def analyze_resume(text, target_role="", career_field="", job_description=""):
    skills = detect_skills(text)
    normalized_role = target_role.strip().lower()
    selected_job = next((role for role in JOB_ROLES if role["title"].lower() == normalized_role), None)
    if not selected_job and career_field:
        selected_job = next((role for role in JOB_ROLES if role["field"] == career_field), None)

    recommendations = []
    for role in JOB_ROLES:
        score, covered = _match_score(skills, role["skills"])
        if career_field and role["field"] != career_field:
            score = max(0, score - 10)
        recommendations.append({
            "title": role["title"],
            "match": score,
            "demonstrated_skills": covered,
            "missing_skills": [skill for skill in role["skills"] if skill not in covered],
            "reason": f"{len(covered)} of {len(role['skills'])} catalogue skills were detected in the resume text.",
            "entry_level": True,
            "next_step": f"Choose one {role['title']} skill gap and build a small project before listing it as a skill.",
        })
    recommendations.sort(key=lambda role: (-role["match"], role["title"]))

    missing = []
    job_match = None
    required = selected_job["skills"] if selected_job else []
    if job_description.strip():
        jd_skills = [name for group in SKILLS.values() for name in group if _contains(job_description, name)]
        if jd_skills:
            required = list(dict.fromkeys(jd_skills))
    if required:
        have = {skill["name"] for skill in skills}
        for index, skill in enumerate(required):
            if skill not in have:
                priority = "High priority" if index < 2 else "Medium priority" if index < 5 else "Optional"
                missing.append({
                    "skill": skill,
                    "priority": priority,
                    "why": f"{skill.title()} is included in the selected role or job-description comparison.",
                    "note": "Not evidenced in this resume text; this does not establish that you lack the skill.",
                })
        covered = [skill for skill in required if skill in have]
        job_match = {
            "score": round(100 * len(covered) / len(required)),
            "covered": covered,
            "required_count": len(required),
            "method": "Detected required-skill coverage only; this is not a hiring probability.",
        }

    summary = "Rule-based analysis found " + (
        f"{len(skills)} skills or skill keywords in the supplied text."
        if skills else "no catalogue skill keywords in the supplied text."
    )
    if selected_job:
        summary += f" A catalogue comparison was prepared for {selected_job['title']}."
    if len(text.split()) < 100:
        summary += " The resume text is short, so the results may be incomplete."

    return {
        "summary": summary,
        "skills": skills,
        "skill_categories": {category: [item["name"] for item in skills if item["category"] == category] for category in SKILLS},
        "quality": _quality_score(text, skills),
        "job_match": job_match,
        "recommendations": recommendations[:5],
        "missing_skills": missing,
        "learning_plan": build_learning_plan([item["skill"] for item in missing if item["priority"] != "Optional"]),
        "improvements": _suggestions(text),
        "ats_checklist": [
            {"label": "Text can be extracted from the document", "passed": len(text.strip()) >= 30},
            {"label": "Common resume sections are present", "passed": sum("section was not detected" not in item["issue"] for item in _suggestions(text)) >= 3},
            {"label": "Resume includes project or experience evidence", "passed": "project" in text.lower() or "experience" in text.lower()},
            {"label": "Use a simple, readable layout and verify dates/links", "passed": False},
        ],
        "limitations": [
            "Keyword detection cannot verify actual proficiency or establish that a candidate lacks a skill.",
            "Career recommendations use the local role catalogue, not live job listings.",
            "Scores are guidance heuristics, not an ATS simulation or hiring probability.",
        ],
    }
