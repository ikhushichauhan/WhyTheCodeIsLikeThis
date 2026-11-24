"""
Comprehensive test suite for Step 3 — Evidence-Based Refusal Mechanism in Rationale.
Tests all required cases without modifying production curated records.
"""

import sys
import unittest
import subprocess
from packaging.version import Version, InvalidVersion

import app
import version_checker


class TestEvidenceBasedRefusal(unittest.TestCase):

    def test_01_verified_decision_before_first_request(self):
        """Test before_first_request returns existing verified decision."""
        res = app.find_decision("before_first_request")
        self.assertIsNotNone(res, "before_first_request should match a decision")
        self.assertEqual(res["entity"], "app.before_first_request")
        self.assertTrue(res["has_rationale"])
        self.assertEqual(res["rationale_status"], "verified")
        expected_quote = (
            "Configuration should be done before _running_ the application, "
            "during the actual setup phase. Preferably, it should be done in a factory function."
        )
        self.assertEqual(res["rationale"], expected_quote)
        self.assertEqual(res["status"], "removed")
        self.assertEqual(res["dep_version"], "v2.2.0")
        self.assertEqual(res["rem_version"], "v2.3.0")
        self.assertGreater(len(res["evidence"]), 0)

    def test_02_verified_decision_got_first_request(self):
        """Test got_first_request returns existing verified decision."""
        res = app.find_decision("got_first_request")
        self.assertIsNotNone(res, "got_first_request should match a decision")
        self.assertEqual(res["entity"], "got_first_request")
        self.assertTrue(res["has_rationale"])
        self.assertEqual(res["rationale_status"], "verified")
        expected_quote = "This property was missed when deprecating `before_first_request`."
        self.assertEqual(res["rationale"], expected_quote)
        self.assertEqual(res["status"], "removed")
        self.assertEqual(res["dep_version"], "v2.3.0")
        self.assertEqual(res["rem_version"], "v3.0.0")

    def test_03_verified_decision_as_tuple(self):
        """Test as_tuple alias returns test_client.as_tuple verified decision."""
        res = app.find_decision("as_tuple")
        self.assertIsNotNone(res, "as_tuple should match a decision")
        self.assertEqual(res["entity"], "test_client.as_tuple")
        self.assertTrue(res["has_rationale"])
        self.assertEqual(res["rationale_status"], "verified")
        expected_quote = (
            "This was deprecated in Werkzeug 2.0, and is no longer supported "
            "in Werkzeug 2.1 or Flask 2.1."
        )
        self.assertEqual(res["rationale"], expected_quote)
        self.assertEqual(res["dep_version"], "v2.0.3")
        self.assertEqual(res["rem_version"], "v2.1.0")

    def test_04_unknown_entity_refusal(self):
        """Test unknown entity like jsonify is refused and returns None."""
        self.assertFalse(app.is_generic_query("jsonify"))
        res = app.find_decision("jsonify")
        self.assertIsNone(res, "Unknown entity must return None")

        # Also verify another unknown function
        res_unknown = app.find_decision("make_response")
        self.assertIsNone(res_unknown, "Unknown entity make_response must return None")

    def test_05_generic_and_short_query_safely_rejected(self):
        """Test generic and short queries like 'app' are safely rejected."""
        self.assertTrue(app.is_generic_query("app"))
        self.assertTrue(app.is_generic_query("flask"))
        self.assertTrue(app.is_generic_query("a"))
        self.assertTrue(app.is_generic_query("   "))
        self.assertTrue(app.is_generic_query("client"))

        # find_decision safely returns None
        self.assertIsNone(app.find_decision("app"))
        self.assertIsNone(app.find_decision("flask"))
        self.assertIsNone(app.find_decision("x"))

    def test_06_missing_rationale_isolated_test_fixture(self):
        """Test isolated decision with missing rationale returns explicit missing-evidence state."""
        fixture_key = "test_fixture_entity_without_rationale"
        fixture_record = {
            "entity": fixture_key,
            "category": "Flask — Testing Fixture",
            "status": "removed",
            "dep_version": "v2.0.0",
            "rem_version": "v2.1.0",
            "subtitle": "Deprecated in Flask 2.0.0",
            "aliases": ["test_fixture_entity_without_rationale", "fixture_alias"],
            "rationale": None,  # Explicitly missing
            "evidence": [
                {"label": "Pull Request #9999", "url": "https://github.com/pallets/flask/pull/9999", "type": "pr"}
            ],
            "events": [
                {"type": "deprecated", "version": "2.0.0", "ref": 9999, "merged_at": None}
            ]
        }

        # Temporarily register fixture in CURATED_DATA without touching production records
        try:
            app.CURATED_DATA[fixture_key] = fixture_record

            res = app.find_decision("fixture_alias")
            self.assertIsNotNone(res, "Fixture decision should be retrieved")
            self.assertEqual(res["entity"], fixture_key)
            self.assertFalse(res["has_rationale"], "has_rationale must be False when rationale is missing")
            self.assertIsNone(res["rationale"], "rationale text must be None, not fabricated text")
            self.assertEqual(res["rationale_status"], "missing_evidence")
            # Evidence references should still be preserved
            self.assertEqual(len(res["evidence"]), 1)
            self.assertEqual(res["evidence"][0]["url"], "https://github.com/pallets/flask/pull/9999")
        finally:
            # Clean up fixture
            app.CURATED_DATA.pop(fixture_key, None)

    def test_07_neo4j_fallback_works_when_offline(self):
        """Test that local fallback returns bundled curated data with correct source and quotes."""
        res = app.find_decision("before_first_request")
        self.assertIsNotNone(res)
        self.assertIn(res["source"], ["Neo4j", "Local fallback"])
        self.assertTrue(res["has_rationale"])
        self.assertIn("factory function", res["rationale"])

    def test_08_version_checker_invalid_version_format(self):
        """Test version_checker invalid version format validation."""
        p = subprocess.run(
            [sys.executable, "version_checker.py"],
            input="invalid_version_format\n",
            text=True,
            capture_output=True
        )
        self.assertIn("Invalid version! Example: 2.2.0", p.stdout)
        self.assertEqual(p.returncode, 0)

    def test_09_version_checker_arbitrary_unsupported_version(self):
        """Test version_checker refuses arbitrary unsupported versions with unavailable evidence notice."""
        for arbitrary in ["99.0.0", "1.0.0", "0.5.0", "4.0.0"]:
            p = subprocess.run(
                [sys.executable, "version_checker.py"],
                input=f"{arbitrary}\n",
                text=True,
                capture_output=True
            )
            self.assertIn("Unavailable version evidence", p.stdout, f"Failed for {arbitrary}")
            self.assertNotIn("Status: Removed", p.stdout, f"Should not claim status for unsupported {arbitrary}")

    def test_10_version_checker_supported_version(self):
        """Test version_checker displays verified decision results for valid supported versions."""
        p = subprocess.run(
            [sys.executable, "version_checker.py"],
            input="2.2.0\n",
            text=True,
            capture_output=True
        )
        self.assertIn("Rationale Version Check: Flask 2.2.0", p.stdout)
        self.assertIn("Entity: app.before_first_request", p.stdout)
        self.assertIn("Status: Deprecated", p.stdout)
        self.assertIn("Entity: got_first_request", p.stdout)
        self.assertIn("Status: Not yet deprecated", p.stdout)
        self.assertIn("Entity: test_client.as_tuple", p.stdout)
        self.assertIn("Status: Removed", p.stdout)


if __name__ == "__main__":
    unittest.main()
