"""Help and documentation page."""
from flask import Blueprint, render_template

bp = Blueprint("help", __name__)

SHORTCUTS = [
    ("Ctrl / ⌘ + Enter", "Run analysis"),
    ("Ctrl / ⌘ + K", "Focus global search"),
    ("Ctrl / ⌘ + B", "Toggle sidebar"),
    ("Esc", "Close modal"),
]

GUIDE = [
    ("1. Submit source", "Paste Python code or upload up to eight supported source files. Files are parsed as text and never executed."),
    ("2. Review findings", "Findings are grouped by severity and category. Each card shows evidence, location, confidence and uncertainty."),
    ("3. Understand scores", "Confidence is an evidence-weighted heuristic estimate. It is not an empirically calibrated probability."),
    ("4. Apply fixes safely", "Suggested fixes are syntax-checked where possible, but the original source is always preserved. Copy or download patched code explicitly."),
    ("5. Export and compare", "Download PDF, JSON, CSV or Markdown reports and compare two reviews using stable rule identifiers."),
]


@bp.get("/help")
def help_page():
    return render_template("help.html", shortcuts=SHORTCUTS, guide=GUIDE)
