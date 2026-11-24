"""Settings, methodology and integration status."""
from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.services.ai_provider import provider_status
from app.utils.settings_store import get_settings, save_settings

bp = Blueprint("settings", __name__)


def _parse_form(form):
    payload = {}
    for key in form:
        value = form.getlist(key)
        value = value[0] if len(value) == 1 else value
        if "[" in key and key.endswith("]"):
            parent, child = key[:-1].split("[", 1)
            payload.setdefault(parent, {})[child] = value
        else:
            payload[key] = value
    return payload


@bp.get("/settings")
def settings():
    return render_template("settings.html", ai=provider_status(), settings=get_settings(),
                           github={"enabled": False, "reason": "GitHub repository access is disabled in this offline-first build."})


def _coerce(value):
    if isinstance(value, dict):
        return {key: _coerce(item) for key, item in value.items()}
    if isinstance(value, str):
        if value.lower() == "true":
            return True
        if value.lower() == "false":
            return False
        if value.isdigit():
            return int(value)
    return value


@bp.post("/settings")
def save_settings_route():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        payload = _parse_form(request.form)
    save_settings({key: _coerce(value) for key, value in payload.items()})
    flash("Preferences saved.", "success")
    return redirect(url_for("settings.settings"))
