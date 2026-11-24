"""Local deterministic Python analysis. Submitted source is parsed, never executed."""
import ast

from app.services.metrics import calculate_metrics
from app.services.quality_analyzer import analyze_quality
from app.services.security_rules import LEXICAL_PATTERNS, rule


def _syntax_finding(exc):
    return {
        "rule_id": "PY-SYN-001",
        "title": "Python syntax error",
        "description": exc.msg,
        "explanation": f"Python's parser rejected this source at line {exc.lineno or 1}, column {exc.offset or 1}.",
        "category": "Syntax",
        "category_group": "Syntax",
        "severity": "High",
        "cwe": "",
        "line": exc.lineno or 1,
        "column": exc.offset or 1,
        "source": "Python AST",
        "recommendation": "Fix the syntax error before running or reviewing this module.",
        "suggested_fix": "Inspect the indicated line and correct its syntax.",
        "potential_impact": "The module cannot be imported or executed until the syntax is corrected.",
        "verified": True, "strength": .98, "certainty": .99, "reliability": .99, "context": .95,
        "independent": None, "context_dependent": False,
        "evidence_description": "Python's parser rejected the submitted source.",
        "fix_code": "", "fix_valid": False,
    }


def analyze_python(code):
    """Return rule-based findings for Python source without running it."""
    findings = []
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return [_syntax_finding(exc)]
    except (ValueError, TypeError, RecursionError) as exc:
        return [{
            "rule_id": "PY-SYN-002", "title": "Python source could not be parsed",
            "description": str(exc) or "The parser could not process the submitted source.",
            "explanation": "The submitted text contains data the parser cannot process.",
            "category": "Syntax", "category_group": "Syntax", "severity": "Medium", "cwe": "",
            "line": 1, "column": 1, "source": "Python AST",
            "recommendation": "Verify the submitted source is valid text before reviewing it.",
            "suggested_fix": "Remove embedded null bytes or unusually deep syntax.",
            "potential_impact": "Automated analysis cannot inspect this source.",
            "verified": True, "strength": .90, "certainty": .95, "reliability": .95, "context": .90,
            "independent": None, "context_dependent": False,
            "evidence_description": str(exc), "fix_code": "", "fix_valid": False,
        }]

    metrics = calculate_metrics(code, tree)

    def add(rule_id, node, description, **overrides):
        finding = rule(rule_id, node, description=description, explanation=description, **overrides)
        findings.append(finding)

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = func.id if isinstance(func, ast.Name) else None
            attr = func.attr if isinstance(func, ast.Attribute) else None
            owner = func.value.id if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) else None

            if name == "eval":
                add("PY-SEC-001", node, "eval evaluates a string as Python code and can execute attacker-controlled input.")
            if name == "exec":
                add("PY-SEC-002", node, "exec executes arbitrary Python statements from a string.")
            if owner == "pickle" and attr in {"load", "loads"} or name in {"pickle_loads", "pickle_load"}:
                add("PY-SEC-005", node, "Pickle deserialization can execute code when the input is untrusted.")
            if owner == "yaml" and attr == "load" and not node.args[-1:] and not any(k.arg == "Loader" for k in node.keywords):
                add("PY-SEC-005", node, "yaml.load without a safe loader can construct arbitrary Python objects.", strength=.80)
            if owner == "marshal" and attr in {"load", "loads"}:
                add("PY-SEC-005", node, "Marshal deserialization of untrusted data is unsafe.", strength=.85)
            if owner == "os" and attr in {"system", "popen"}:
                add("PY-SEC-006", node, "OS shell helpers may interpret user-controlled command text.")
            if attr in {"run", "call", "Popen", "check_call", "check_output"} and any(k.arg == "shell" and isinstance(k.value, ast.Constant) and k.value.value is True for k in node.keywords):
                add("PY-SEC-007", node, "A subprocess call enables shell interpretation.")
            if (name == "execute" or attr == "execute") and node.args and isinstance(node.args[0], ast.BinOp) and isinstance(node.args[0].op, (ast.Add, ast.Mod)):
                add("PY-SEC-003", node, "A SQL execution call receives a concatenated or formatted query.")
            if owner == "tempfile" and attr == "mktemp":
                add("PY-SEC-008", node, "tempfile.mktemp is vulnerable to race conditions.")
            if owner == "hashlib" and attr in {"md5", "sha1"}:
                add("PY-SEC-009", node, f"hashlib.{attr} provides weak collision resistance.", strength=.80)
            if owner == "random" and attr in {"random", "randint", "choice", "uniform"}:
                add("PY-SEC-010", node, f"random.{attr} is not suitable for security-sensitive values.", strength=.70)
            if name == "open" and node.args and not isinstance(node.args[0], ast.Constant):
                add("PY-SEC-011", node, "A file path is built dynamically; validate it against an allowed base directory.", strength=.62)
            if name == "run" and any(k.arg == "debug" and isinstance(k.value, ast.Constant) and k.value.value is True for k in node.keywords):
                add("PY-SEC-012", node, "Debug mode is explicitly enabled in this configuration.")

        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            names = [x.id.lower() for target in node.targets for x in ast.walk(target) if isinstance(x, ast.Name)]
            value = node.value.value
            if any(any(secret in name for secret in ("password", "passwd", "secret", "token")) for name in names) and len(value) >= 4:
                add("PY-SEC-004", node, "A credential-like variable is assigned a string literal.")
            elif any("api_key" in name or "apikey" in name for name in names) and len(value) >= 8:
                add("PY-SEC-013", node, "An API-key-like variable is assigned a string literal.")

        if isinstance(node, ast.Assign) and isinstance(node.value, ast.BinOp) and isinstance(node.value.op, ast.Add):
            left = node.value.left
            if isinstance(left, ast.Constant) and isinstance(left.value, str) and any(word in left.value.lower() for word in ("select ", "insert ", "update ", "delete ")):
                add("PY-SEC-003", node, "A SQL statement is assembled with string concatenation.")

        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            if isinstance(node.right, ast.Constant) and node.right.value == 0:
                findings.append({
                    "rule_id": "PY-BUG-001", "title": "Division by zero",
                    "description": "The denominator is the literal zero, so this expression always raises ZeroDivisionError.",
                    "explanation": "The divisor is a constant zero at this location.",
                    "category": "Bug", "category_group": "Correctness", "severity": "High", "cwe": "",
                    "line": node.lineno, "column": node.col_offset + 1, "source": "Local Python AST rules",
                    "recommendation": "Correct the denominator or validate it before division.",
                    "suggested_fix": "if denominator != 0:\n    result = numerator / denominator",
                    "potential_impact": "This expression always raises an exception.",
                    "verified": True, "strength": .99, "certainty": .99, "reliability": .99, "context": .98,
                    "independent": None, "context_dependent": False,
                    "evidence_description": "The divisor is the literal 0.", "fix_code": "", "fix_valid": False,
                })
            elif isinstance(node.right, ast.Name):
                findings.append({
                    "rule_id": "PY-BUG-002", "title": "Potential division by zero",
                    "description": "A variable is used as a divisor; confirm it cannot be zero at the point of division.",
                    "explanation": "The divisor is dynamic, so its runtime value is not established by static evidence alone.",
                    "category": "Bug", "category_group": "Correctness", "severity": "Medium", "cwe": "",
                    "line": node.lineno, "column": node.col_offset + 1, "source": "Local Python AST rules",
                    "recommendation": "Validate the divisor or handle ZeroDivisionError where appropriate.",
                    "suggested_fix": "if divisor == 0:\n    return None",
                    "potential_impact": "A runtime exception may occur for zero-valued input.",
                    "verified": False, "strength": .73, "certainty": .70, "reliability": .85, "context": .58,
                    "independent": None, "context_dependent": True,
                    "evidence_description": "The divisor is a variable.", "fix_code": "", "fix_valid": False,
                })

        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], (ast.Is, ast.IsNot)) and isinstance(node.comparators[0], ast.Constant) and isinstance(node.comparators[0].value, (str, int, float, bool)):
            operator = "==" if isinstance(node.ops[0], ast.Is) else "!="
            findings.append({
                "rule_id": "PY-BUG-003", "title": "Identity comparison with a literal",
                "description": "The 'is' operator checks object identity; value equality is likely intended for this literal.",
                "explanation": "Identity comparison with a literal is rarely intended and depends on interpreter internals.",
                "category": "Bug", "category_group": "Correctness", "severity": "Medium", "cwe": "",
                "line": node.lineno, "column": node.col_offset + 1, "source": "Local Python AST rules",
                "recommendation": "Use == or != when comparing data values.",
                "suggested_fix": f"if value {operator} {node.comparators[0].value!r}",
                "potential_impact": "The comparison may produce surprising results for equal values.",
                "verified": False, "strength": .86, "certainty": .83, "reliability": .90, "context": .76,
                "independent": None, "context_dependent": True,
                "evidence_description": "Identity operator used with a literal comparator.", "fix_code": "", "fix_valid": False,
            })

        if isinstance(node, ast.ExceptHandler):
            broad = node.type is None or (isinstance(node.type, ast.Name) and node.type.id in {"Exception", "BaseException"})
            if broad and (not node.body or all(isinstance(statement, ast.Pass) for statement in node.body)):
                findings.append({
                    "rule_id": "PY-BUG-004", "title": "Exception is swallowed",
                    "description": "A broad exception handler suppresses errors without recording or handling them.",
                    "explanation": "A bare or broad except block with only pass discards failures silently.",
                    "category": "Bug", "category_group": "Correctness", "severity": "Medium", "cwe": "CWE-390",
                    "line": node.lineno, "column": node.col_offset + 1, "source": "Local Python AST rules",
                    "recommendation": "Catch expected exception types and log or propagate failures.",
                    "suggested_fix": "except (ValueError, OSError) as exc:\n    logger.warning('Operation failed: %s', exc)",
                    "potential_impact": "Errors may go unnoticed and leave the system in an invalid state.",
                    "verified": True, "strength": .92, "certainty": .94, "reliability": .92, "context": .90,
                    "independent": None, "context_dependent": False,
                    "evidence_description": "Broad exception handler contains only pass.", "fix_code": "", "fix_valid": False,
                })

        if isinstance(node, ast.For) and any(isinstance(child, ast.For) for child in ast.walk(node) if child is not node):
            findings.append({
                "rule_id": "PY-PERF-001", "title": "Nested loop may be costly",
                "description": "A loop contains another loop; runtime may grow with the product of collection sizes.",
                "explanation": "Nested iteration is present in the submitted source.",
                "category": "Performance", "category_group": "Efficiency", "severity": "Low", "cwe": "",
                "line": node.lineno, "column": node.col_offset + 1, "source": "Local Python AST rules",
                "recommendation": "Check input sizes and consider indexing or a more suitable algorithm.",
                "suggested_fix": "Build a lookup dictionary before iterating.",
                "potential_impact": "Potential quadratic or worse growth on large inputs.",
                "verified": False, "strength": .73, "certainty": .72, "reliability": .85, "context": .66,
                "independent": None, "context_dependent": True,
                "evidence_description": "A For node contains another For node.", "fix_code": "", "fix_valid": False,
            })

    for rule_id, pattern in LEXICAL_PATTERNS:
        for match in pattern.finditer(code):
            line = code.count("\n", 0, match.start()) + 1
            column = match.start() - (code.rfind("\n", 0, match.start()) + 1) + 1
            findings.append(rule(rule_id, None, line=line, column=column, verified=False))

    findings.extend(analyze_quality(code, tree, metrics))
    unique = {}
    for item in findings:
        unique.setdefault((item.get("rule_id") or item["title"], item["line"], item["column"]), item)
    return list(unique.values())
