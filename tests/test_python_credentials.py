"""Check which Azure Identity credential the Python Entra samples create."""

import os
from pathlib import Path
import runpy
import sys
from types import ModuleType
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
TENANT = "00000000-0000-0000-0000-000000000000"
SAMPLES = ("decisions_example", "decisions_multimodal_example", "responses_example_entra")


class PythonCredentialTests(unittest.TestCase):
    def run_sample(self, stem: str, environment: dict[str, str]) -> Mock:
        """Run a sample up to its token provider and return the Azure Developer CLI credential factory."""
        identity = ModuleType("azure.identity")
        identity.AzureDeveloperCliCredential = Mock()
        identity.get_bearer_token_provider = Mock(side_effect=RuntimeError("stop before token acquisition"))
        dotenv = ModuleType("dotenv")
        dotenv.load_dotenv = Mock()
        openai = ModuleType("openai")
        openai.OpenAI = Mock(side_effect=AssertionError("unexpected client"))
        response = ModuleType("openai.types.responses")
        response.Response = object
        decision = ModuleType("openai.types.decision")
        decision.Decision = object
        modules = {
            "azure.identity": identity, "dotenv": dotenv, "openai": openai,
            "openai.types.responses": response, "openai.types.decision": decision,
        }
        environment = {"AZURE_OPENAI_ENDPOINT": "https://example.invalid/", **environment}
        with (patch.dict(sys.modules, modules), patch.dict(os.environ, environment, clear=True),
              patch.object(sys, "argv", [f"{stem}.py"])):
            sample = runpy.run_path(str(ROOT / "src" / "python" / f"{stem}.py"))
            with self.assertRaisesRegex(RuntimeError, "stop before token acquisition"):
                sample["main"]()
        openai.OpenAI.assert_not_called()
        return identity.AzureDeveloperCliCredential

    def test_tenant_is_passed_to_the_azd_credential(self) -> None:
        for stem in SAMPLES:
            with self.subTest(sample=stem):
                self.run_sample(stem, {"AZURE_TENANT_ID": TENANT}).assert_called_once_with(tenant_id=TENANT)

    def test_azd_credential_is_used_without_a_tenant(self) -> None:
        for stem in SAMPLES:
            for environment in ({}, {"AZURE_TENANT_ID": ""}):
                with self.subTest(sample=stem, environment=environment):
                    self.run_sample(stem, environment).assert_called_once_with()

    def test_azure_token_credentials_does_not_change_the_credential(self) -> None:
        for stem in SAMPLES:
            with self.subTest(sample=stem):
                credential = self.run_sample(stem, {
                    "AZURE_TENANT_ID": TENANT, "AZURE_TOKEN_CREDENTIALS": "AzureCliCredential",
                })
                credential.assert_called_once_with(tenant_id=TENANT)


if __name__ == "__main__":
    unittest.main()
