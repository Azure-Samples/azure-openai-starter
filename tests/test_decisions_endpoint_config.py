"""Validate endpoint configuration before constructing clients or credentials."""

import os
from pathlib import Path
import runpy
import sys
from types import ModuleType
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]


class EndpointConfigurationTests(unittest.TestCase):
    def run_python_sample(self, endpoint: str, api_key: str | None, argv: list[str] | None = None) -> None:
        identity = ModuleType("azure.identity")
        identity.DefaultAzureCredential = Mock(side_effect=AssertionError("credential construction reached"))
        identity.get_bearer_token_provider = Mock(side_effect=AssertionError("token provider reached"))
        dotenv = ModuleType("dotenv")
        dotenv.load_dotenv = Mock()
        openai = ModuleType("openai")
        openai.OpenAI = Mock(side_effect=AssertionError("client construction reached"))
        decision = ModuleType("openai.types.decision")
        decision.Decision = object
        modules = {
            "azure.identity": identity, "dotenv": dotenv,
            "openai": openai, "openai.types.decision": decision,
        }
        environment = {"AZURE_OPENAI_ENDPOINT": endpoint}
        if api_key is not None:
            environment["AZURE_OPENAI_API_KEY"] = api_key
        with patch.dict(sys.modules, modules), patch.dict(os.environ, environment, clear=True):
            sample = runpy.run_path(str(ROOT / "src" / "python" / "decisions_example.py"))
            sample["main"](argv or [])

    def test_remote_http_is_rejected_before_client_or_credentials(self) -> None:
        for api_key in ("local-contract-test-key", None, ""):
            for endpoint in ("http://example.invalid", "http://127.0.0.1.example.invalid"):
                with self.subTest(endpoint=endpoint, api_key=bool(api_key)):
                    with self.assertRaisesRegex(ValueError, "must use HTTPS"):
                        self.run_python_sample(endpoint, api_key)

    def test_loopback_http_requires_an_explicit_key(self) -> None:
        for endpoint in ("http://localhost", "http://127.0.0.1:8080", "http://[::1]:8080"):
            for api_key in (None, ""):
                with self.subTest(endpoint=endpoint, api_key=api_key):
                    with self.assertRaisesRegex(ValueError, "must use HTTPS"):
                        self.run_python_sample(endpoint, api_key)

    def test_invalid_resource_roots_fail_before_authentication(self) -> None:
        for endpoint in (
            "example.invalid", "https://", "https://user:password@example.invalid",
            "https://@example.invalid", "https://example.invalid?", "https://example.invalid#",
            "https://example.invalid/openai/v1/", "https://example.invalid/?query=1",
            "https://example.invalid/#fragment", "https://example.invalid:invalid",
            "https://example.invalid:99999",
        ):
            for api_key in ("local-contract-test-key", None):
                with self.subTest(endpoint=endpoint, api_key=bool(api_key)):
                    with self.assertRaisesRegex(ValueError, "resource root URL"):
                        self.run_python_sample(endpoint, api_key)

    def test_https_and_explicit_key_loopback_reach_client_construction(self) -> None:
        for endpoint in (
            "https://example.invalid", "https://example.invalid///",
            "http://localhost:8080", "http://127.0.0.1:8080/",
            "http://127.1.2.3:8080", "http://[::1]:8080/",
        ):
            with self.subTest(endpoint=endpoint):
                with self.assertRaisesRegex(AssertionError, "client construction reached"):
                    self.run_python_sample(endpoint, "local-contract-test-key")

    def test_https_still_supports_passwordless_authentication(self) -> None:
        with self.assertRaisesRegex(AssertionError, "credential construction reached"):
            self.run_python_sample("https://example.invalid/", None)

    def test_image_inputs_are_checked_before_authentication(self) -> None:
        for source, message in (
            ("http://example.invalid/photo.png", "HTTPS"),
            ("https://user@example.invalid/photo.png", "HTTPS"),
            ("photo.svg", "PNG, JPEG, WebP, or GIF"),
        ):
            with self.subTest(source=source), self.assertRaisesRegex(ValueError, message):
                self.run_python_sample("https://example.invalid", None, ["--image", source])


if __name__ == "__main__":
    unittest.main()
