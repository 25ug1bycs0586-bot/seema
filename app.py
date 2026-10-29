from datetime import datetime, timezone
from io import BytesIO
import os
from urllib.parse import urlparse
from xml.sax.saxutils import escape

from flask import Flask, flash, jsonify, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required, login_user, logout_user
from flask_wtf.csrf import CSRFError
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from werkzeug.utils import secure_filename

from config import Config, ensure_instance_directory
from extensions import csrf, db, limiter, login_manager
from models import Analysis, LearningTask, User
from services.ai_service import enrich_with_ai
from services.job_catalog import JOB_ROLES
from services.resume_parser import ResumeParseError, extract_resume_text
from services.skill_analyzer import analyze_resume

ALLOWED_EXTENSIONS = {"pdf", "docx"}
CAREER_FIELDS = [
    ("software_development", "Software development"),
    ("data_analytics", "Data analytics"),
    ("web_development", "Web development"),
    ("cybersecurity", "Cybersecurity"),
    ("cloud_computing", "Cloud computing"),
]


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    ensure_instance_directory(app)
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "login"
    login_manager.login_message = "Sign in to access your private reports."
    csrf.init_app(app)
    limiter.init_app(app)

    @app.after_request
    def set_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Cache-Control", "no-store")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self' https://cdn.jsdelivr.net https://fonts.googleapis.com 'unsafe-inline'; "
            "script-src 'self' https://cdn.jsdelivr.net https://cdn.jsdelivr.net/npm/chart.js; "
            "font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; "
            "object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'",
        )
        return response

    @app.context_processor
    def inject_navigation():
        return {"now_year": datetime.now(timezone.utc).year}

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.get("/")
    def dashboard():
        if not current_user.is_authenticated:
            return render_template("landing.html")
        recent = Analysis.query.filter_by(user_id=current_user.id).order_by(Analysis.created_at.desc()).limit(5).all()
        count = Analysis.query.filter_by(user_id=current_user.id).count()
        return render_template("dashboard.html", analyses=recent, analysis_count=count)

    @app.route("/register", methods=["GET", "POST"])
    @limiter.limit("5 per hour", methods=["POST"])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            if len(name) < 2 or len(name) > 120 or len(password) < 10 or len(password) > 128:
                flash("Enter a name and a password between 10 and 128 characters.", "error")
            elif "@" not in email or len(email) > 254:
                flash("Enter a valid email address.", "error")
            elif User.query.filter_by(email=email).first():
                flash("An account already uses that email address.", "error")
            else:
                user = User(name=name, email=email)
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                login_user(user)
                flash("Your account is ready. Upload a resume to begin.", "success")
                return redirect(url_for("dashboard"))
        return render_template("auth.html", mode="register")

    @app.route("/login", methods=["GET", "POST"])
    @limiter.limit("10 per 15 minutes", methods=["POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            user = User.query.filter_by(email=email).first()
            if not user or not user.check_password(password):
                flash("Email or password is incorrect.", "error")
            else:
                login_user(user, remember=request.form.get("remember") == "on")
                next_url = request.args.get("next", "")
                parsed_next = urlparse(next_url)
                if parsed_next.scheme or parsed_next.netloc or not next_url.startswith("/") or next_url.startswith("//"):
                    next_url = url_for("dashboard")
                return redirect(next_url)
        return render_template("auth.html", mode="login")

    @app.post("/logout")
    @login_required
    def logout():
        logout_user()
        flash("You have been signed out.", "success")
        return redirect(url_for("login"))

    @app.route("/analyze", methods=["GET", "POST"])
    @login_required
    @limiter.limit("20 per hour", methods=["POST"])
    def analyze():
        if request.method == "GET":
            return render_template(
                "upload.html",
                jobs=JOB_ROLES,
                career_fields=CAREER_FIELDS,
                max_upload_mb=app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024),
            )
        resume_text = request.form.get("resume_text", "").strip()
        upload = request.files.get("resume_file")
        if upload and upload.filename:
            filename = secure_filename(upload.filename)
            extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            if extension not in ALLOWED_EXTENSIONS:
                flash("Upload a PDF or DOCX file, or paste your resume text.", "error")
                return redirect(url_for("analyze"))
            try:
                resume_text = extract_resume_text(filename, upload.read(app.config["MAX_CONTENT_LENGTH"] + 1))
            except ResumeParseError as error:
                flash(str(error), "error")
                return redirect(url_for("analyze"))
        if not resume_text:
            flash("Upload a PDF/DOCX resume or paste resume text before analyzing.", "error")
            return redirect(url_for("analyze"))
        if len(resume_text) > 100_000:
            flash("Resume text is too long. Keep pasted text under 100,000 characters.", "error")
            return redirect(url_for("analyze"))
        target_role = request.form.get("target_role", "").strip()[:120]
        career_field = request.form.get("career_field", "").strip()
        job_description = request.form.get("job_description", "").strip()[:20_000]
        allowed_fields = {value for value, _label in CAREER_FIELDS}
        allowed_roles = {role["title"] for role in JOB_ROLES}
        if target_role and target_role not in allowed_roles:
            flash("Choose a target role from the list.", "error")
            return redirect(url_for("analyze"))
        if career_field not in allowed_fields and career_field:
            flash("Choose a career field from the list.", "error")
            return redirect(url_for("analyze"))

        report = analyze_resume(resume_text, target_role, career_field, job_description)
        report, mode, warning = enrich_with_ai(
            resume_text, report, app.config.get("OPENAI_API_KEY"), app.config.get("OPENAI_MODEL")
        )
        analysis = Analysis(
            user_id=current_user.id,
            target_role=target_role,
            career_field=career_field,
            job_description=job_description,
            report_json=report,
            analyzer_mode=mode,
        )
        db.session.add(analysis)
        db.session.flush()
        for phase in report["learning_plan"]:
            for task in phase["tasks"]:
                db.session.add(LearningTask(analysis_id=analysis.id, title=task["title"], week=phase["week"]))
        db.session.commit()
        if warning:
            flash(warning, "info")
        return redirect(url_for("report", analysis_id=analysis.id))

    @app.get("/report/<int:analysis_id>")
    @login_required
    def report(analysis_id):
        analysis = Analysis.query.filter_by(id=analysis_id, user_id=current_user.id).first_or_404()
        task_states = {task.title: task.completed for task in analysis.learning_tasks}
        task_ids = {task.title: task.id for task in analysis.learning_tasks}
        return render_template(
            "report.html",
            analysis=analysis,
            report=analysis.report_json,
            task_states=task_states,
            task_ids=task_ids,
        )

    @app.get("/history")
    @login_required
    def history():
        analyses = Analysis.query.filter_by(user_id=current_user.id).order_by(Analysis.created_at.desc()).all()
        return render_template("history.html", analyses=analyses)

    @app.get("/jobs")
    @login_required
    def jobs():
        recent = Analysis.query.filter_by(user_id=current_user.id).order_by(Analysis.created_at.desc()).limit(3).all()
        return render_template("jobs.html", jobs=JOB_ROLES, analyses=recent)

    @app.get("/learning")
    @app.get("/learning/<int:analysis_id>")
    @login_required
    def learning(analysis_id=None):
        query = Analysis.query.filter_by(user_id=current_user.id)
        analysis = (
            query.filter_by(id=analysis_id).first_or_404()
            if analysis_id is not None
            else query.order_by(Analysis.created_at.desc()).first()
        )
        task_states = {task.title: task.completed for task in analysis.learning_tasks} if analysis else {}
        task_ids = {task.title: task.id for task in analysis.learning_tasks} if analysis else {}
        return render_template(
            "learning.html",
            analysis=analysis,
            task_states=task_states,
            task_ids=task_ids,
        )

    @app.post("/history/<int:analysis_id>/delete")
    @login_required
    def delete_analysis(analysis_id):
        analysis = Analysis.query.filter_by(id=analysis_id, user_id=current_user.id).first_or_404()
        db.session.delete(analysis)
        db.session.commit()
        flash("Analysis report deleted.", "success")
        return redirect(url_for("history"))

    @app.post("/learning/<int:analysis_id>/tasks")
    @login_required
    def update_learning_task(analysis_id):
        analysis = Analysis.query.filter_by(id=analysis_id, user_id=current_user.id).first_or_404()
        payload = request.get_json(silent=True) or {}
        task_id = payload.get("task_id")
        completed = payload.get("completed")
        if not isinstance(task_id, int) or not isinstance(completed, bool):
            return jsonify(error="Provide a valid task and completion state."), 400
        task = LearningTask.query.filter_by(id=task_id, analysis_id=analysis.id).first_or_404()
        task.completed = completed
        db.session.commit()
        return jsonify({"task_id": task.id, "completed": task.completed})

    @app.get("/report/<int:analysis_id>/pdf")
    @login_required
    def download_pdf(analysis_id):
        analysis = Analysis.query.filter_by(id=analysis_id, user_id=current_user.id).first_or_404()
        report = analysis.report_json
        output = BytesIO()
        document = SimpleDocTemplate(output, pagesize=letter, rightMargin=0.65 * inch, leftMargin=0.65 * inch)
        styles = getSampleStyleSheet()
        flow = [
            Paragraph("ResumeAI Analysis Report", styles["Title"]),
            Paragraph(f"Target role: {escape(analysis.target_role or 'Not specified')}", styles["Normal"]),
            Paragraph(f"Analysis mode: {escape(analysis.analyzer_mode)}", styles["Normal"]),
            Paragraph(f"Resume quality guidance score: {report['quality']['score']}/100", styles["Heading2"]),
            Paragraph(escape(report["summary"]), styles["BodyText"]),
        ]

        def add_section(title):
            flow.extend([Spacer(1, 10), Paragraph(title, styles["Heading2"])])

        def add_table(rows, widths):
            table = Table(rows, colWidths=widths, repeatRows=1)
            table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#142447")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dce3ee")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f6fb")]),
            ]))
            flow.append(table)

        if report["job_match"]:
            flow.append(Paragraph(
                f"Target skill coverage: {report['job_match']['score']}% "
                f"({len(report['job_match']['covered'])} of {report['job_match']['required_count']} skills detected). "
                f"{escape(report['job_match']['method'])}",
                styles["BodyText"],
            ))

        add_section("Resume quality breakdown")
        add_table(
            [["Category", "Score", "Weight", "Feedback"]]
            + [[
                escape(item["name"]),
                f"{item['score']}/{item['weight']}",
                f"{item['weight']}%",
                Paragraph(escape(item["feedback"]), styles["BodyText"]),
            ] for item in report["quality"]["criteria"]],
            [1.35 * inch, 0.65 * inch, 0.55 * inch, 3.9 * inch],
        )

        add_section("Detected skills and evidence")
        if report["skills"]:
            add_table(
                [["Skill", "Category", "Evidence in resume text"]]
                + [[
                    escape(item["name"]),
                    escape(item["category"]),
                    Paragraph(escape(item["evidence"]), styles["BodyText"]),
                ] for item in report["skills"]],
                [1.0 * inch, 1.65 * inch, 3.8 * inch],
            )
        else:
            flow.append(Paragraph("No catalogue skills detected.", styles["BodyText"]))

        add_section("Career recommendations")
        add_table(
            [["Role", "Match", "Evidence found"]]
            + [[
                escape(item["title"]),
                f"{item['match']}%",
                Paragraph(escape(item["reason"] + " " + item["next_step"]), styles["BodyText"]),
            ] for item in report["recommendations"]],
            [1.55 * inch, 0.65 * inch, 4.25 * inch],
        )

        add_section("Missing or unmentioned skills")
        if report["missing_skills"]:
            add_table(
                [["Skill", "Priority", "Why it matters"]]
                + [[
                    escape(item["skill"]),
                    escape(item["priority"]),
                    Paragraph(escape(item["why"] + " " + item["note"]), styles["BodyText"]),
                ] for item in report["missing_skills"]],
                [1.0 * inch, 0.9 * inch, 4.55 * inch],
            )
        else:
            flow.append(Paragraph("No missing skill comparison was prepared.", styles["BodyText"]))

        add_section("Resume improvement suggestions")
        for item in report["improvements"]:
            flow.append(Paragraph(f"<b>{escape(item['issue'])}</b>", styles["BodyText"]))
            flow.append(Paragraph(escape(item["why"] + " " + item["recommendation"]), styles["BodyText"]))
            if item["example"]:
                flow.append(Paragraph(f"Example: {escape(item['example'])}", styles["BodyText"]))
            flow.append(Spacer(1, 5))

        add_section("Four-week learning roadmap")
        for phase in report["learning_plan"]:
            flow.append(Paragraph(escape(phase["week"]), styles["Heading3"]))
            for task in phase["tasks"]:
                flow.append(Paragraph(
                    f"<b>{escape(task['title'])}</b> ({escape(task['estimate'])})",
                    styles["BodyText"],
                ))
                flow.append(Paragraph(
                    escape(task["activity"] + " " + task["exercise"] + " Goal: " + task["goal"]),
                    styles["BodyText"],
                ))
                flow.append(Paragraph(
                    f"Resource: {escape(task['resource_name'])} — {escape(task['resource_url'])}",
                    styles["BodyText"],
                ))
                flow.append(Spacer(1, 4))

        add_section("ATS-readability checklist")
        for item in report["ats_checklist"]:
            marker = "Complete" if item["passed"] else "Review"
            flow.append(Paragraph(f"[{marker}] {escape(item['label'])}", styles["BodyText"]))

        add_section("Important limitations")
        flow.extend(Paragraph(escape(item), styles["BodyText"]) for item in report["limitations"])
        flow.append(Paragraph(
            "This is student guidance, not a hiring decision, hiring probability, or perfect ATS simulation.",
            styles["BodyText"],
        ))
        document.build(flow)
        output.seek(0)
        return send_file(output, mimetype="application/pdf", as_attachment=True, download_name=f"resumeai-report-{analysis.id}.pdf")

    @app.get("/about")
    def about():
        return render_template("about.html")

    @app.errorhandler(413)
    def too_large(_error):
        flash(f"Upload exceeds the {app.config['MAX_CONTENT_LENGTH'] // (1024 * 1024)} MB limit.", "error")
        return redirect(url_for("analyze"))

    @app.errorhandler(CSRFError)
    def csrf_error(_error):
        return render_template("error.html", title="Security token expired", message="Refresh the page and submit the form again."), 400

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("error.html", title="Page not found", message="The page or report could not be found."), 404

    @app.errorhandler(429)
    def rate_limited(_error):
        return render_template("error.html", title="Slow down", message="Too many requests. Wait a few minutes and try again."), 429

    @app.errorhandler(500)
    def internal_error(_error):
        db.session.rollback()
        return render_template(
            "error.html",
            title="Something went wrong",
            message="The request could not be completed. Please try again.",
        ), 500

    with app.app_context():
        db.create_all()

    return app


app = create_app()


if __name__ == "__main__":
    if not os.getenv("FLASK_SECRET_KEY"):
        print("Warning: using a temporary local session key. Set FLASK_SECRET_KEY in .env for persistent sessions.")
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG") == "true")
