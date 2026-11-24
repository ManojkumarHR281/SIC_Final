"""Persistent review, finding, evidence, and preference records."""
from datetime import datetime, timezone

from app import db


class Review(db.Model):
    __tablename__ = "review"
    __table_args__ = (
        db.Index("ix_review_created_at", "created_at"),
        db.Index("ix_review_language", "language"),
        db.Index("ix_review_status", "status"),
    )

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    language = db.Column(db.String(24), nullable=False)
    review_mode = db.Column(db.String(32), nullable=False)
    code_hash = db.Column(db.String(64), nullable=False)
    code_size = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(24), default="complete", nullable=False)
    total_findings = db.Column(db.Integer, default=0)
    high_confidence_count = db.Column(db.Integer, default=0)
    medium_confidence_count = db.Column(db.Integer, default=0)
    low_confidence_count = db.Column(db.Integer, default=0)
    duration = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    file_count = db.Column(db.Integer, default=1)
    file_names_json = db.Column(db.Text, default="[]")
    source_files_json = db.Column(db.Text, default="{}")
    quality_score = db.Column(db.Float, default=0)
    risk_level = db.Column(db.String(24), default="Low")
    avg_confidence = db.Column(db.Float, default=0)
    avg_uncertainty = db.Column(db.Float, default=0)
    metrics_json = db.Column(db.Text, default="{}")

    findings = db.relationship("Finding", backref="review", cascade="all, delete-orphan", order_by="Finding.confidence.desc()")

    @property
    def file_names(self):
        import json
        try:
            value = json.loads(self.file_names_json or "[]")
            return value if isinstance(value, list) else []
        except (TypeError, ValueError):
            return []

    @property
    def source_files(self):
        import json
        try:
            value = json.loads(self.source_files_json or "{}")
            return value if isinstance(value, dict) else {}
        except (TypeError, ValueError):
            return {}

    @property
    def metrics(self):
        import json
        try:
            value = json.loads(self.metrics_json or "{}")
            return value if isinstance(value, dict) else {}
        except (TypeError, ValueError):
            return {}

    @property
    def severity_counts(self):
        counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0, "Informational": 0}
        for finding in self.findings:
            if finding.severity in counts:
                counts[finding.severity] += 1
        return counts


class Finding(db.Model):
    __tablename__ = "finding"
    __table_args__ = (
        db.Index("ix_finding_review_id", "review_id"),
        db.Index("ix_finding_severity", "severity"),
        db.Index("ix_finding_category", "category"),
        db.Index("ix_finding_confidence_level", "confidence_level"),
        db.Index("ix_finding_rule_id", "rule_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    review_id = db.Column(db.Integer, db.ForeignKey("review.id", ondelete="CASCADE"), nullable=False)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(32), nullable=False)
    severity = db.Column(db.String(24), nullable=False)
    file_name = db.Column(db.String(255), default="submitted_code.py")
    line_start = db.Column(db.Integer, nullable=True)
    line_end = db.Column(db.Integer, nullable=True)
    snippet = db.Column(db.Text, default="")
    confidence = db.Column(db.Float, nullable=False)
    uncertainty = db.Column(db.Float, nullable=False)
    confidence_level = db.Column(db.String(24), nullable=False)
    recommendation = db.Column(db.Text, nullable=False)
    suggested_fix = db.Column(db.Text, default="")
    source = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(24), default="open", nullable=False)
    rationale = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    rule_id = db.Column(db.String(64), default="")
    column_no = db.Column(db.Integer, default=1)
    cwe = db.Column(db.String(24), default="")
    category_group = db.Column(db.String(32), default="")
    explanation = db.Column(db.Text, default="")
    potential_impact = db.Column(db.Text, default="")
    fix_code = db.Column(db.Text, default="")
    fix_valid = db.Column(db.Boolean, default=False)
    score_factors_json = db.Column(db.Text, default="{}")
    model_probability = db.Column(db.Float, nullable=True)
    calibrated_probability = db.Column(db.Float, nullable=True)
    model_version = db.Column(db.String(64), default="")

    evidence = db.relationship("Evidence", backref="finding", cascade="all, delete-orphan")

    @property
    def score_factors(self):
        import json
        try:
            value = json.loads(self.score_factors_json or "{}")
            return value if isinstance(value, dict) else {}
        except (TypeError, ValueError):
            return {}


class Evidence(db.Model):
    __tablename__ = "evidence"
    __table_args__ = (db.Index("ix_evidence_finding_id", "finding_id"),)

    id = db.Column(db.Integer, primary_key=True)
    finding_id = db.Column(db.Integer, db.ForeignKey("finding.id", ondelete="CASCADE"), nullable=False)
    source = db.Column(db.String(120), nullable=False)
    evidence_type = db.Column(db.String(40), nullable=False)
    description = db.Column(db.Text, nullable=False)
    strength = db.Column(db.Float, nullable=False)
    verified = db.Column(db.Boolean, default=False)
    metadata_json = db.Column(db.Text, default="{}")


class UserSetting(db.Model):
    __tablename__ = "user_setting"

    id = db.Column(db.Integer, primary_key=True)
    preferences_json = db.Column(db.Text, default="{}")
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    @property
    def preferences(self):
        import json
        try:
            value = json.loads(self.preferences_json or "{}")
            return value if isinstance(value, dict) else {}
        except (TypeError, ValueError):
            return {}
