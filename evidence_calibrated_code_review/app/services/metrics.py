"""Cyclomatic complexity and maintainability metrics computed from an AST."""
import ast

COMPLEXITY_NODES = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler,
                    ast.With, ast.AsyncWith, ast.Assert, ast.IfExp)


def _complexity(node):
    score = 1
    for child in ast.walk(node):
        if isinstance(child, COMPLEXITY_NODES):
            score += 1
        elif isinstance(child, ast.BoolOp):
            score += len(child.values) - 1
        elif isinstance(child, ast.comprehension):
            score += 1 + len(child.ifs)
        elif isinstance(child, getattr(ast, "Match", ())):  # pragma: no cover - 3.10+
            score += len(getattr(child, "cases", []))
    return score


def _max_depth(node, depth=0):
    best = depth
    for child in ast.iter_child_nodes(node):
        blocks = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith, ast.Try)
        best = max(best, _max_depth(child, depth + 1 if isinstance(child, blocks) else depth))
    return best


def calculate_metrics(code, tree=None):
    """Return code metrics without ever executing the submitted source."""
    if tree is None:
        tree = ast.parse(code)
    functions = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append({
                "name": node.name,
                "line": node.lineno,
                "complexity": _complexity(node),
                "statements": len(node.body),
                "has_docstring": ast.get_docstring(node) is not None,
            })
    classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    rows = code.splitlines()
    loc = sum(1 for row in rows if row.strip() and not row.lstrip().startswith("#"))
    total_complexity = sum(item["complexity"] for item in functions)
    max_complexity = max((item["complexity"] for item in functions), default=0)
    nesting = _max_depth(tree)
    documented = sum(1 for item in functions if item["has_docstring"])
    doc_ratio = documented / len(functions) if functions else 0.0
    maintainability = max(0.0, min(100.0,
        100 - max(0, max_complexity - 5) * 4 - max(0, nesting - 3) * 4 - (1 - doc_ratio) * 10
    ))
    return {
        "lines_of_code": loc,
        "total_lines": len(rows),
        "function_count": len(functions),
        "class_count": len(classes),
        "total_complexity": total_complexity,
        "max_complexity": max_complexity,
        "average_complexity": round(total_complexity / len(functions), 2) if functions else 0,
        "max_nesting": nesting,
        "documented_functions": documented,
        "documentation_ratio": round(doc_ratio, 3),
        "maintainability_index": round(maintainability, 1),
        "functions": functions,
    }
