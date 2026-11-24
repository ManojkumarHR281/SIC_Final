"""Conservative, code-grounded language for model findings (no generated facts)."""


def explain_code_prediction(code, prediction):
    if not prediction.get("available"):
        return "No trained code model was available to explain this submission."
    if prediction["prediction"] == "non-vulnerable":
        return "The trained Devign model classified this C/C++ submission as non-vulnerable. This is a model prediction, not proof that the code is safe."
    if prediction["prediction"] == "uncertain":
        warning = prediction.get("quality_warning", "The model score did not reach the configured certainty threshold.")
        return f"The model cannot make a reliable vulnerable/non-vulnerable decision for this submission. {warning} No CWE or causal explanation is supported by Devign's binary labels."
    excerpt = next((line.strip() for line in code.splitlines() if line.strip()), "")
    evidence = f" The submitted source begins with: {excerpt[:180]!r}." if excerpt else " The submission contains no non-empty source line to cite."
    return ("The trained Devign classifier marked the submitted C/C++ code as a potential defect/vulnerability. "
            "Devign provides a binary label and does not identify a specific CWE or causal statement." + evidence)
