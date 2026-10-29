import pytest

from app import create_app
from extensions import db


@pytest.fixture()
def app():
    test_app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-key-not-for-production",
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "WTF_CSRF_ENABLED": False,
        "RATELIMIT_ENABLED": False,
    })
    yield test_app
    with test_app.app_context():
        db.session.remove()
        db.drop_all()


def create_account(client, name="Test Student", email="student@example.test"):
    return client.post("/register", data={
        "name": name,
        "email": email,
        "password": "a-secure-test-password",
    }, follow_redirects=True)


def test_public_landing_and_authenticated_navigation(app):
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert b"Your next opportunity" in response.data

    create_account(client)
    assert client.get("/").status_code == 200
    assert client.get("/analyze").status_code == 200
    assert client.get("/jobs").status_code == 200
    assert client.get("/learning").status_code == 200
    assert client.get("/history").status_code == 200


def test_analysis_persists_report_without_uploading_a_file(app):
    client = app.test_client()
    create_account(client)
    response = client.post("/analyze", data={
        "resume_text": (
            "Education\nComputer Science\nSkills\nPython SQL Git\n"
            "Projects\nBuilt a Python reporting application using SQL."
        ),
        "target_role": "Python Developer",
        "career_field": "software_development",
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Resume insights" in response.data
    assert b"Rule-based fallback" in response.data
    assert b"Download PDF" in response.data
    assert client.get("/history").data.count(b"Python Developer") == 1


def test_report_is_private_and_external_login_redirect_is_rejected(app):
    owner = app.test_client()
    create_account(owner)
    response = owner.post("/analyze", data={
        "resume_text": "Skills: Python and SQL. Project: Built a reporting tool.",
    })
    report_url = response.headers["Location"]

    other = app.test_client()
    create_account(other, "Other Student", "other@example.test")
    assert other.get(report_url).status_code == 404

    visitor = app.test_client()
    login_response = visitor.post(
        "/login?next=https://example.com/",
        data={"email": "student@example.test", "password": "a-secure-test-password"},
    )
    assert login_response.status_code == 302
    assert login_response.headers["Location"] == "/"


def test_invalid_pasted_resume_gets_clear_feedback(app):
    client = app.test_client()
    create_account(client)
    response = client.post("/analyze", data={"resume_text": "   "}, follow_redirects=True)
    assert response.status_code == 200
    assert b"Upload a PDF/DOCX resume or paste resume text before analyzing." in response.data
