"""Safe helpers for extracting source snippets without evaluating code."""
import json


def snippet_at(code, line, radius=1):
    rows = code.splitlines()
    if not line or line < 1 or line > len(rows):
        return ""
    return "\n".join(rows[max(0, line - radius - 1):min(len(rows), line + radius)])


def line_with_pointer(code, line, column=None):
    rows = code.splitlines()
    if not line or line < 1 or line > len(rows):
        return ""
    text = rows[line - 1]
    if column and 0 <= column <= len(text) + 1:
        return text + "\n" + " " * (column - 1) + "^"
    return text


def json_dumps(value):
    """Compact deterministic JSON for metadata columns."""
    return json.dumps(value, separators=(",", ":"), sort_keys=True)
