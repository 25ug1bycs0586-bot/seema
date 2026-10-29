from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db


def utc_now():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)
    analyses = db.relationship("Analysis", backref="owner", cascade="all, delete-orphan", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Analysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    target_role = db.Column(db.String(120), nullable=False, default="")
    career_field = db.Column(db.String(80), nullable=False, default="")
    job_description = db.Column(db.Text, nullable=False, default="")
    report_json = db.Column(db.JSON, nullable=False)
    analyzer_mode = db.Column(db.String(60), nullable=False, default="Rule-based")
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    learning_tasks = db.relationship("LearningTask", backref="analysis", cascade="all, delete-orphan", lazy=True)


class LearningTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    analysis_id = db.Column(db.Integer, db.ForeignKey("analysis.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(220), nullable=False)
    week = db.Column(db.String(80), nullable=False)
    completed = db.Column(db.Boolean, nullable=False, default=False)
    __table_args__ = (db.UniqueConstraint("analysis_id", "title", name="uq_learning_task_title"),)
