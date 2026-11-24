"""Flask application factory."""
from pathlib import Path

from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import event, inspect, text
from sqlalchemy.engine import Engine

from config import Config

db = SQLAlchemy()
csrf = CSRFProtect()

MIGRATION_COLUMNS = {
    "review": {
        "file_count": "INTEGER DEFAULT 1",
        "file_names_json": "TEXT DEFAULT '[]'",
        "source_files_json": "TEXT DEFAULT '{}'",
        "quality_score": "REAL DEFAULT 0",
        "risk_level": "TEXT DEFAULT 'Low'",
        "avg_confidence": "REAL DEFAULT 0",
        "avg_uncertainty": "REAL DEFAULT 0",
        "metrics_json": "TEXT DEFAULT '{}'",
    },
    "finding": {
        "rule_id": "TEXT DEFAULT ''",
        "column_no": "INTEGER DEFAULT 1",
        "cwe": "TEXT DEFAULT ''",
        "category_group": "TEXT DEFAULT ''",
        "explanation": "TEXT DEFAULT ''",
        "potential_impact": "TEXT DEFAULT ''",
        "fix_code": "TEXT DEFAULT ''",
        "fix_valid": "INTEGER DEFAULT 0",
        "score_factors_json": "TEXT DEFAULT '{}'",
        "model_probability": "REAL",
        "calibrated_probability": "REAL",
        "model_version": "TEXT DEFAULT ''",
    },
}

MIGRATION_INDEXES = (
    "CREATE INDEX IF NOT EXISTS ix_finding_rule_id ON finding (rule_id)",
    "CREATE INDEX IF NOT EXISTS ix_finding_severity ON finding (severity)",
    "CREATE INDEX IF NOT EXISTS ix_finding_category ON finding (category)",
    "CREATE INDEX IF NOT EXISTS ix_finding_confidence_level ON finding (confidence_level)",
    "CREATE INDEX IF NOT EXISTS ix_finding_review_id ON finding (review_id)",
    "CREATE INDEX IF NOT EXISTS ix_evidence_finding_id ON evidence (finding_id)",
    "CREATE INDEX IF NOT EXISTS ix_review_created_at ON review (created_at)",
)


@event.listens_for(Engine, "connect")
def enable_sqlite_foreign_keys(connection, _record):
    """SQLite leaves FK enforcement off by default; enable it for each connection."""
    if connection.__class__.__module__.startswith("sqlite3"):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def upgrade_schema():
    """Add newer columns to an existing SQLite database without dropping records."""
    try:
        inspector = inspect(db.engine)
        tables = set(inspector.get_table_names())
        for table, columns in MIGRATION_COLUMNS.items():
            if table not in tables:
                continue
            existing = {column["name"] for column in inspector.get_columns(table)}
            for name, definition in columns.items():
                if name not in existing:
                    db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {definition}"))
        for statement in MIGRATION_INDEXES:
            db.session.execute(text(statement))
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    csrf.init_app(app)

    from app.routes.dashboard import bp as dashboard_bp
    from app.routes.review import bp as review_bp, api_bp
    from app.routes.history import bp as history_bp
    from app.routes.settings import bp as settings_bp
    from app.routes.analysis import bp as analysis_bp
    from app.routes.reports import bp as reports_bp
    from app.routes.help import bp as help_bp
    from app.routes.api import bp as new_api_bp

    for blueprint in (dashboard_bp, review_bp, api_bp, history_bp, settings_bp,
                      analysis_bp, reports_bp, help_bp, new_api_bp):
        app.register_blueprint(blueprint)

    from app.utils.settings_store import get_settings
    from app.services.ai_provider import provider_status

    @app.context_processor
    def inject_globals():
        from flask import request
        return {
            "app_settings": get_settings(),
            "ai_status": provider_status(),
            "current_path": request.path,
            "app_version": "2.0.0",
        }

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def server_error(_error):
        db.session.rollback()
        return render_template("500.html"), 500

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("403.html"), 403

    with app.app_context():
        from app import models  # noqa: F401
        db.create_all()
        upgrade_schema()

    return app
