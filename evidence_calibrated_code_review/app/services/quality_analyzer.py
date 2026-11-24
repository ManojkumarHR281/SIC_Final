"""Safe AST-based code-quality checks for Python source."""
import ast
from collections import Counter

from app.services.metrics import calculate_metrics

QUALITY_RULES = {
    "PY-QA-001": ("Unused import", "Imported name is never referenced in the submitted source.", "Remove the import or use the name.", "import module  # only when used"),
    "PY-QA-002": ("Unused local variable", "A local assignment is never read within its function.", "Remove the assignment or use the value.", "result = compute()  # then use result"),
    "PY-QA-003": ("Long function", "A function has many top-level statements, making behavior harder to verify.", "Split the function into smaller, purpose-focused helpers.", "Extract cohesive blocks into named functions."),
    "PY-QA-004": ("Excessive nesting", "Deeply nested control flow is difficult to read and test.", "Use early returns or helper functions to reduce nesting.", "if not valid:\n    return None"),
    "PY-QA-005": ("Poor function name", "A function name is very short or does not follow snake_case.", "Use a descriptive snake_case name.", "def calculate_total(items):"),
    "PY-QA-006": ("Missing docstring", "A non-trivial function has no documentation string.", "Add a concise docstring describing purpose and contract.", 'def calculate_total(items):\n    """Return the total value of items."""'),
    "PY-QA-007": ("Duplicate code block", "An identical statement sequence appears in more than one function.", "Extract the shared logic into a helper function.", "shared = helper(a, b)"),
    "PY-QA-008": ("High cyclomatic complexity", "A function has many independent decision paths.", "Decompose the function and simplify conditional logic.", "Split branches into small validated helpers."),
}


def _finding(rule_id, node, description, line=None, **overrides):
    rule = {
        "rule_id": rule_id,
        "title": QUALITY_RULES[rule_id][0],
        "description": description,
        "explanation": description,
        "category": "Quality" if rule_id not in {"PY-QA-002"} else "Bug",
        "category_group": "Maintainability",
        "severity": "Low",
        "cwe": "",
        "line": line if line is not None else getattr(node, "lineno", 1),
        "column": getattr(node, "col_offset", 0) + 1,
        "source": "Local Python quality rules",
        "recommendation": QUALITY_RULES[rule_id][2],
        "suggested_fix": QUALITY_RULES[rule_id][3],
        "potential_impact": "Reduced readability and higher risk of future defects.",
        "verified": True,
        "strength": .80,
        "certainty": .82,
        "reliability": .88,
        "context": .80,
        "independent": None,
        "context_dependent": False,
        "evidence_description": description,
        "fix_code": "",
        "fix_valid": False,
    }
    rule.update(overrides)
    return rule


def analyze_quality(code, tree=None, metrics=None):
    findings = []
    tree = tree or ast.parse(code)
    metrics = metrics or calculate_metrics(code, tree)

    imported = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported[alias.asname or alias.name.split(".")[0]] = node
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name != "*":
                    imported[alias.asname or alias.name] = node
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    used |= {n.value.id for n in ast.walk(tree) if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)}
    for name, node in imported.items():
        if name not in used:
            findings.append(_finding("PY-QA-001", node, f"Imported name '{name}' is never referenced."))

    for func in (n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))):
        stores = [n for n in ast.walk(func) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store) and n.id not in {"self", "cls"} and not n.id.startswith("_")]
        loads = {n.id for n in ast.walk(func) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
        for name in stores:
            if name.id not in loads:
                findings.append(_finding("PY-QA-002", name, f"Local variable '{name.id}' is assigned but never read.", strength=.72, certainty=.75, verified=False))
        if len(func.body) > 60:
            findings.append(_finding("PY-QA-003", func, f"Function '{func.name}' has {len(func.body)} top-level statements."))
        if metrics.get("max_nesting", 0) > 4:
            findings.append(_finding("PY-QA-004", func, f"Control flow in '{func.name}' exceeds four nesting levels.", verified=False, strength=.70))
        bare = func.name.strip("_")
        if len(bare) < 2 or any(character.isupper() for character in bare):
            findings.append(_finding("PY-QA-005", func, f"Function name '{func.name}' is short or not snake_case."))
        if len(func.body) > 3 and ast.get_docstring(func) is None:
            findings.append(_finding("PY-QA-006", func, f"Function '{func.name}' has no docstring.", verified=False, strength=.65))
        complexity = next((item["complexity"] for item in metrics.get("functions", []) if item["name"] == func.name), 0)
        if complexity > 10:
            findings.append(_finding("PY-QA-008", func, f"Function '{func.name}' has cyclomatic complexity {complexity}.", severity="Medium", verified=False, strength=.78))

    blocks = {}
    for func in (n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))):
        for statement in func.body:
            key = ast.dump(statement)
            blocks.setdefault(key, []).append((func, statement))
    for key, locations in blocks.items():
        if len(locations) > 1:
            _, statement = locations[0]
            findings.append(_finding("PY-QA-007", statement, "The same statement sequence appears in multiple functions.", verified=False, strength=.68))

    unique = {}
    for item in findings:
        unique.setdefault((item["rule_id"], item["line"], item["column"]), item)
    return list(unique.values())
