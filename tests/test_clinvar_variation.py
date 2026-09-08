"""Offline route controls for NCBI RefSNP's retired beta endpoint."""

import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import requests


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "life-science-research/sources/clinvar-variation-skill/scripts/clinvar_variation.py"
)
spec = importlib.util.spec_from_file_location("clinvar_variation", SCRIPT)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def response(url, status, data):
    result = requests.Response()
    result.status_code = status
    result.url = url
    result._content = json.dumps(data).encode()
    return result


class ClinVarVariationRouteTests(unittest.TestCase):
    def test_refsnp_uses_current_route_and_preserves_record(self):
        # NCBI documents rs328 as its public API example. The obsolete route
        # returned 404 for this control during the 2026-09-08 investigation.
        url = "https://api.ncbi.nlm.nih.gov/variation/v0/refsnp/328"
        record = {"refsnp_id": "328", "primary_snapshot_data": {"variant_type": "snv"}}

        def serve(request_url, **kwargs):
            return response(request_url, 200 if request_url == url else 404, record)

        for identifier in (328, "328", "rs328", "RS328"):
            with (
                self.subTest(identifier=identifier),
                tempfile.TemporaryDirectory() as tmp,
            ):
                output_path = Path(tmp) / "record.json"
                with patch.object(helper.requests, "get", side_effect=serve) as get:
                    result = helper.execute(
                        {
                            "action": "refsnp",
                            "refsnp": identifier,
                            "timeout_sec": 7,
                            "save_raw": True,
                            "raw_output_path": str(output_path),
                        }
                    )
                self.assertTrue(result["ok"])
                self.assertEqual(result["summary"]["refsnp_id"], "328")
                self.assertEqual(json.loads(output_path.read_text()), record)
                get.assert_called_once_with(url, timeout=7)

    def test_clinvar_accessions_keep_existing_beta_routes(self):
        base = "https://api.ncbi.nlm.nih.gov/variation/v0/beta/clinvar"
        cases = (
            ("vcv", "VCV000013080", f"{base}/variation/000013080"),
            ("rcv", "RCV000000001", f"{base}/rcv/RCV000000001"),
            ("scv", "SCV000000001", f"{base}/scv/SCV000000001"),
        )
        for action, identifier, url in cases:
            with self.subTest(action=action):
                with patch.object(
                    helper.requests, "get", return_value=response(url, 200, {})
                ) as get:
                    result = helper.execute({"action": action, action: identifier})
                self.assertTrue(result["ok"])
                get.assert_called_once_with(url, timeout=30)

    def test_http_failures_remain_errors_and_cli_exits_nonzero(self):
        url = "https://api.ncbi.nlm.nih.gov/variation/v0/refsnp/328"
        for status in (404, 429, 500):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as tmp:
                output_path = Path(tmp) / "must-not-exist.json"
                payload = {
                    "action": "refsnp",
                    "refsnp": "rs328",
                    "save_raw": True,
                    "raw_output_path": str(output_path),
                }
                failed_response = response(url, status, {"refsnp_id": "328"})
                failed_response.json = Mock(
                    side_effect=AssertionError("must reject status first")
                )
                stdout = io.StringIO()
                with (
                    patch.object(helper.requests, "get", return_value=failed_response),
                    patch.object(helper.sys, "stdin", io.StringIO(json.dumps(payload))),
                    patch.object(helper.sys, "stdout", stdout),
                ):
                    exit_code = helper.main()
                result = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 1)
                self.assertFalse(result["ok"])
                self.assertEqual(result["error"]["code"], "network_error")
                self.assertIn(str(status), result["error"]["message"])
                self.assertNotIn("summary", result)
                self.assertFalse(output_path.exists())
                failed_response.json.assert_not_called()


if __name__ == "__main__":
    unittest.main()
