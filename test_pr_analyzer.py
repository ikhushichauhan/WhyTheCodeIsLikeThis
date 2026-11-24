"""
Tests for Step 5 — GitHub Pull Request Diff Analyzer (pr_analyzer.py).
Verifies all required scenarios using isolated mocked API responses.
"""

import unittest
from unittest.mock import MagicMock, patch
import requests

import pr_analyzer


class TestPRAnalyzer(unittest.TestCase):

    def test_01_valid_public_pr_url_parsing(self):
        """1. Valid public PR URL parsing for various standard URL formats."""
        valid_urls = [
            ("https://github.com/pallets/flask/pull/4997", "pallets", "flask", 4997),
            ("https://github.com/pallets/flask/pull/4997/", "pallets", "flask", 4997),
            ("https://github.com/pallets/flask/pull/4997/files", "pallets", "flask", 4997),
            ("http://github.com/owner/repo/pull/123", "owner", "repo", 123),
            ("github.com/owner/repo.git/pull/456", "owner", "repo", 456),
            ("https://www.github.com/org-name/repo_name.js/pull/999?diff=unified#issuecomment-1", "org-name", "repo_name.js", 999),
        ]
        for url, expected_owner, expected_repo, expected_num in valid_urls:
            owner, repo, num, err = pr_analyzer.parse_pr_url(url)
            self.assertIsNone(err, f"Expected no error for {url}")
            self.assertEqual(owner, expected_owner)
            self.assertEqual(repo, expected_repo)
            self.assertEqual(num, expected_num)

    def test_02_invalid_url_handling(self):
        """2. Invalid URL formats rejected with descriptive error."""
        invalid_urls = [
            "https://gitlab.com/owner/repo/pull/123",
            "https://github.com/owner/repo/issues/123",
            "https://github.com/owner",
            "https://github.com/owner/repo",
            "not_a_valid_url",
            "",
            None,
        ]
        for url in invalid_urls:
            owner, repo, num, err = pr_analyzer.parse_pr_url(url)
            self.assertIsNotNone(err, f"Expected error for {url}")
            self.assertIsNone(owner)
            self.assertIsNone(repo)
            self.assertIsNone(num)

    def test_03_invalid_pr_number(self):
        """3. Invalid PR numbers (0, negative, non-numeric) rejected."""
        invalid_numbers = [
            "https://github.com/owner/repo/pull/0",
            "https://github.com/owner/repo/pull/-10",
        ]
        for url in invalid_numbers:
            owner, repo, num, err = pr_analyzer.parse_pr_url(url)
            self.assertIsNotNone(err)
            self.assertIn("greater than zero", err)

    def test_04_mocked_github_api_response(self):
        """4. Successful PR metadata and file list fetched via mocked API."""
        mock_meta = {
            "title": "Migrate deprecated Flask hooks",
            "state": "open",
            "html_url": "https://github.com/test-owner/test-repo/pull/1",
            "user": {"login": "flask-dev"},
            "changed_files": 1,
        }
        mock_files = [
            {
                "filename": "app.py",
                "status": "modified",
                "additions": 2,
                "deletions": 0,
                "patch": "@@ -10,3 +10,5 @@ def setup():\n     pass\n+    @app.before_first_request\n+    def init(): pass\n"
            }
        ]

        session = MagicMock()
        resp_meta = MagicMock()
        resp_meta.status_code = 200
        resp_meta.json.return_value = mock_meta

        resp_files = MagicMock()
        resp_files.status_code = 200
        resp_files.json.return_value = mock_files

        session.get.side_effect = [resp_meta, resp_files]

        result = pr_analyzer.analyze_pr("https://github.com/test-owner/test-repo/pull/1", session=session)
        self.assertTrue(result.success)
        self.assertEqual(result.owner, "test-owner")
        self.assertEqual(result.repo, "test-repo")
        self.assertEqual(result.pr_number, 1)
        self.assertEqual(result.pr_title, "Migrate deprecated Flask hooks")
        self.assertEqual(result.total_findings, 1)
        self.assertEqual(result.findings[0].symbol, "app.before_first_request")

    def test_05_pr_with_deprecated_api_in_added_code(self):
        """5. PR with a supported deprecated API in added (+) code marked as 'added'."""
        patch_text = """@@ -25,4 +25,6 @@ def init_app():
     config = load_config()
-    old_call()
+    if not app.got_first_request:
+        perform_init()
     return True
"""
        findings, _ = pr_analyzer.analyze_python_patch("server.py", patch_text, target_version="2.3.0")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].symbol, "got_first_request")
        self.assertEqual(findings[0].change_type, "added")
        self.assertEqual(findings[0].status, "Deprecated")
        self.assertEqual(findings[0].file_path, "server.py")

    def test_06_pr_with_api_only_in_unchanged_context(self):
        """6. PR with the API only in unchanged context (leading space) marked as 'context'."""
        patch_text = """@@ -25,6 +25,7 @@ def init_app():
     config = load_config()
     if not app.got_first_request:
         perform_init()
+    new_logger.info("Initialized")
     return True
"""
        findings, _ = pr_analyzer.analyze_python_patch("server.py", patch_text, target_version="2.3.0")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].symbol, "got_first_request")
        self.assertEqual(findings[0].change_type, "context")
        self.assertEqual(findings[0].status, "Deprecated")

    def test_07_pr_with_no_python_files(self):
        """7. PR with only non-Python files (docs, configs) skipped with reason."""
        mock_meta = {"title": "Update documentation", "state": "closed", "user": {"login": "doc-writer"}}
        mock_files = [
            {"filename": "README.md", "status": "modified", "additions": 10, "deletions": 2, "patch": "@@ -1,2 +1,3 @@\n+Docs update"},
            {"filename": "config.yaml", "status": "modified", "additions": 3, "deletions": 1, "patch": "@@ -1,2 +1,3 @@\n+port: 8080"}
        ]

        session = MagicMock()
        resp_meta = MagicMock(status_code=200, json=lambda: mock_meta)
        resp_files = MagicMock(status_code=200, json=lambda: mock_files)
        session.get.side_effect = [resp_meta, resp_files]

        result = pr_analyzer.analyze_pr("https://github.com/owner/repo/pull/5", session=session)
        self.assertTrue(result.success)
        self.assertEqual(result.python_files_count, 0)
        self.assertEqual(result.total_findings, 0)
        self.assertEqual(len(result.skipped_files), 2)
        self.assertIn("Non-Python", result.skipped_files[0].reason)

    def test_08_missing_patch_handling(self):
        """8. Python file without patch is marked skipped with explicit explanation, not silently claimed scanned."""
        mock_meta = {"title": "Delete legacy file and huge refactor", "state": "open", "user": {"login": "cleaner"}}
        mock_files = [
            {
                "filename": "deleted_legacy.py",
                "status": "removed",
                "additions": 0,
                "deletions": 150,
                # patch is omitted by GitHub when file is removed or large
            },
            {
                "filename": "giant_generated.py",
                "status": "modified",
                "additions": 4000,
                "deletions": 200,
                "changes": 4200,
                # patch omitted due to size
            }
        ]

        session = MagicMock()
        resp_meta = MagicMock(status_code=200, json=lambda: mock_meta)
        resp_files = MagicMock(status_code=200, json=lambda: mock_files)
        session.get.side_effect = [resp_meta, resp_files]

        result = pr_analyzer.analyze_pr("https://github.com/owner/repo/pull/8", session=session)
        self.assertTrue(result.success)
        self.assertEqual(len(result.analyzed_files), 0)
        self.assertEqual(len(result.skipped_files), 2)
        self.assertIn("File deleted", result.skipped_files[0].reason)
        self.assertIn("threshold", result.skipped_files[1].reason)
        self.assertEqual(result.total_findings, 0)

    def test_09_rate_limit_response(self):
        """9. Rate limit response (HTTP 403/429) handled gracefully with descriptive error."""
        session = MagicMock()
        resp_meta = MagicMock()
        resp_meta.status_code = 403
        resp_meta.headers = {"content-type": "application/json"}
        resp_meta.json.return_value = {
            "message": "API rate limit exceeded for IP xxx. See https://docs.github.com/rest/overview/resources-in-the-rest-api#rate-limiting"
        }
        session.get.return_value = resp_meta

        result = pr_analyzer.analyze_pr("https://github.com/owner/repo/pull/10", session=session)
        self.assertFalse(result.success)
        self.assertIn("rate limit exceeded", result.error.lower())

    def test_10_network_failure(self):
        """10. Network failure (ConnectionError / Timeout) caught without crashing."""
        session = MagicMock()
        session.get.side_effect = requests.exceptions.ConnectionError("Connection refused by peer")

        result = pr_analyzer.analyze_pr("https://github.com/owner/repo/pull/11", session=session)
        self.assertFalse(result.success)
        self.assertIn("Network connection error", result.error)

    def test_11_correct_file_and_line_mapping(self):
        """11. Line numbers in findings correspond reliably to target new file line numbers."""
        patch_text = """@@ -50,5 +50,8 @@ class TestViews:
     def test_home(self, client):
         res = client.get('/')
+        # Test with as_tuple
+        tuple_res = client.get('/feed', as_tuple=True)
         assert res.status_code == 200
"""
        findings, _ = pr_analyzer.analyze_python_patch("tests/test_views.py", patch_text, target_version="2.1.0")
        self.assertEqual(len(findings), 1)
        f = findings[0]
        self.assertEqual(f.symbol, "test_client.as_tuple")
        # Line 50 is def test_home:, line 51 is res = client.get('/')
        # Line 52 is # Test with as_tuple, line 53 is tuple_res = client.get('/feed', as_tuple=True)
        self.assertEqual(f.line_number, 53)
        self.assertEqual(f.change_type, "added")
        self.assertEqual(f.file_path, "tests/test_views.py")


