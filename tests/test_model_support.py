"""Model-catalog checks use fixtures only; no Azure credentials are needed."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check-model-support.py"
SPEC = importlib.util.spec_from_file_location("model_support", SCRIPT)
support = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(support)


class ModelSupportTests(unittest.TestCase):
    def test_nested_catalog_reports_versions_and_skus(self) -> None:
        catalog = [{
            "model": {"name": "gpt-6-luna", "version": "2026-09-22"},
            "skus": [{"name": "GlobalStandard"}],
        }]
        row = support.catalog_rows("swedencentral", catalog, ["gpt-6-luna"], "GlobalStandard")[0]
        self.assertEqual(row["catalog"], "listed")
        self.assertEqual(row["versions"][0]["version"], "2026-09-22")
        self.assertTrue(row["versions"][0]["requested_sku_listed"])
        self.assertEqual(row["decisions_rollout"], "verify_service_support")

    def test_flat_catalog_and_missing_skus_are_explicitly_unknown(self) -> None:
        catalog = {"value": [{"name": "gpt-6.1-sol", "version": "2026-09-29"}]}
        row = support.catalog_rows("eastus", catalog, ["gpt-6.1-sol"], "GlobalStandard")[0]
        self.assertIsNone(row["versions"][0]["requested_sku_listed"])
        self.assertEqual(row["decisions_rollout"], "not_applicable")

    def test_rollout_exclusion_is_independent_of_model_catalog(self) -> None:
        catalog = [{"name": "gpt-6-luna", "version": "2026-09-22"}]
        row = support.catalog_rows("eastus2", catalog, ["gpt-6-luna"], "GlobalStandard")[0]
        self.assertEqual(row["catalog"], "listed")
        self.assertEqual(row["decisions_rollout"], "excluded_in_public_docs")

    def test_missing_model_and_missing_requested_sku(self) -> None:
        rows = support.catalog_rows("eastus", [
            {"model": {"name": "gpt-6-luna", "version": "2026-09-22"}, "skus": [{"name": "Standard"}]}
        ], ["gpt-6.1-sol", "gpt-6-luna"], "GlobalStandard")
        self.assertEqual(rows[0]["catalog"], "not_listed")
        self.assertFalse(rows[1]["versions"][0]["requested_sku_listed"])

    def test_invalid_catalogs_fail_instead_of_reporting_availability(self) -> None:
        for catalog in (None, {}, {"value": {}}, [1], [{}], [{"name": "gpt-6-luna", "skus": "invalid"}]):
            with self.subTest(catalog=catalog), self.assertRaises(ValueError):
                support.catalog_rows("eastus", catalog, ["gpt-6-luna"], "GlobalStandard")

    def test_cli_error_and_invalid_json_propagate(self) -> None:
        with patch.object(support.shutil, "which", return_value="az"):
            with patch.object(support.subprocess, "run", return_value=subprocess.CompletedProcess(
                [], 9, stdout="", stderr="Permission denied"
            )):
                with self.assertRaisesRegex(RuntimeError, "Permission denied"):
                    support.azure_json(["cognitiveservices", "model", "list"], None)
            with patch.object(support.subprocess, "run", return_value=subprocess.CompletedProcess(
                [], 0, stdout="not json", stderr=""
            )):
                with self.assertRaisesRegex(RuntimeError, "valid JSON"):
                    support.azure_json(["account", "list-locations"], None)

    def test_saved_catalog_json_output_does_not_require_azure_cli(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "catalog.json"
            fixture.write_text(json.dumps([{"name": "gpt-6-luna", "version": "2026-09-22"}]))
            result = subprocess.run([
                sys.executable, str(SCRIPT), "--region", "eastus2",
                "--catalog-file", str(fixture), "--format", "json",
            ], text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["source"], "saved_catalog")
        self.assertEqual(report["models"][1]["decisions_rollout"], "excluded_in_public_docs")
        self.assertIn("quota", report["limitations"][0])

    def test_ambiguous_or_invalid_input_is_rejected(self) -> None:
        for arguments in (
            ["--region", "East US 2"],
            ["--all-regions", "--catalog-file", "catalog.json"],
            ["--region", "eastus", "--region", "eastus2", "--catalog-file", "catalog.json"],
            ["--region", "eastus", "--model", ""],
        ):
            with self.subTest(arguments=arguments), self.assertRaises(SystemExit) as error:
                support.parse_arguments(arguments)
            self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
