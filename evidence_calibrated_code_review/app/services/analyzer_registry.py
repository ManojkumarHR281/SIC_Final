"""Extensible analyzer registry. Only Python currently has a complete adapter."""
from app.services.code_analyzer import analyze_python
from app.services.security_analyzer import analyze_security

SUPPORTED_LANGUAGES = {
    "python": {"name": "Python", "full_analysis": True, "extensions": [".py"]},
    "javascript": {"name": "JavaScript", "full_analysis": False, "extensions": [".js"]},
    "typescript": {"name": "TypeScript", "full_analysis": False, "extensions": [".ts"]},
    "java": {"name": "Java", "full_analysis": False, "extensions": [".java"]},
    "cpp": {"name": "C++", "full_analysis": False, "extensions": [".cpp"]},
    "c": {"name": "C", "full_analysis": False, "extensions": [".c"]},
    "csharp": {"name": "C#", "full_analysis": False, "extensions": [".cs"]},
    "php": {"name": "PHP", "full_analysis": False, "extensions": [".php"]},
    "go": {"name": "Go", "full_analysis": False, "extensions": [".go"]},
    "ruby": {"name": "Ruby", "full_analysis": False, "extensions": [".rb"]},
}


def analyze(code, language="python"):
    """Return (findings, metrics, is_full_analysis) for the selected language."""
    language = language if language in SUPPORTED_LANGUAGES else "python"
    info = SUPPORTED_LANGUAGES[language]
    if language == "python":
        return analyze_python(code), _python_metrics(code), True
    findings = analyze_security(code)
    for item in findings:
        item["source"] = f"Generic {info['name']} pattern rules"
    lines = code.splitlines()
    metrics = {
        "lines_of_code": sum(1 for row in lines if row.strip() and not row.lstrip().startswith(("//", "#"))),
        "total_lines": len(lines),
        "function_count": 0, "class_count": 0,
        "total_complexity": 0, "max_complexity": 0, "average_complexity": 0,
        "max_nesting": 0, "maintainability_index": 0,
        "documentation_ratio": 0, "functions": [],
        "limited_analysis": True,
    }
    return findings, metrics, False


def _python_metrics(code):
    from app.services.metrics import calculate_metrics

    try:
        return calculate_metrics(code)
    except SyntaxError as exc:
        lines = code.splitlines()
        loc = sum(1 for row in lines if row.strip() and not row.lstrip().startswith("#"))
        return {
            "lines_of_code": loc,
            "total_lines": len(lines),
            "function_count": 0, "class_count": 0,
            "total_complexity": 0, "max_complexity": 0, "average_complexity": 0,
            "max_nesting": 0, "documented_functions": 0, "documentation_ratio": 0,
            "maintainability_index": 0, "functions": [],
            "syntax_error": {"message": exc.msg, "line": exc.lineno, "offset": exc.offset},
        }
