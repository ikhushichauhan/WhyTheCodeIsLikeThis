"""
Tests for Step 4 — Python AST-Based Deprecated Flask API Scanner (code_scanner.py).
Verifies all 10 required test cases using isolated small test fixtures.
"""

import os
import unittest
import code_scanner


class TestCodeScanner(unittest.TestCase):

    def test_01_before_first_request_detection(self):
        """1. app.before_first_request detection as decorator and attribute."""
        code = """
from flask import Flask, Blueprint

app = Flask(__name__)
bp = Blueprint('bp', __name__)

@app.before_first_request
def setup_app():
    pass

@bp.before_app_first_request
def setup_bp():
    pass

app.before_first_request(setup_app)
"""
        res = code_scanner.scan_code(code, file_name="app.py")
        self.assertTrue(res.success)
        self.assertEqual(res.total_findings, 3)
        for f in res.findings:
            self.assertEqual(f.symbol, "app.before_first_request")
            self.assertIn("factory function", f.explanation)
            self.assertEqual(f.dep_version, "2.2.0")
            self.assertEqual(f.rem_version, "2.3.0")

    def test_02_got_first_request_detection(self):
        """2. got_first_request detection as attribute access."""
        code = """
from flask import Flask

app = Flask(__name__)

if not app.got_first_request:
    print("Not yet started")

val = current_app.got_first_request
"""
        res = code_scanner.scan_code(code, file_name="views.py")
        self.assertTrue(res.success)
        self.assertEqual(res.total_findings, 2)
        for f in res.findings:
            self.assertEqual(f.symbol, "got_first_request")
            self.assertEqual(f.detection_type, "attribute_access")
            self.assertEqual(f.dep_version, "2.3.0")
            self.assertEqual(f.rem_version, "3.0.0")

    def test_03_test_client_as_tuple_detection(self):
        """3. test_client.as_tuple detection in test calls and attributes."""
        code = """
with app.test_client() as client:
    resp = client.get('/', as_tuple=True)
    post_resp = client.post('/submit', as_tuple=False)
    raw = client.as_tuple
"""
        res = code_scanner.scan_code(code, file_name="test_app.py")
        self.assertTrue(res.success)
        self.assertEqual(res.total_findings, 3)
        for f in res.findings:
            self.assertEqual(f.symbol, "test_client.as_tuple")
            self.assertEqual(f.dep_version, "2.0.3")
            self.assertEqual(f.rem_version, "2.1.0")

    def test_04_unrelated_attributes_not_flagged(self):
        """4. Unrelated attributes, variables, and functions are not flagged (zero false positives)."""
        code = """
from collections import namedtuple

# Standard Flask methods that are NOT deprecated
app.route('/home')
app.run(debug=True)
client.get('/home')
client.post('/data', data={'key': 'val'})

# Unrelated object attribute named as_tuple
Point = namedtuple('Point', ['x', 'y'])
pt = Point(1, 2)
coords = pt.as_tuple() if hasattr(pt, 'as_tuple') else None

# Plain variable or function definitions using similar names
as_tuple = True
before_first_request = "hello"

def got_first_request():
    return True

def before_first_request():
    return False
"""
        res = code_scanner.scan_code(code, file_name="safe_code.py")
        self.assertTrue(res.success)
        self.assertEqual(res.total_findings, 0, f"Expected 0 findings, got: {[f.symbol for f in res.findings]}")

    def test_05_empty_source_code(self):
        """5. Empty and whitespace-only source code handled gracefully."""
        for empty_val in ["", "   \n\t  \n", None]:
            res = code_scanner.scan_code(empty_val, file_name="empty.py")
            self.assertTrue(res.success)
            self.assertEqual(res.total_findings, 0)
            self.assertIsNone(res.error)

    def test_06_invalid_python_syntax(self):
        """6. Invalid Python syntax caught gracefully without crashing."""
        broken_code = """
def unclosed_function(
    return 42
"""
        res = code_scanner.scan_code(broken_code, file_name="broken.py")
        self.assertFalse(res.success)
        self.assertEqual(res.total_findings, 0)
        self.assertIsNotNone(res.error)
        self.assertIn("SyntaxError", res.error)

    def test_07_multiple_findings_in_one_file(self):
        """7. Multiple distinct findings in one file correctly found."""
        code = """
from flask import Flask

app = Flask(__name__)

@app.before_first_request
def init_db():
    pass

if not app.got_first_request:
    init_db()

with app.test_client() as client:
    res, env = client.get('/', as_tuple=True)
"""
        res = code_scanner.scan_code(code, file_name="legacy_app.py")
        self.assertTrue(res.success)
        self.assertEqual(res.total_findings, 3)
        detected_symbols = [f.symbol for f in res.findings]
        self.assertIn("app.before_first_request", detected_symbols)
        self.assertIn("got_first_request", detected_symbols)
        self.assertIn("test_client.as_tuple", detected_symbols)

    def test_08_correct_line_number_reporting(self):
        """8. Correct 1-based line number reporting for AST nodes."""
        code = (
            "# Line 1\n"
            "# Line 2\n"
            "@app.before_first_request\n"  # Line 3
            "def fn(): pass\n"            # Line 4
            "# Line 5\n"
            "x = app.got_first_request\n"  # Line 6
        )
        res = code_scanner.scan_code(code, file_name="lines.py")
        self.assertTrue(res.success)
        self.assertEqual(res.total_findings, 2)
        self.assertEqual(res.findings[0].line, 3)
        self.assertEqual(res.findings[0].symbol, "app.before_first_request")
        self.assertEqual(res.findings[1].line, 6)
        self.assertEqual(res.findings[1].symbol, "got_first_request")

    def test_09_version_aware_status(self):
        """9. Version-aware status correctly distinguishes deprecated from removed and not-yet-deprecated."""
        code = "@app.before_first_request\ndef init(): pass"

        # Deprecated in 2.2.0, removed in 2.3.0
        # Target 2.1.0 -> Not yet deprecated
        r_pre = code_scanner.scan_code(code, target_version="2.1.0")
        self.assertEqual(r_pre.findings[0].status, "Not yet deprecated")

        # Target 2.2.0 -> Deprecated
        r_dep = code_scanner.scan_code(code, target_version="2.2.0")
        self.assertEqual(r_dep.findings[0].status, "Deprecated")

        # Target 2.3.0 -> Removed
        r_rem = code_scanner.scan_code(code, target_version="2.3.0")
        self.assertEqual(r_rem.findings[0].status, "Removed")

        # Target None -> Reports known lifecycle milestones without claiming incompatibility
        r_none = code_scanner.scan_code(code, target_version=None)
        self.assertIn("Removed in Flask 2.3.0", r_none.findings[0].status)
        self.assertIn("Deprecated in 2.2.0", r_none.findings[0].status)

    def test_10_no_code_execution(self):
        """10. Scanner never executes user-submitted Python code (no eval, exec, side-effects)."""
        marker_var = "TEST_AST_SCANNER_EXECUTION_FLAG"
        if marker_var in os.environ:
            del os.environ[marker_var]

        malicious_code = f"""
import os
os.environ['{marker_var}'] = 'EXECUTED'
raise RuntimeError('Code should NEVER be executed!')
"""
        res = code_scanner.scan_code(malicious_code, file_name="untrusted.py")
        self.assertTrue(res.success)
        # Verify the code was never executed
        self.assertNotIn(marker_var, os.environ, "SECURITY VIOLATION: User code was executed!")


if __name__ == "__main__":
    unittest.main()
