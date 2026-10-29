# ResumeAI

ResumeAI is a local Flask application for student resume analysis and career guidance. It accepts PDF/DOCX files or pasted text, detects catalogue skills, compares them with entry-level role requirements, creates a learning roadmap, and stores private analysis reports in SQLite.

The project is a guidance and education tool. It is not a hiring system, a live job board, an ATS simulator, or a predictor of employment outcomes.

## Features

- Account registration, sign-in, password hashing, per-account report ownership, and CSRF protection.
- PDF text extraction with PyMuPDF and DOCX text extraction with python-docx. Scanned PDFs with little selectable text receive an OCR limitation message; OCR is not included.
- Local rule-based skills, evidence hints, configurable score categories, role recommendations, missing-skill comparison, learning resources, and resume improvement checklist.
- Optional OpenAI-assisted summary and truthful writing suggestions. The UI labels the analysis mode; rule-based output remains usable without an API key.
- Analysis history, report deletion, learning task progress, and a downloadable PDF report.
- Uploaded file bytes are processed in memory and are not saved. Extracted resume text and the report are saved to the signed-in user's history until deleted.

## Requirements

- Python 3.10 or later (3.11+ recommended)
- Windows, macOS, or Linux
- Internet access is needed for the Bootstrap/Chart.js CDN assets; the server and analysis run locally.

## Install and run on Windows

From the `resume-ai` directory in VS Code:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and set `FLASK_SECRET_KEY` to a new random value (for example, generate one with `python -c "import secrets; print(secrets.token_urlsafe(32))"`). The local default creates a temporary random key when this is not configured, so sessions will not survive a server restart.

Start the application:

```powershell
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000). Create an account, upload a resume or paste its text, optionally choose a target role or add a job description, and submit the analysis. Reports and learning progress are available from the sidebar.

## Optional OpenAI setup

Set `OPENAI_API_KEY` in `.env` and optionally set `OPENAI_MODEL` (defaults to `gpt-4o-mini`). The key is read by the server only and must never be added to frontend code or source control. An OpenAI request processes resume text for a summary and writing suggestions. Without the key, the app performs and clearly labels rule-based analysis. API failures or invalid output fall back to the labeled rule-based report.

The AI model is not used to invent candidate credentials, scores, or job openings. Model output is schema-constrained and validated. Avoid sending resume data to the optional AI service unless that external processing is acceptable to you.

## Configuration

| Variable | Purpose | Default |
|---|---|---|
| `FLASK_SECRET_KEY` | Session signing key; configure a random secret for persistent sessions | Random temporary local key |
| `DATABASE_URL` | SQLAlchemy database URL | `sqlite:///resumeai.sqlite` |
| `OPENAI_API_KEY` | Optional server-side API key | Empty (rule-based mode) |
| `OPENAI_MODEL` | OpenAI model name | `gpt-4o-mini` |
| `MAX_CONTENT_LENGTH` | Maximum request size in bytes | `8388608` (8 MiB) |
| `SESSION_COOKIE_SECURE` | Set secure cookies behind HTTPS | `false` for local HTTP |
| `PORT` | Local server port | `5000` |
| `FLASK_DEBUG` | Enable Flask debug mode for local development | Disabled |

The SQLite database is created in Flask's instance directory on first run. Uploaded files are not retained; reports contain extracted resume text only as needed for viewing the analysis and are owned by the account that created them.

## Tests

Activate the virtual environment and run:

```powershell
python -m pytest -q
```

Tests cover PDF/DOCX validation, skill evidence, match and score explanations, learning task tracking data, authentication, report ownership, and invalid input feedback.

## Troubleshooting

- **`ModuleNotFoundError`:** activate `.venv` and run `python -m pip install -r requirements.txt`.
- **Scanned PDF or empty extraction:** use a text-based PDF/DOCX or paste its text; OCR is not implemented.
- **AI is unavailable:** confirm the key and model in `.env`. The report still works in rule-based mode.
- **Sign-in expires after restart:** set a persistent `FLASK_SECRET_KEY` in `.env`.
- **Charts or styles do not load:** check access to the Bootstrap and Chart.js CDN; report text and tables remain available.
- **Port is already in use:** set `PORT` to an available local port before starting.

## Project layout

```text
app.py                    Flask routes, authentication, upload and PDF response
config.py                 Environment-based configuration
models.py                 User, report and learning-task models
extensions.py             Flask extensions
services/
  ai_service.py           Optional validated OpenAI summary/suggestions
  job_catalog.py          Editable local role/skill catalogue
  learning_recommender.py Four-week plan and reputable resource links
  resume_parser.py        In-memory PDF/DOCX extraction
  skill_analyzer.py       Rule-based skills, scores, gaps and suggestions
templates/                Accessible server-rendered pages
static/css/style.css      Responsive dashboard design
static/js/                Upload, progress, copy, and Chart.js behavior
tests/                    Service and Flask integration tests
```
