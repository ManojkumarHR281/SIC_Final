from app.services.review_engine import review_code


def test_ast_detects_requested_security_and_bug_patterns():
    code = '''def vulnerable(user_input):
    password = "admin123"
    query = "SELECT * FROM users WHERE name = " + user_input
    result = eval(user_input)
    return query
'''
    found = review_code(code)
    titles = {x["title"] for x in found}
    assert "Unsafe eval usage" in titles
    assert "Possible SQL injection" in titles
    assert "Hardcoded credential" in titles
    assert all(0 <= x["confidence"] <= 1 for x in found)
    assert all(x["evidence"] for x in found)


def test_syntax_error_is_reported():
    assert review_code("def broken(:\n pass")
