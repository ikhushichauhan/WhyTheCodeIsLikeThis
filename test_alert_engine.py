"""
Tests for Step 6 — Actionable Findings and Alert System (alert_engine.py).

Verifies:
  1. Severity assignment rules (Critical, High, Medium, Informational).
  2. Deprecated versus removed status distinction.
  3. Missing target version handling (defaults to High if removal known).
  4. Missing evidence handling (no crash, explicit None/missing marker).
  5. Missing line number handling.
  6. Deduplication for same API, file, line, source.
  7. Multiple findings in one file preserved as distinct alerts.
  8. Alert grouping by severity.
  9. Filtering by severity, detection source, and API symbol.
  10. Session status behavior (New -> Needs Review -> Resolved).
  11. Integration with code_scanner.ScanFinding and pr_analyzer.PRFinding.
  12. Merging reports from multiple sources.
"""

import unittest
from typing import List

import alert_engine
from code_scanner import ScanFinding, scan_code
from pr_analyzer import PRFinding, analyze_python_patch


class TestAlertEngine(unittest.TestCase):

    def test_01_severity_critical_when_target_at_or_above_removal(self):
        """1. Confirmed removed in target Flask version assigns Critical severity."""
        # app.before_first_request was removed in Flask 2.3.0
        finding = ScanFinding(
            symbol="app.before_first_request",
            file_name="app.py",
            line=15,
            col=0,
            detection_type="decorator",
            dep_version="2.2.0",
            rem_version="2.3.0",
            explanation="Configuration should be done before running...",
            evidence_url="https://github.com/pallets/flask/issues/4605",
            status="Removed in Flask 2.3.0",
            confidence="high",
        )
        report = alert_engine.alerts_from_scan_findings([finding], target_version="2.3.0")
        self.assertEqual(report.total, 1)
        alert = report.alerts[0]
        self.assertEqual(alert.severity, alert_engine.SEVERITY_CRITICAL)
        self.assertIn("removed in Flask 2.3.0", alert.description)
        self.assertIsNotNone(alert.recommended_action)

        # target_version higher than removal (Flask 3.0.0 >= 2.3.0) -> Critical
        report_higher = alert_engine.alerts_from_scan_findings([finding], target_version="3.0.0")
        self.assertEqual(report_higher.alerts[0].severity, alert_engine.SEVERITY_CRITICAL)

    def test_02_severity_high_when_removal_known_but_target_missing(self):
        """2. Removal version is known, but target version is not supplied -> High."""
        finding = ScanFinding(
            symbol="test_client.as_tuple",
            file_name="tests/test_api.py",
            line=30,
            col=4,
            detection_type="attribute_access",
            dep_version="2.0.3",
            rem_version="2.1.0",
            explanation="Deprecated in Werkzeug 2.0...",
            evidence_url="https://github.com/pallets/flask/pull/4417",
            status="Removed in Flask 2.1.0 (Deprecated in 2.0.3)",
            confidence="high",
        )
        # No target version supplied
        report = alert_engine.alerts_from_scan_findings([finding], target_version=None)
        self.assertEqual(report.total, 1)
        alert = report.alerts[0]
        self.assertEqual(alert.severity, alert_engine.SEVERITY_HIGH)
        self.assertIn("No target version was provided", alert.description)

    def test_03_severity_medium_when_deprecated_not_removed_for_target(self):
        """3. API is deprecated in target version, but not confirmed removed -> Medium."""
        # got_first_request: deprecated in 2.3.0, removed in 3.0.0. Target: 2.3.0
        finding = ScanFinding(
            symbol="got_first_request",
            file_name="server.py",
            line=42,
            col=8,
            detection_type="attribute_access",
            dep_version="2.3.0",
            rem_version="3.0.0",
            explanation="Property was missed when deprecating before_first_request",
            evidence_url="https://github.com/pallets/flask/pull/4997",
            status="Deprecated in Flask 2.3.0",
            confidence="high",
        )
        report = alert_engine.alerts_from_scan_findings([finding], target_version="2.3.0")
        self.assertEqual(report.total, 1)
        alert = report.alerts[0]
        self.assertEqual(alert.severity, alert_engine.SEVERITY_MEDIUM)
        self.assertIn("deprecated", alert.description.lower())
        self.assertIn("not confirmed removed", alert.description.lower())

    def test_04_severity_informational_when_below_deprecation_or_unknown(self):
        """4. Target version is earlier than deprecation milestone -> Informational."""
        # got_first_request deprecated in 2.3.0, target is 2.1.0
        finding = ScanFinding(
            symbol="got_first_request",
            file_name="server.py",
            line=10,
            col=0,
            detection_type="attribute_access",
            dep_version="2.3.0",
            rem_version="3.0.0",
            explanation="Property was missed",
            evidence_url="https://github.com/pallets/flask/pull/4997",
            status="Not yet deprecated in Flask 2.1.0",
            confidence="high",
        )
        report = alert_engine.alerts_from_scan_findings([finding], target_version="2.1.0")
        self.assertEqual(report.total, 1)
        alert = report.alerts[0]
        self.assertEqual(alert.severity, alert_engine.SEVERITY_INFO)

    def test_05_missing_evidence_reference_handled(self):
        """5. Finding without verified evidence link does not fail and is marked."""
        finding = ScanFinding(
            symbol="custom.unknown_api",
            file_name="custom.py",
            line=5,
            col=0,
            detection_type="call_argument",
            dep_version=None,
            rem_version=None,
            explanation="",
            evidence_url=None,
            status="Unknown",
            confidence="low",
        )
        report = alert_engine.alerts_from_scan_findings([finding], target_version="2.0.0")
        self.assertEqual(report.total, 1)
        alert = report.alerts[0]
        self.assertIsNone(alert.evidence_url)
        self.assertEqual(alert.severity, alert_engine.SEVERITY_INFO)
        # Recommendation should be None (never invent a fake recommendation)
        self.assertIsNone(alert.recommended_action)

    def test_06_missing_line_number_handled(self):
        """6. Alert correctly handles missing/unreliable line numbers as None."""
        pr_finding = PRFinding(
            symbol="app.before_first_request",
            file_path="factory.py",
            line_number=None,
            change_type="added",
            detection_type="decorator",
            dep_version="2.2.0",
            rem_version="2.3.0",
            status="Removed in Flask 2.3.0",
            explanation="Move to factory",
            evidence_url="https://github.com/pallets/flask/issues/4605",
            snippet="@app.before_first_request",
            confidence="medium (partial hunk context)",
        )
        report = alert_engine.alerts_from_pr_findings([pr_finding], target_version="2.3.0")
        self.assertEqual(report.total, 1)
        alert = report.alerts[0]
        self.assertIsNone(alert.line_number)
        self.assertEqual(alert.source, alert_engine.SOURCE_GITHUB_PR)
        self.assertEqual(alert.change_type, "added")

    def test_07_deduplication_same_api_file_line_source(self):
        """7. Identical findings for same API, file, line, and source are deduplicated."""
        f1 = ScanFinding(
            symbol="got_first_request",
            file_name="app.py",
            line=20,
            col=4,
            detection_type="attribute_access",
            dep_version="2.3.0",
            rem_version="3.0.0",
            explanation="quote",
            evidence_url="https://github.com/pallets/flask/pull/4997",
            status="Deprecated in 2.3.0",
        )
        # Exact duplicate
        f2 = ScanFinding(
            symbol="got_first_request",
            file_name="app.py",
            line=20,
            col=8,
            detection_type="attribute_access",
            dep_version="2.3.0",
            rem_version="3.0.0",
            explanation="quote",
            evidence_url="https://github.com/pallets/flask/pull/4997",
            status="Deprecated in 2.3.0",
        )
        report = alert_engine.alerts_from_scan_findings([f1, f2], target_version="2.3.0")
        # Deduplication should collapse them to 1 alert
        self.assertEqual(report.total, 1)

    def test_08_multiple_distinct_findings_in_one_file_preserved(self):
        """8. Distinct findings in the same file (different lines or APIs) are preserved."""
        f1 = ScanFinding(
            symbol="app.before_first_request",
            file_name="views.py",
            line=10,
            col=0,
            detection_type="decorator",
            dep_version="2.2.0",
            rem_version="2.3.0",
            explanation="setup in factory",
            evidence_url="https://github.com/pallets/flask/issues/4605",
            status="Removed in 2.3.0",
        )
        f2 = ScanFinding(
            symbol="got_first_request",
            file_name="views.py",
            line=45,
            col=4,
            detection_type="attribute_access",
            dep_version="2.3.0",
            rem_version="3.0.0",
            explanation="property missed",
            evidence_url="https://github.com/pallets/flask/pull/4997",
            status="Deprecated in 2.3.0",
        )
        report = alert_engine.alerts_from_scan_findings([f1, f2], target_version="2.3.0")
        self.assertEqual(report.total, 2)
        symbols = [a.symbol for a in report.alerts]
        self.assertIn("app.before_first_request", symbols)
        self.assertIn("got_first_request", symbols)
        # Critical before_first_request (removed in 2.3.0) should sort before Medium got_first_request (removed in 3.0.0)
        self.assertEqual(report.alerts[0].symbol, "app.before_first_request")
        self.assertEqual(report.alerts[0].severity, alert_engine.SEVERITY_CRITICAL)
        self.assertEqual(report.alerts[1].symbol, "got_first_request")
        self.assertEqual(report.alerts[1].severity, alert_engine.SEVERITY_MEDIUM)

    def test_09_alert_grouping_by_severity(self):
        """9. by_severity() groups alerts in priority order."""
        f_crit = ScanFinding(
            symbol="app.before_first_request",
            file_name="a.py",
            line=1,
            col=0,
            detection_type="decorator",
            dep_version="2.2.0",
            rem_version="2.3.0",
            explanation="",
            evidence_url=None,
            status="",
        )
        f_med = ScanFinding(
            symbol="got_first_request",
            file_name="b.py",
            line=1,
            col=0,
            detection_type="attribute_access",
            dep_version="2.3.0",
            rem_version="3.0.0",
            explanation="",
            evidence_url=None,
            status="",
        )
        report = alert_engine.alerts_from_scan_findings([f_crit, f_med], target_version="2.3.0")
        grouped = report.by_severity()
        self.assertIn(alert_engine.SEVERITY_CRITICAL, grouped)
        self.assertIn(alert_engine.SEVERITY_MEDIUM, grouped)
        self.assertEqual(len(grouped[alert_engine.SEVERITY_CRITICAL]), 1)
        self.assertEqual(len(grouped[alert_engine.SEVERITY_MEDIUM]), 1)

    def test_10_filters_by_severity_source_and_symbol(self):
        """10. filter() correctly filters alerts by severity, source, and symbol."""
        f1 = ScanFinding(
            symbol="app.before_first_request",
            file_name="a.py",
            line=1,
            col=0,
            detection_type="decorator",
            dep_version="2.2.0",
            rem_version="2.3.0",
            explanation="",
            evidence_url=None,
            status="",
        )
        pr1 = PRFinding(
            symbol="test_client.as_tuple",
            file_path="tests/b.py",
            line_number=20,
            change_type="added",
            detection_type="call_argument",
            dep_version="2.0.3",
            rem_version="2.1.0",
            status="",
            explanation="",
            evidence_url=None,
            snippet="client.get('/', as_tuple=True)",
        )
        rep1 = alert_engine.alerts_from_scan_findings([f1], target_version="2.3.0")
        rep2 = alert_engine.alerts_from_pr_findings([pr1], target_version="2.3.0")
        merged = alert_engine.merge_reports(rep1, rep2)

        self.assertEqual(merged.total, 2)
        # Filter by severity
        crit_only = merged.filter(severity=alert_engine.SEVERITY_CRITICAL)
        self.assertEqual(len(crit_only), 2)  # Both removed in <= 2.3.0
        # Filter by source
        local_only = merged.filter(source=alert_engine.SOURCE_LOCAL_SCAN)
        self.assertEqual(len(local_only), 1)
        self.assertEqual(local_only[0].symbol, "app.before_first_request")
        pr_only = merged.filter(source=alert_engine.SOURCE_GITHUB_PR)
        self.assertEqual(len(pr_only), 1)
        self.assertEqual(pr_only[0].symbol, "test_client.as_tuple")
        # Filter by symbol
        bfr_only = merged.filter(symbol="app.before_first_request")
        self.assertEqual(len(bfr_only), 1)

    def test_11_session_status_behavior(self):
        """11. Session status transitions: New -> Needs Review -> Resolved."""
        finding = ScanFinding(
            symbol="app.before_first_request",
            file_name="app.py",
            line=10,
            col=0,
            detection_type="decorator",
            dep_version="2.2.0",
            rem_version="2.3.0",
            explanation="",
            evidence_url=None,
            status="",
        )
        report = alert_engine.alerts_from_scan_findings([finding], target_version="2.3.0")
        alert = report.alerts[0]
        # Default status
        self.assertEqual(alert.status, "New")

        # Session overrides
        status_map = {alert.alert_id: "Needs Review"}
        updated_report = alert_engine.apply_status_overrides(report, status_map)
        self.assertEqual(updated_report.alerts[0].status, "Needs Review")

        # Mark as Resolved
        status_map[alert.alert_id] = "Resolved"
        resolved_report = alert_engine.apply_status_overrides(report, status_map)
        self.assertEqual(resolved_report.alerts[0].status, "Resolved")

    def test_12_end_to_end_scanner_and_pr_integration(self):
        """12. Real scan_code and analyze_python_patch results produce valid AlertReports."""
        code = """
@app.before_first_request
def init_db():
    pass

if not app.got_first_request:
    setup()
"""
        scan_res = scan_code(code, file_name="sample.py", target_version="2.3.0")
        self.assertTrue(scan_res.success)
        self.assertEqual(scan_res.total_findings, 2)

        report = alert_engine.alerts_from_scan_findings(scan_res.findings, target_version="2.3.0")
        self.assertEqual(report.total, 2)
        self.assertEqual(report.critical_count, 1)  # before_first_request (removed in 2.3.0)
        self.assertEqual(report.medium_count, 1)    # got_first_request (removed in 3.0.0)

        # Check dictionary serialization
        data = report.to_dict()
        self.assertEqual(data["total"], 2)
        self.assertEqual(data["critical"], 1)
        self.assertEqual(data["medium"], 1)
        self.assertEqual(len(data["alerts"]), 2)

    def test_13_normalize_scan_finding_from_dict_and_object(self):
        """13. normalize_scan_finding correctly handles both dataclasses and dicts."""
        finding_obj = ScanFinding(
            symbol="app.before_first_request",
            file_name="app.py",
            line=10,
            col=0,
            detection_type="decorator",
            dep_version="2.2.0",
            rem_version="2.3.0",
            explanation="Configuration should be done before running...",
            evidence_url="https://github.com/pallets/flask/issues/4605",
            status="Removed in Flask 2.3.0",
            confidence="high",
        )
        norm_obj = alert_engine.normalize_scan_finding(finding_obj)
        self.assertEqual(norm_obj["symbol"], "app.before_first_request")
        self.assertEqual(norm_obj["file_name"], "app.py")
        self.assertEqual(norm_obj["line"], 10)
        self.assertEqual(norm_obj["rem_version"], "2.3.0")

        # Dict representation (e.g. from session state / serialization)
        finding_dict = {
            "symbol": "app.before_first_request",
            "file_name": "app.py",
            "line": 10,
            "dep_version": "2.2.0",
            "rem_version": "2.3.0",
            "status": "Removed in Flask 2.3.0",
            "evidence_url": "https://github.com/pallets/flask/issues/4605",
            "confidence": "high",
            "detection_type": "decorator",
        }
        norm_dict = alert_engine.normalize_scan_finding(finding_dict)
        self.assertEqual(norm_dict["symbol"], "app.before_first_request")
        self.assertEqual(norm_dict["file_name"], "app.py")
        self.assertEqual(norm_dict["line"], 10)
        self.assertEqual(norm_dict["rem_version"], "2.3.0")

    def test_14_alerts_from_scan_findings_with_dicts(self):
        """14. alerts_from_scan_findings safely consumes plain dict finding records."""
        finding_dict = {
            "symbol": "app.before_first_request",
            "file_name": "server.py",
            "line": 12,
            "dep_version": "2.2.0",
            "rem_version": "2.3.0",
            "status": "Removed in Flask 2.3.0",
            "evidence_url": "https://github.com/pallets/flask/issues/4605",
            "confidence": "high",
            "detection_type": "decorator",
        }
        report = alert_engine.alerts_from_scan_findings([finding_dict], target_version="2.3.0")
        self.assertEqual(report.total, 1)
        self.assertEqual(report.alerts[0].symbol, "app.before_first_request")
        self.assertEqual(report.alerts[0].severity, alert_engine.SEVERITY_CRITICAL)
        self.assertEqual(report.alerts[0].file_path, "server.py")
        self.assertEqual(report.alerts[0].line_number, 12)

    def test_15_scanner_to_alerts_integration_flow_before_first_request(self):
        """15. Complete flow: Scan deprecated code -> pass to alert_engine -> verify alert."""
        deprecated_code = """from flask import Flask
app = Flask(__name__)

@app.before_first_request
def setup_app():
    pass
"""
        scan_res = scan_code(deprecated_code, file_name="app.py", target_version="2.3.0")
        self.assertTrue(scan_res.success)
        self.assertEqual(scan_res.total_findings, 1)
        self.assertEqual(scan_res.findings[0].symbol, "app.before_first_request")

        # Simulate storing in session state and retrieving on Alerts page
        session_state_findings = scan_res.findings
        report = alert_engine.alerts_from_scan_findings(session_state_findings, target_version="2.3.0")

        self.assertEqual(report.total, 1)
        alert = report.alerts[0]
        self.assertEqual(alert.symbol, "app.before_first_request")
        self.assertEqual(alert.severity, alert_engine.SEVERITY_CRITICAL)
        self.assertEqual(alert.file_path, "app.py")
        self.assertEqual(alert.line_number, 4)
        self.assertIn("application factory", alert.recommended_action)
        self.assertEqual(alert.status, "New")

    def test_16_scanner_to_alerts_integration_flow_no_target_version(self):
        """16. Complete flow without target version defaults to High severity."""
        code = """from flask import Flask
app = Flask(__name__)

@app.before_first_request
def setup():
    pass
"""
        scan_res = scan_code(code, file_name="main.py", target_version=None)
        self.assertTrue(scan_res.success)
        self.assertEqual(scan_res.total_findings, 1)

        report = alert_engine.alerts_from_scan_findings(scan_res.findings, target_version=None)
        self.assertEqual(report.total, 1)
        alert = report.alerts[0]
        self.assertEqual(alert.symbol, "app.before_first_request")
        self.assertEqual(alert.severity, alert_engine.SEVERITY_HIGH)
        self.assertIn("No target version was provided", alert.description)


if __name__ == "__main__":
    unittest.main()
