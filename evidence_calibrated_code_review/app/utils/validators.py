"""Input validation for untrusted submitted source."""
import re

LANGUAGES = {"python", "javascript", "typescript", "java", "cpp", "c", "csharp", "php", "go", "ruby"}
MODES = {"comprehensive", "general", "bugs", "security", "performance", "quality"}
SENSITIVITIES = {"conservative", "balanced", "thorough"}
MAX_CODE_BYTES = 500_000
MAX_FILES = 8
MAX_TOTAL_BYTES = 1_500_000
ALLOWED_EXTENSIONS = {".py", ".js", ".ts", ".java", ".cpp", ".c", ".cs", ".php", ".go", ".rb"}
EXTENSION_LANGUAGE = {
    ".py": "python", ".js": "javascript", ".ts": "typescript", ".java": "java",
    ".cpp": "cpp", ".c": "c", ".cs": "csharp", ".php": "php", ".go": "go", ".rb": "ruby",
}


def validate_review(code, language, mode, sensitivity):
    if not isinstance(code, str) or not code.strip():
        return "Please provide non-empty source code."
    if len(code.encode("utf-8")) > MAX_CODE_BYTES:
        return "Source code exceeds the 500 KB per-file limit."
    if not isinstance(language, str) or language not in LANGUAGES:
        return "Unsupported programming language."
    if not isinstance(mode, str) or mode not in MODES:
        return "Unsupported analysis mode."
    if not isinstance(sensitivity, str) or sensitivity not in SENSITIVITIES:
        return "Unsupported review sensitivity."
    return None


def safe_filename(name):
    name = str(name or "source").replace("\\", "/").split("/")[-1]
    name = re.sub(r"[^A-Za-z0-9_.-]", "_", name)[:120]
    return name if name and "." in name else "source.py"


def extension_of(filename):
    name = safe_filename(filename)
    return "." + name.rsplit(".", 1)[-1].lower()


def validate_upload(filename, size):
    """Validate one uploaded file before its contents are read."""
    extension = extension_of(filename)
    if extension not in ALLOWED_EXTENSIONS:
        return f"Unsupported file extension '{extension}'."
    if size > MAX_CODE_BYTES:
        return "Each source file must be 500 KB or smaller."
    return None


def language_for_filename(filename):
    return EXTENSION_LANGUAGE.get(extension_of(filename), "python")