if __name__ == "__main__":
    unittest.main()


class TestIncompleteSnippetHandling(unittest.TestCase):
    """Verification tests for incomplete diff hunk handling (Step 5 finalization)."""

    def test_12_deprecated_api_in_function_body_without_def(self):
        """Scenario 1: Deprecated API inside a function whose def is outside the diff hunk.
        The hunk starts mid-function (indented body), so the whole-hunk parse may fail.
        The scanner must still detect the API and mark it with reduced confidence."""
        # Hunk from inside a function — no 'def' line, starts with indented body.
        # The 'else:' orphan clause triggers SyntaxError for whole-hunk parse.
        patch_text = """@@ -45,5 +45,8 @@ def setup_app(app):
     config = load_config()
 else:
+    if not app.got_first_request:
+        perform_init()
     return app
"""
        findings, had_incomplete = pr_analyzer.analyze_python_patch("utils.py", patch_text)
        # Should detect got_first_request
        self.assertTrue(len(findings) >= 1, "Expected at least one finding for got_first_request")
        symbols = [f.symbol for f in findings]
        self.assertIn("got_first_request", symbols)
        # Verify the finding from incomplete context is marked with reduced confidence
        gfr = [f for f in findings if f.symbol == "got_first_request"][0]
        self.assertEqual(gfr.change_type, "added")
        # had_incomplete should be True because the whole-hunk parse fails
        self.assertTrue(had_incomplete, "Expected had_incomplete_snippets to be True for orphan else block")
        self.assertIn("medium", gfr.confidence.lower(),
                       "Findings from incomplete hunks should have medium confidence")

    def test_13_deprecated_api_in_class_method_without_class_def(self):
        """Scenario 2: Deprecated API inside a class method with missing class context.
        The hunk shows only method-level code from inside a class whose 'class' line
        is outside the diff."""
        patch_text = """@@ -100,4 +100,7 @@ class FlaskApp:
     def run_checks(self):
         # run health checks
+        @self.before_first_request
+        def on_first():
+            pass
         return True
"""
        findings, had_incomplete = pr_analyzer.analyze_python_patch("server.py", patch_text)
        self.assertTrue(len(findings) >= 1, "Expected at least one finding for before_first_request")
        symbols = [f.symbol for f in findings]
        self.assertIn("app.before_first_request", symbols)
        bfr = [f for f in findings if f.symbol == "app.before_first_request"][0]
        self.assertEqual(bfr.change_type, "added")

    def test_14_valid_added_api_in_complete_function(self):
        """Scenario 3: Valid added API occurrence in a complete function.
        The hunk contains a complete function definition — full AST parse succeeds.
        Confidence should be 'high'."""
        patch_text = """@@ -1,0 +1,6 @@
+def init_app(app):
+    @app.before_first_request
+    def setup():
+        db.init()
+    return app
"""
        findings, had_incomplete = pr_analyzer.analyze_python_patch("app_factory.py", patch_text)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].symbol, "app.before_first_request")
        self.assertEqual(findings[0].change_type, "added")
        self.assertEqual(findings[0].confidence, "high")
        self.assertFalse(had_incomplete, "Complete function hunk should not flag incomplete")

    def test_15_deprecated_api_only_in_unchanged_context(self):
        """Scenario 4: Deprecated API appearing only in unchanged context lines.
        The finding should still be reported but marked as 'context' not 'added'."""
        patch_text = """@@ -10,5 +10,6 @@ def legacy_setup(app):
     @app.before_first_request
     def startup():
         init_db()
+    app.logger.info("setup complete")
     return app
"""
        findings, had_incomplete = pr_analyzer.analyze_python_patch("legacy.py", patch_text)
        self.assertTrue(len(findings) >= 1)
        bfr = [f for f in findings if f.symbol == "app.before_first_request"][0]
        self.assertEqual(bfr.change_type, "context",
                         "API in unchanged context lines should be marked as 'context'")
        self.assertFalse(had_incomplete, "Complete hunk should not flag incomplete")

    def test_16_incomplete_snippet_marked_partially_analyzed_in_pr(self):
        """End-to-end: analyze_pr marks a file as 'partially_analyzed' when
        hunks contain incomplete syntax and sets reduced confidence on findings."""
        mock_meta = {
            "title": "Fix legacy setup",
            "state": "open",
            "html_url": "https://github.com/owner/repo/pull/42",
            "user": {"login": "dev"},
        }
        # Patch with an orphan 'else:' that triggers fallback
        mock_files = [{
            "filename": "setup.py",
            "status": "modified",
            "additions": 2,
            "deletions": 0,
            "patch": "@@ -20,3 +20,5 @@ def configure():\n else:\n+    if not app.got_first_request:\n+        init()\n     pass\n",
        }]

        session = MagicMock()
        resp_meta = MagicMock(status_code=200, json=lambda: mock_meta)
        resp_files = MagicMock(status_code=200, json=lambda: mock_files)
        session.get.side_effect = [resp_meta, resp_files]

        result = pr_analyzer.analyze_pr("https://github.com/owner/repo/pull/42", session=session)
        self.assertTrue(result.success)
        # File should be partially_analyzed
        self.assertEqual(len(result.analyzed_files), 1)
        self.assertEqual(result.analyzed_files[0].status, "partially_analyzed")
        self.assertIn("incomplete syntax", result.analyzed_files[0].reason.lower())
        # Finding should exist with medium confidence
        self.assertTrue(result.total_findings >= 1)
        gfr = [f for f in result.findings if f.symbol == "got_first_request"]
        self.assertTrue(len(gfr) >= 1)
        self.assertIn("medium", gfr[0].confidence.lower())
