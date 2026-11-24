"""Optional, explicitly configured AI explanations. No responses are fabricated."""
import json
import os
import urllib.error
import urllib.request

ACTIONS = {
    "explain_code": "Explain this code",
    "explain_error": "Explain this error",
    "explain_vulnerability": "Explain this vulnerability",
    "suggest_correction": "Suggest a correction",
    "improve_readability": "Improve code readability",
    "optimize_code": "Optimize code",
    "explain_security_risks": "Explain security risks",
    "suggest_best_practices": "Suggest best practices",
}


def _credentials():
    return os.environ.get("REVIEW_AI_ENDPOINT", "").strip(), os.environ.get("REVIEW_AI_API_KEY", "").strip()


def provider_status():
    endpoint, key = _credentials()
    enabled = bool(endpoint and key)
    return {
        "enabled": enabled,
        "mode": "Configured AI provider available." if enabled else "Local analysis mode active. No AI provider is configured.",
        "endpoint_configured": bool(endpoint),
        "key_configured": bool(key),
        "actions": [{"id": key_, "label": label} for key_, label in ACTIONS.items()],
    }


def request_explanation(action, code, finding=None, timeout=20):
    """Call the configured provider. Returns an explicit error when unavailable."""
    endpoint, key = _credentials()
    if not endpoint or not key:
        return {"ok": False, "text": "", "error": "AI explanations require REVIEW_AI_ENDPOINT and REVIEW_AI_API_KEY to be configured. Local analysis is unaffected.", "provider": "unconfigured"}
    if action not in ACTIONS:
        return {"ok": False, "text": "", "error": "Unknown AI action.", "provider": "unconfigured"}
    instruction = ACTIONS[action]
    payload = {
        "action": action,
        "instruction": instruction,
        "language": "python",
        "code": code,
        "finding": {k: finding.get(k) for k in ("title", "description", "severity", "confidence", "recommendation")} if finding else None,
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8", errors="replace"))
        text = body.get("text") or body.get("output") or ""
        if not text and isinstance(body.get("choices"), list) and body["choices"]:
            text = body["choices"][0].get("message", {}).get("content", "")
        if not text:
            return {"ok": False, "text": "", "error": "The configured provider returned no explanation text.", "provider": "configured"}
        return {"ok": True, "text": text, "error": "", "provider": "configured"}
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        return {"ok": False, "text": "", "error": f"AI provider request failed: {exc}", "provider": "configured"}
