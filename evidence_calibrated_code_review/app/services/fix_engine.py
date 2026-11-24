"""Fix validation and safe before/after comparison helpers."""
import ast
import difflib


def validate_fix(text, language="python"):
    """Syntax-check a suggested fix. Syntax validity is not semantic correctness."""
    if not text or not text.strip():
        return {"valid": False, "syntax_valid": False, "reason": "No fix was provided."}
    if language != "python":
        return {"valid": False, "syntax_valid": False, "reason": "Automatic fix validation is only available for Python."}
    candidates = [text]
    indented = "\n".join(("    " + line) if line.strip() else line for line in text.splitlines())
    candidates.append(f"def _candidate():\n{indented}")
    for candidate in candidates:
        try:
            ast.parse(candidate)
            return {"valid": True, "syntax_valid": True,
                    "reason": "The suggestion is syntactically valid Python; review the change before applying it."}
        except SyntaxError as exc:
            last = f"Syntax error at line {exc.lineno or 1}, column {exc.offset or 1}: {exc.msg}"
    return {"valid": False, "syntax_valid": False, "reason": last}


def build_diff(before, after, from_label="before", to_label="after"):
    """Return a unified diff for side-by-side display."""
    return list(difflib.unified_diff(
        (before or "").splitlines(), (after or "").splitlines(),
        fromfile=from_label, tofile=to_label, lineterm="", n=2,
    ))


def apply_line_replacement(source, line, new_text):
    """Return a copy of source with one line replaced; never mutates the original."""
    if not line or line < 1:
        return source
    rows = source.splitlines(keepends=True)
    if line > len(rows):
        return source
    newline = "\n" if rows[line - 1].endswith("\n") else ""
    rows[line - 1] = new_text.rstrip("\n") + newline
    return "".join(rows)
