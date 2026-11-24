"""Supplementary safe lexical checks for languages without a full parser."""
import re

GENERIC_PATTERNS = [
    (r"\bsubprocess\.(?:run|call|Popen|check_call|check_output)\s*\([^)]*?\bshell\s*=\s*True",
     "PY-SEC-007", "Subprocess with shell=True", "Subprocess", "Unsafe execution", "CWE-78",
     "Shell interpretation can make command injection possible if any argument is untrusted."),
    (r"\b(?:password|api_key|secret|token)\s*=\s*['\"][^'\"]{4,}['\"]",
     "PY-SEC-004", "Possible hardcoded secret", "Secrets exposure", "Secrets exposure", "CWE-798",
     "A credential-like assignment uses a literal; validity and exposure context require manual confirmation."),
]


def analyze_security(code):
    out = []
    for pattern, rule_id, title, category, group, cwe, description in GENERIC_PATTERNS:
        for match in re.finditer(pattern, code, re.I | re.S):
            line = code.count("\n", 0, match.start()) + 1
            column = match.start() - (code.rfind("\n", 0, match.start()) + 1) + 1
            out.append({
                "rule_id": rule_id,
                "title": title,
                "description": description,
                "explanation": description,
                "category": "Security",
                "category_group": group,
                "severity": "High",
                "cwe": cwe,
                "line": line,
                "column": column,
                "source": "Local security pattern rules",
                "recommendation": "Avoid shell parsing and keep credentials outside source code.",
                "suggested_fix": "Use a validated argument list or environment-based secret storage.",
                "potential_impact": "Exploitability depends on runtime context and input sources.",
                "verified": False, "strength": .72, "certainty": .70, "reliability": .78, "context": .58,
                "independent": None, "context_dependent": True,
                "evidence_description": description,
                "fix_code": "", "fix_valid": False,
            })
    return out
