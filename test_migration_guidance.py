"""
Tests for Step 7 — Evidence-Backed Migration Guidance (migration_guidance.py).

Verifies:
  1. All three curated APIs supported with exact verified milestones.
  2. Preserves verified maintainer guidance and quotes.
  3. No fabricated replacement for got_first_request (explicit refusal notice).
  4. Alias resolution (before_first_request, as_tuple).
  5. Unsupported API handling (returns None; refuses to invent guidance).
  6. Version-aware lifecycle evaluation (Removed, Deprecated, Not yet deprecated).
  7. Unavailable and invalid target version formats handled gracefully.
  8. Missing evidence / isolated test fixture handling.
  9. Reliable evidence links (Pallets Issues and PRs).
  10. Technically valid optional illustrative code examples (only when verified).
  11. End-to-end integration with scanner findings.
"""

import unittest

import migration_guidance
from code_scanner import scan_code


class TestMigrationGuidance(unittest.TestCase):

    def test_01_before_first_request_guidance(self):
        """1. app.before_first_request: verified milestones, maintainer guidance, and sources."""
        guidance = migration_guidance.get_migration_guidance("app.before_first_request")
        self.assertIsNotNone(guidance)
        self.assertEqual(guidance.symbol, "app.before_first_request")
        self.assertEqual(guidance.dep_version, "2.2.0")
        self.assertEqual(guidance.rem_version, "2.3.0")
        self.assertTrue(guidance.has_verified_replacement)
        self.assertIn("factory function", guidance.replacement.lower())
        self.assertIn("Configuration should be done before _running_ the application", guidance.source_quote)
        self.assertEqual(guidance.source_ref, 4605)

        # Primary source links
        urls = [link["url"] for link in guidance.evidence_links]
        self.assertIn("https://github.com/pallets/flask/issues/4605", urls)
        self.assertIn("https://github.com/pallets/flask/pull/4995", urls)

        # Code example is present and explicitly labeled
        self.assertTrue(guidance.has_code_example)
        self.assertIn("@app.before_first_request", guidance.before_code)
        self.assertIn("create_app", guidance.after_code)

    def test_02_got_first_request_no_fabricated_replacement(self):
        """2. got_first_request: verified milestones, no fabricated replacement API."""
        guidance = migration_guidance.get_migration_guidance("got_first_request")
        self.assertIsNotNone(guidance)
        self.assertEqual(guidance.symbol, "got_first_request")
        self.assertEqual(guidance.dep_version, "2.3.0")
        self.assertEqual(guidance.rem_version, "3.0.0")

        # Crucial Requirement: No fabricated replacement
        self.assertFalse(guidance.has_verified_replacement)
        self.assertIsNone(guidance.replacement)
        self.assertEqual(
            guidance.display_replacement,
            "No verified replacement guidance is currently available for this API."
        )

        # Crucial Requirement: No invented code snippet
        self.assertFalse(guidance.has_code_example)
        self.assertIsNone(guidance.before_code)
        self.assertIsNone(guidance.after_code)

        # Primary source links
        urls = [link["url"] for link in guidance.evidence_links]
        self.assertIn("https://github.com/pallets/flask/pull/4997", urls)
        self.assertIn("https://github.com/pallets/flask/pull/5223", urls)
        self.assertIn("property was missed", guidance.source_quote.lower())

    def test_03_test_client_as_tuple_guidance(self):
        """3. test_client.as_tuple: verified milestones, Werkzeug compatibility, and sources."""
        guidance = migration_guidance.get_migration_guidance("test_client.as_tuple")
        self.assertIsNotNone(guidance)
        self.assertEqual(guidance.symbol, "test_client.as_tuple")
        self.assertEqual(guidance.dep_version, "2.0.3")
        self.assertEqual(guidance.rem_version, "2.1.0")
        self.assertTrue(guidance.has_verified_replacement)
        self.assertIn("TestResponse", guidance.replacement)
        self.assertIn("response.request.environ", guidance.replacement)

        # Primary source links
        urls = [link["url"] for link in guidance.evidence_links]
        self.assertIn("https://github.com/pallets/flask/pull/4341", urls)
        self.assertIn("https://github.com/pallets/flask/pull/4417", urls)

        # Code example
        self.assertTrue(guidance.has_code_example)
        self.assertIn("as_tuple=True", guidance.before_code)
        self.assertIn("response.request.environ", guidance.after_code)

    def test_04_alias_resolution(self):
        """4. Aliases resolve to canonical decision records."""
        # before_first_request -> app.before_first_request
        g1 = migration_guidance.get_migration_guidance("before_first_request")
        self.assertIsNotNone(g1)
        self.assertEqual(g1.symbol, "app.before_first_request")

        # before_app_first_request -> app.before_first_request
        g2 = migration_guidance.get_migration_guidance("before_app_first_request")
        self.assertIsNotNone(g2)
        self.assertEqual(g2.symbol, "app.before_first_request")

        # as_tuple -> test_client.as_tuple
        g3 = migration_guidance.get_migration_guidance("as_tuple")
        self.assertIsNotNone(g3)
        self.assertEqual(g3.symbol, "test_client.as_tuple")

    def test_05_unsupported_api_returns_none(self):
        """5. Unsupported/unknown API returns None; refuses to fabricate guidance."""
        self.assertIsNone(migration_guidance.get_migration_guidance("jsonify"))
        self.assertIsNone(migration_guidance.get_migration_guidance("url_for"))
        self.assertIsNone(migration_guidance.get_migration_guidance(""))
        self.assertIsNone(migration_guidance.get_migration_guidance(None))

    def test_06_target_version_removed(self):
        """6. Target version where API is confirmed removed."""
        # app.before_first_request removed in 2.3.0
        g = migration_guidance.get_migration_guidance("app.before_first_request", target_version="2.3.0")
        self.assertTrue(g.target_version_evaluated)
        self.assertIn("Removed in Flask 2.3.0", g.version_status)
        self.assertIn("Incompatible", g.version_status)
        self.assertIsNone(g.target_version_notice)

        # Higher version (Flask 3.0.0 >= 2.3.0)
        g3 = migration_guidance.get_migration_guidance("app.before_first_request", target_version="3.0.0")
        self.assertTrue(g3.target_version_evaluated)
        self.assertIn("Removed", g3.version_status)

    def test_07_target_version_deprecated_not_removed(self):
        """7. Target version where API is deprecated but not yet removed."""
        # got_first_request deprecated in 2.3.0, removed in 3.0.0. Target: 2.3.0
        g = migration_guidance.get_migration_guidance("got_first_request", target_version="2.3.0")
        self.assertTrue(g.target_version_evaluated)
        self.assertIn("Deprecated in Flask 2.3.0", g.version_status)
        self.assertNotIn("Incompatible", g.version_status)

    def test_08_target_version_not_yet_deprecated(self):
        """8. Target version earlier than deprecation milestone."""
        # got_first_request deprecated in 2.3.0. Target: 2.1.0
        g = migration_guidance.get_migration_guidance("got_first_request", target_version="2.1.0")
        self.assertTrue(g.target_version_evaluated)
        self.assertIn("Not yet deprecated in Flask 2.1.0", g.version_status)

    def test_09_target_version_unavailable_evidence(self):
        """9. Valid version string but outside verified milestone records."""
        g = migration_guidance.get_migration_guidance("app.before_first_request", target_version="99.0.0")
        self.assertFalse(g.target_version_evaluated)
        self.assertIsNotNone(g.target_version_notice)
        self.assertIn("Unavailable version evidence", g.target_version_notice)
        self.assertIn("99.0.0", g.target_version_notice)

    def test_10_target_version_invalid_format(self):
        """10. Malformed target version handled gracefully with clear notice."""
        g = migration_guidance.get_migration_guidance("app.before_first_request", target_version="not-a-valid-version")
        self.assertFalse(g.target_version_evaluated)
        self.assertIsNotNone(g.target_version_notice)
        self.assertIn("Invalid version format", g.target_version_notice)

    def test_11_missing_evidence_isolation(self):
        """11. Missing evidence handled gracefully without inventing rationale."""
        # Isolated mock decision with missing rationale quote and missing events
        mock_decisions = [
            {
                "entity": "isolated.symbol",
                "aliases": [],
                "status": "removed",
                "events": [],
                "rationale": None,
            }
        ]
        g = migration_guidance.get_migration_guidance("isolated.symbol", decisions=mock_decisions)
        self.assertIsNotNone(g)
        self.assertIsNone(g.source_quote)
        self.assertIsNone(g.dep_version)
        self.assertIsNone(g.rem_version)
        self.assertEqual(g.evidence_completeness, "unavailable")

    def test_12_scanner_integration(self):
        """12. Scanner findings seamlessly link to verified migration guidance."""
        source = """
@app.before_first_request
def setup():
    pass

if not app.got_first_request:
    pass
"""
        scan_res = scan_code(source, file_name="sample.py", target_version="2.3.0")
        self.assertTrue(scan_res.success)
        self.assertEqual(scan_res.total_findings, 2)

        for finding in scan_res.findings:
            guidance = migration_guidance.get_migration_guidance(
                finding.symbol, target_version=scan_res.target_version
            )
            self.assertIsNotNone(guidance)
            self.assertEqual(guidance.symbol, finding.symbol)
            self.assertTrue(guidance.target_version_evaluated)
            # Ensure serialization functions properly
            d = guidance.to_dict()
            self.assertEqual(d["symbol"], finding.symbol)
            self.assertIn("display_replacement", d)


if __name__ == "__main__":
    unittest.main()
