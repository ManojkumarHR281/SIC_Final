"""Persistent application preferences stored as a single settings record."""
import copy
import json

DEFAULT_SETTINGS = {
    "theme": "dark",
    "language": "python",
    "font_size": 13,
    "tab_size": 4,
    "word_wrap": True,
    "minimap": True,
    "editor_theme": "vs-dark",
    "enabled_rules": {"security": True, "quality": True, "complexity": True, "bugs": True},
    "severity_preferences": {"Critical": True, "High": True, "Medium": True, "Low": True},
    "confidence_display": "percentage",
    "default_report_format": "pdf",
    "report_options": {"include_snippets": True, "include_evidence": True, "include_metrics": True},
    "ai_provider": "none",
    "ai_model": "default",
}


def _record():
    from app import db
    from app.models import UserSetting

    record = db.session.get(UserSetting, 1)
    if record is None:
        record = UserSetting(id=1, preferences_json=json.dumps(DEFAULT_SETTINGS))
        db.session.add(record)
        db.session.commit()
    return record


def get_settings():
    """Return saved preferences merged over the defaults."""
    try:
        saved = _record().preferences
    except Exception:
        saved = {}
    merged = copy.deepcopy(DEFAULT_SETTINGS)
    for key, value in saved.items():
        if key in merged and isinstance(value, type(merged[key])):
            if isinstance(value, dict):
                merged[key].update(value)
            else:
                merged[key] = value
    return merged


def save_settings(payload):
    """Validate and persist preferences; returns the effective settings."""
    from app import db

    if not isinstance(payload, dict):
        return get_settings()
    current = get_settings()
    for key, default in DEFAULT_SETTINGS.items():
        if key not in payload:
            continue
        value = payload[key]
        if not isinstance(value, type(default)):
            continue
        if isinstance(value, dict):
            for nested_key, nested_value in value.items():
                if nested_key in current[key] and isinstance(nested_value, type(current[key][nested_key])):
                    current[key][nested_key] = nested_value
        else:
            current[key] = value
    current["font_size"] = max(10, min(22, int(current["font_size"])))
    current["tab_size"] = max(2, min(8, int(current["tab_size"])))
    current["theme"] = "dark"
    if current["confidence_display"] not in {"percentage", "decimal"}:
        current["confidence_display"] = "percentage"
    if current["default_report_format"] not in {"pdf", "json", "csv", "markdown"}:
        current["default_report_format"] = "pdf"
    record = _record()
    record.preferences_json = json.dumps(current)
    db.session.commit()
    return current
