"""Simple evidence-preserving report summary from measured review results."""


def summarize(findings):
    if not findings:
        return "No findings were reported by the configured analyzers."
    counts = {}
    for finding in findings:
        severity = finding.get("severity", "Unknown")
        counts[severity] = counts.get(severity, 0) + 1
    return f"{len(findings)} finding(s) reported. Severity counts: " + ", ".join(f"{k}: {v}" for k, v in sorted(counts.items())) + "."
