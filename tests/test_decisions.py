"""Exercise all six real Decisions clients against a local HTTP contract."""

import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from test_samples import Sample, build, selected_languages, tool

ROOT = Path(__file__).resolve().parents[1]
INPUT = "I was charged twice for order 123. Please refund the duplicate charge."
NAMES = ["refund_requested", "department", "severity"]
PHOTO = ROOT / "images" / "decisions-photo.png"
PHOTO_URL = "https://raw.githubusercontent.com/scikit-image/scikit-image/v0.25.2/skimage/data/astronaut.png"
PHOTO_NAMES = ["visible_damage", "category", "severity"]


class DecisionsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(prefix="openai-decisions-tests-")
        cls.addClassCleanup(cls.temporary.cleanup)
        destination = Path(cls.temporary.name)
        languages = selected_languages(include_ruby=True)
        if not languages:
            raise unittest.SkipTest("No Decisions languages selected")
        cls.samples = []
        if "Python" in languages:
            cls.samples.append(Sample(
                "Python", "key", [sys.executable, str(ROOT / "src" / "python" / "decisions_example.py")],
                ROOT / "src" / "python",
            ))
        typescript = ROOT / "src" / "typescript"
        if "TypeScript" in languages:
            build([tool("npm"), "run", "build"], typescript)
            cls.samples.append(Sample(
                "TypeScript", "key", [tool("node"), str(typescript / "dist" / "decisions_example.js")],
                typescript,
            ))
        go = ROOT / "src" / "go" / "decisions_example"
        executable = destination / ("decisions.exe" if os.name == "nt" else "decisions")
        if "Go" in languages:
            build([tool("go"), "build", "-o", str(executable), "."], go)
            cls.samples.append(Sample("Go", "key", [str(executable)], go))
        java = ROOT / "src" / "java"
        classpath_file = destination / "classpath.txt"
        if "Java" in languages:
            build([tool("mvn"), "--batch-mode", "compile", "dependency:build-classpath",
                   f"-Dmdep.outputFile={classpath_file}"], java)
            classpath = str(java / "target" / "classes") + os.pathsep + classpath_file.read_text().strip()
            cls.samples.append(Sample(
                "Java", "key", [tool("java"), "-cp", classpath,
                               "com.azure.openai.starter.DecisionsExample"], java,
            ))
        dotnet = ROOT / "src" / "dotnet"
        output = destination / "dotnet"
        if ".NET" in languages:
            build([tool("dotnet"), "build", "decisions_example.cs", "--nologo",
                   "--output", str(output)], dotnet)
            cls.samples.append(Sample(
                ".NET REST", "key", [tool("dotnet"), str(output / "decisions_example.dll")], dotnet,
            ))
        ruby = ROOT / "src" / "ruby"
        if "Ruby" in languages:
            build([tool("bundle"), "check"], ruby)
            cls.samples.append(Sample(
                "Ruby", "key", [tool("bundle"), "exec", "ruby", "decisions_example.rb"], ruby,
            ))
        cls.requests = []
        cls.scenario = "completed"

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: object) -> None:
                pass

            def do_POST(self) -> None:
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                cls.requests.append({
                    "path": self.path, "body": body,
                    "authorization": self.headers.get("Authorization"),
                    "api-key": self.headers.get("api-key"),
                    "content-encoding": self.headers.get("Content-Encoding"),
                })
                names = [question["name"] for question in body["questions"]]
                choices = body["questions"][1]["choices"]
                answers = [
                    {"type": "predicate", "name": names[0], "probability": 0.95},
                    {"type": "choice", "name": names[1], "choice": choices[0]["value"], "confidence": 0.9,
                     "probabilities": [{"value": choice["value"], "probability": probability}
                                       for choice, probability in zip(choices, (0.9, 0.05, 0.05))]},
                    {"type": "score", "name": names[2], "score": 1.1, "confidence": 0.55,
                     "probabilities": [{"label": "Low", "value": 0, "probability": 0.1},
                                       {"label": "Medium", "value": 1, "probability": 0.7},
                                       {"label": "High", "value": 2, "probability": 0.2}]},
                ]
                if cls.scenario == "refusal":
                    answers = [{"type": "refusal", "name": name} for name in names]
                elif cls.scenario == "empty":
                    answers = []
                elif cls.scenario == "unknown":
                    answers[0]["type"] = "unexpected"
                response = {
                    "model": body["model"],
                    "answers": answers,
                    "usage": {
                        "input_tokens": 42,
                        "input_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0},
                        "output_tokens": 0,
                        "output_tokens_details": {"reasoning_tokens": 0},
                        "total_tokens": 42,
                    },
                }
                if cls.scenario == "missing_usage":
                    response["usage"] = None
                code = 200
                if self.path != "/openai/v1/decisions":
                    code = 404
                    response = {"error": {"message": "Unexpected request path", "type": "invalid_request_error"}}
                elif cls.scenario == "http_error":
                    code = 400
                    response = {"error": {"message": "Contract test rejection", "type": "invalid_request_error"}}
                elif cls.scenario == "deployment_not_found":
                    code = 404
                    response = {"error": {"code": "DeploymentNotFound",
                                          "message": "The specified deployment does not exist."}}
                payload = json.dumps(response).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.addClassCleanup(cls.server.server_close)
        cls.addClassCleanup(cls.thread.join)
        cls.addClassCleanup(cls.server.shutdown)
        cls.endpoint = f"http://127.0.0.1:{cls.server.server_port}"

    def setUp(self) -> None:
        type(self).scenario = "completed"
        self.requests.clear()

    def run_sample(self, sample: Sample, settings: dict[str, str | None] | None = None,
                   *, arguments: list[str] | None = None, live: bool = False) -> subprocess.CompletedProcess:
        environment = os.environ.copy()
        for name in list(environment):
            if name.startswith("OPENAI_") or (not live and name.startswith(("AZURE_OPENAI_", "Clients__"))):
                environment.pop(name)
        environment.update({
            "PYTHON_DOTENV_DISABLED": "1",
            "DOTENV_CONFIG_PATH": os.devnull,
            "PYTHONIOENCODING": "utf-8",
        })
        if live:
            environment.pop("AZURE_OPENAI_API_KEY", None)
        else:
            environment.update({
                "AZURE_OPENAI_ENDPOINT": self.endpoint,
                "AZURE_OPENAI_API_KEY": "local-contract-test-key",
            })
        for name, value in (settings or {}).items():
            if value is None:
                environment.pop(name, None)
            else:
                environment[name] = value
        result = subprocess.run([*sample.command, *(arguments or [])], cwd=sample.directory, env=environment,
                                capture_output=True, text=True, encoding="utf-8",
                                errors="replace", timeout=240 if sample.language == "Ruby" else 180 if live else 60)
        result.stdout += result.stderr
        result.stdout = result.stdout.replace("local-contract-test-key", "[redacted]")
        return result

    def assert_request(self, deployment: str = "gpt-6-luna") -> None:
        self.assertEqual(len(self.requests), 1)
        request = self.requests[0]
        self.assertEqual(request["path"], "/openai/v1/decisions")
        self.assertTrue(request["authorization"] == "Bearer local-contract-test-key"
                        or request["api-key"] == "local-contract-test-key")
        self.assertIsNone(request["content-encoding"])
        body = request["body"]
        self.assertEqual(body["model"], deployment)
        self.assertEqual(body["input"], INPUT)
        self.assertEqual([item["name"] for item in body["questions"]], NAMES)
        self.assertEqual([item["type"] for item in body["questions"]], ["predicate", "choice", "score"])
        self.assertEqual(body["questions"][1]["choices"][0]["value"], "billing")
        self.assertEqual([item["label"] for item in body["questions"][2]["levels"]], ["Low", "Medium", "High"])
        for field in ("reasoning", "temperature", "max_output_tokens", "stream"):
            self.assertNotIn(field, body)

    def test_defaults_endpoint_normalization_and_deployment_override(self) -> None:
        for sample in self.samples:
            for ending, deployment in (("", "gpt-6-luna"), ("/", "custom-luna"), ("///", "custom-luna")):
                with self.subTest(language=sample.language, endpoint_suffix=ending):
                    self.requests.clear()
                    settings = {"AZURE_OPENAI_ENDPOINT": self.endpoint + ending}
                    if deployment != "gpt-6-luna":
                        settings["AZURE_OPENAI_DEPLOYMENT"] = deployment
                    result = self.run_sample(sample, settings)
                    self.assertEqual(result.returncode, 0, result.stdout)
                    for name in NAMES:
                        self.assertIn(name, result.stdout)
                    for kind in ("predicate", "choice", "score"):
                        self.assertIn(kind, result.stdout.lower())
                    self.assertIn("probabilities=", result.stdout)
                    self.assertIn("Usage:", result.stdout)
                    for field in ("input_tokens", "output_tokens", "total_tokens", "cached_tokens", "cache_write_tokens"):
                        self.assertIn(field, result.stdout)
                    for option in ("billing", "technical", "other", "Low", "Medium", "High"):
                        self.assertIn(option, result.stdout)
                    self.assert_request(deployment)

    def test_refusals_are_handled_explicitly(self) -> None:
        type(self).scenario = "refusal"
        for sample in self.samples:
            with self.subTest(language=sample.language):
                self.requests.clear()
                result = self.run_sample(sample)
                self.assertEqual(result.returncode, 0, result.stdout)
                self.assertIn("refus", result.stdout.lower())
                self.assert_request()

    def test_http_and_malformed_responses_fail(self) -> None:
        for sample in self.samples:
            for scenario in ("http_error", "deployment_not_found", "empty", "missing_usage", "unknown"):
                with self.subTest(language=sample.language, scenario=scenario):
                    type(self).scenario = scenario
                    self.requests.clear()
                    result = self.run_sample(sample)
                    self.assertNotEqual(result.returncode, 0, result.stdout)
                    self.assertEqual(len(self.requests), 1)
                    self.assertIsNone(self.requests[0]["content-encoding"])
                    if scenario == "http_error":
                        self.assertIn("Contract test rejection", result.stdout)
                    elif scenario == "deployment_not_found":
                        self.assertIn("The specified deployment does not exist.", result.stdout)

    def test_missing_endpoint_fails_before_request(self) -> None:
        for sample in self.samples:
            with self.subTest(language=sample.language):
                result = self.run_sample(sample, {"AZURE_OPENAI_ENDPOINT": None})
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn("AZURE_OPENAI_ENDPOINT", result.stdout)
                self.assertEqual(self.requests, [])

    def test_explicit_empty_deployment_fails_before_request(self) -> None:
        for sample in self.samples:
            for value in ("", " "):
                with self.subTest(language=sample.language, deployment=value):
                    self.requests.clear()
                    result = self.run_sample(sample, {"AZURE_OPENAI_DEPLOYMENT": value})
                    self.assertNotEqual(result.returncode, 0, result.stdout)
                    self.assertIn("AZURE_OPENAI_DEPLOYMENT", result.stdout)
                    self.assertEqual(self.requests, [])

    def test_dotnet_rest_client_is_configured_through_dependency_injection(self) -> None:
        for sample in self.samples:
            if sample.language != ".NET REST":
                continue
            with self.subTest(language=sample.language):
                self.requests.clear()
                result = self.run_sample(sample, {
                    "AZURE_OPENAI_ENDPOINT": None,
                    "AZURE_OPENAI_API_KEY": None,
                    "AZURE_OPENAI_DEPLOYMENT": "ignored-legacy-deployment",
                    "Clients__Decisions__Options__Endpoint": self.endpoint + "/openai/v1/",
                    "Clients__Decisions__Options__NetworkTimeout": "00:00:10",
                    "Clients__Decisions__Credential__CredentialSource": "ApiKeyCredential",
                    "Clients__Decisions__Credential__Key": "local-contract-test-key",
                    "Clients__Decisions__Model": "configured-luna",
                })
                self.assertEqual(result.returncode, 0, result.stdout)
                self.assert_request("configured-luna")
                self.assertIn("Usage:", result.stdout)

    def test_python_and_typescript_reject_unsafe_endpoints_before_authentication(self) -> None:
        for sample in self.samples:
            if sample.language not in ("Python", "TypeScript"):
                continue
            for endpoint in ("http://example.invalid", "http://127.0.0.1.example.invalid", self.endpoint):
                for api_key in (None, "", "local-contract-test-key"):
                    if endpoint == self.endpoint and api_key:
                        continue
                    with self.subTest(language=sample.language, endpoint=endpoint, api_key=bool(api_key)):
                        self.requests.clear()
                        result = self.run_sample(sample, {
                            "AZURE_OPENAI_ENDPOINT": endpoint,
                            "AZURE_OPENAI_API_KEY": api_key,
                            "AZURE_TOKEN_CREDENTIALS": "AzureCliCredential",
                        })
                        self.assertNotEqual(result.returncode, 0, result.stdout)
                        self.assertIn("AZURE_OPENAI_ENDPOINT must use HTTPS", result.stdout)
                        self.assertEqual(self.requests, [])

    def test_python_and_typescript_reject_invalid_resource_roots(self) -> None:
        for sample in self.samples:
            if sample.language not in ("Python", "TypeScript"):
                continue
            for endpoint in (
                "example.invalid", "https://", "https://user:password@example.invalid",
                "https://@example.invalid", "https://example.invalid/openai/v1/",
                "https://example.invalid/?query=1", "https://example.invalid/#fragment",
                "https://example.invalid?", "https://example.invalid#",
                "https://example.invalid:invalid", "https://example.invalid:99999",
            ):
                for api_key in (None, "local-contract-test-key"):
                    with self.subTest(language=sample.language, endpoint=endpoint, api_key=bool(api_key)):
                        self.requests.clear()
                        result = self.run_sample(sample, {
                            "AZURE_OPENAI_ENDPOINT": endpoint,
                            "AZURE_OPENAI_API_KEY": api_key,
                            "AZURE_TOKEN_CREDENTIALS": "AzureCliCredential",
                        })
                        self.assertNotEqual(result.returncode, 0, result.stdout)
                        self.assertIn("resource root URL", result.stdout)
                        self.assertEqual(self.requests, [])

    def test_typescript_keyless_examples_forward_the_resource_tenant(self) -> None:
        if not any(sample.language == "TypeScript" for sample in self.samples):
            self.skipTest("TypeScript was not selected")
        script = r"""
const Module = require("node:module");
const originalLoad = Module._load;
const tenant = "00000000-0000-0000-0000-000000000000";
process.env.AZURE_OPENAI_ENDPOINT = "https://example.invalid/";
process.env.AZURE_TENANT_ID = tenant;
delete process.env.AZURE_OPENAI_API_KEY;
delete process.env.AZURE_OPENAI_DEPLOYMENT;
delete process.env.AZURE_OPENAI_REASONING_EFFORT;
delete process.env.AZURE_OPENAI_MAX_OUTPUT_TOKENS;
Module._load = function (name, ...args) {
    if (name === "@azure/identity") return {
        DefaultAzureCredential: class {
            constructor(options) {
                if (options?.tenantId !== tenant) throw new Error("resource tenant was not forwarded");
                throw new Error("resource tenant forwarded before token request");
            }
        },
        getBearerTokenProvider() { throw new Error("unexpected token request"); }
    };
    return originalLoad.call(this, name, ...args);
};
require(process.argv[1]);
"""
        for stem in ("decisions_example", "responses_example_entra"):
            with self.subTest(sample=stem):
                self.requests.clear()
                result = subprocess.run(
                    [tool("node"), "-e", script, str(ROOT / "src" / "typescript" / "dist" / f"{stem}.js")],
                    cwd=ROOT / "src" / "typescript",
                    env={**os.environ, "DOTENV_CONFIG_PATH": os.devnull},
                    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("resource tenant forwarded before token request", result.stdout + result.stderr)
                self.assertEqual(self.requests, [])

    def test_go_and_ruby_developer_clis_receive_the_resource_tenant(self) -> None:
        tenant = "00000000-0000-0000-0000-000000000000"
        for sample in self.samples:
            if sample.language not in ("Go", "Ruby"):
                continue
            credentials = ["AzureDeveloperCliCredential"]
            if sample.language == "Ruby":
                credentials.append("AzureCliCredential")
            for credential in credentials:
                with self.subTest(language=sample.language, credential=credential):
                    with tempfile.TemporaryDirectory(prefix="decisions-cli-test-") as temporary:
                        directory = Path(temporary)
                        recorded = directory / "arguments.txt"
                        for name in ("az", "azd"):
                            script = directory / name
                            script.write_text(
                                '#!/bin/sh\nprintf \'%s\\n\' "$@" > "$STARTER_TEST_CLI_ARGUMENTS"\n'
                                'echo "Synthetic CLI failure" >&2\nexit 2\n', encoding="utf-8",
                            )
                            script.chmod(0o755)
                            (directory / f"{name}.cmd").write_text(
                                '@echo off\necho %* > "%STARTER_TEST_CLI_ARGUMENTS%"\n'
                                'echo Synthetic CLI failure 1>&2\nexit /b 2\n', encoding="utf-8",
                            )
                        self.requests.clear()
                        result = self.run_sample(sample, {
                            "AZURE_OPENAI_ENDPOINT": "https://example.invalid/",
                            "AZURE_OPENAI_API_KEY": None,
                            "AZURE_TOKEN_CREDENTIALS": credential,
                            "AZURE_TENANT_ID": tenant,
                            "PATH": str(directory) + os.pathsep + os.environ.get("PATH", ""),
                            "STARTER_TEST_CLI_ARGUMENTS": str(recorded),
                        })
                        self.assertNotEqual(result.returncode, 0, result.stdout)
                        self.assertTrue(recorded.is_file(), result.stdout)
                        arguments = recorded.read_text(encoding="utf-8")
                        self.assertIn(tenant, arguments)
                        self.assertIn("--tenant-id" if credential == "AzureDeveloperCliCredential"
                                      else "--tenant", arguments)
                        if credential == "AzureDeveloperCliCredential":
                            self.assertIn("--scope", arguments)
                            self.assertIn("https://cognitiveservices.azure.com/.default", arguments)
                        else:
                            self.assertIn("--resource", arguments)
                        self.assertEqual(self.requests, [])

    def test_ruby_developer_cli_rejects_invalid_token_responses(self) -> None:
        sample = next((item for item in self.samples if item.language == "Ruby"), None)
        if sample is None:
            self.skipTest("Ruby was not selected")
        for payload in ("[]", "null", "not-json", "{}"):
            with self.subTest(response=payload), tempfile.TemporaryDirectory(prefix="decisions-cli-json-") as temporary:
                directory = Path(temporary)
                script = directory / "azd"
                script.write_text(f"#!/bin/sh\nprintf '%s\\n' '{payload}'\n", encoding="utf-8")
                script.chmod(0o755)
                (directory / "azd.cmd").write_text(f"@echo off\necho {payload}\nexit /b 0\n", encoding="utf-8")
                self.requests.clear()
                result = self.run_sample(sample, {
                    "AZURE_OPENAI_ENDPOINT": "https://example.invalid/",
                    "AZURE_OPENAI_API_KEY": None,
                    "AZURE_TOKEN_CREDENTIALS": "AzureDeveloperCliCredential",
                    "AZURE_TENANT_ID": "00000000-0000-0000-0000-000000000000",
                    "PATH": str(directory) + os.pathsep + os.environ.get("PATH", ""),
                })
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn("Azure Developer CLI did not return a JSON access token", result.stdout)
                self.assertEqual(self.requests, [])

    def test_real_photo_inputs_inline_and_https(self) -> None:
        photo_bytes = PHOTO.read_bytes()
        self.assertTrue(photo_bytes.startswith(b"\x89PNG\r\n\x1a\n"))
        for sample in self.samples:
            for source in (str(PHOTO), PHOTO_URL):
                with self.subTest(language=sample.language, source="inline" if source == str(PHOTO) else "https"):
                    self.requests.clear()
                    result = self.run_sample(sample, arguments=["--image", source])
                    self.assertEqual(result.returncode, 0, result.stdout)
                    self.assertEqual(len(self.requests), 1)
                    body = self.requests[0]["body"]
                    self.assertEqual(body["model"], "gpt-6-luna")
                    self.assertEqual([question["name"] for question in body["questions"]], PHOTO_NAMES)
                    self.assertEqual(body["questions"][1]["choices"][-1]["value"], "other")
                    content = body["input"][0]["content"]
                    self.assertEqual(body["input"][0]["role"], "user")
                    self.assertEqual(content[0]["type"], "input_text")
                    self.assertEqual(content[1]["type"], "input_image")
                    image = content[1]["image_url"]
                    if source == str(PHOTO):
                        prefix, encoded = image.split(",", 1)
                        self.assertEqual(prefix, "data:image/png;base64")
                        self.assertEqual(base64.b64decode(encoded, validate=True), photo_bytes)
                    else:
                        self.assertEqual(image, PHOTO_URL)
                    for name in PHOTO_NAMES:
                        self.assertIn(name, result.stdout)
                    self.assertIn("probabilities=", result.stdout)
                    self.assertIn("Usage:", result.stdout)

    def test_invalid_image_options_fail_before_request(self) -> None:
        for sample in self.samples:
            for arguments in (["--image"], ["--image", "http://example.invalid/photo.png"],
                              ["--image", str(ROOT / "README.md")]):
                with self.subTest(language=sample.language, arguments=arguments):
                    self.requests.clear()
                    result = self.run_sample(sample, arguments=arguments)
                    self.assertNotEqual(result.returncode, 0, result.stdout)
                    self.assertEqual(self.requests, [])

    @unittest.skipUnless(os.getenv("AZURE_OPENAI_DECISIONS_LIVE_TESTS") == "1",
                         "Set AZURE_OPENAI_DECISIONS_LIVE_TESTS=1 for billable Entra-authenticated Azure tests")
    def test_live_entra_text_and_photo_matrix(self) -> None:
        self.assertTrue(os.getenv("AZURE_OPENAI_ENDPOINT", "").startswith("https://"),
                        "Configure the HTTPS endpoint of an existing Azure OpenAI resource")
        self.assertTrue(os.getenv("AZURE_OPENAI_DEPLOYMENT", "").strip(),
                        "Configure the Azure deployment name for GPT-6 Luna")
        for sample in self.samples:
            for scenario, arguments, names in (
                ("text", [], NAMES),
                ("inline_photo", ["--image", str(PHOTO)], PHOTO_NAMES),
                ("https_photo", ["--image", PHOTO_URL], PHOTO_NAMES),
            ):
                with self.subTest(language=sample.language, scenario=scenario):
                    result = self.run_sample(sample, arguments=arguments, live=True)
                    self.assertEqual(result.returncode, 0, result.stdout)
                    for name in names:
                        self.assertIn(name, result.stdout)
                    self.assertIn("Usage:", result.stdout)
                    print(f"PASS Decisions live: {sample.language} / Entra / {scenario}", flush=True)


if __name__ == "__main__":
    unittest.main()
