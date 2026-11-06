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
# The multimodal examples send this public-domain photo when no image is given.
DEFAULT_PHOTO_URL = "https://raw.githubusercontent.com/scikit-image/scikit-image/v0.25.2/skimage/data/astronaut.png"
HOSTED_PHOTO_URL = "https://example.invalid/photo.png"
PHOTO_NAMES = ["visible_damage", "category", "severity"]


def message_text(value: list) -> str:
    """Return the text of an input made of a single user message with one text part.

    The typed .NET client always sends a text input as one user message, while the other
    clients send the plain string. The API accepts both forms of the same input.
    """
    if len(value) != 1 or value[0]["role"] != "user":
        raise AssertionError(f"Expected one user message: {value!r}")
    content = value[0]["content"]
    if len(content) != 1 or content[0]["type"] != "input_text":
        raise AssertionError(f"Expected one input_text part: {content!r}")
    return content[0]["text"]


class DecisionsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(prefix="openai-decisions-tests-")
        cls.addClassCleanup(cls.temporary.cleanup)
        destination = Path(cls.temporary.name)
        languages = selected_languages(include_ruby=True)
        if not languages:
            raise unittest.SkipTest("No Decisions languages selected")
        # Each language has a text example and a multimodal (text and image) example.
        cls.samples = []
        cls.photo_samples = []
        stems = (("decisions_example", cls.samples), ("decisions_multimodal_example", cls.photo_samples))
        if "Python" in languages:
            python = ROOT / "src" / "python"
            for stem, samples in stems:
                samples.append(Sample("Python", "key", [sys.executable, str(python / f"{stem}.py")], python))
        typescript = ROOT / "src" / "typescript"
        if "TypeScript" in languages:
            build([tool("npm"), "run", "build"], typescript)
            for stem, samples in stems:
                samples.append(Sample(
                    "TypeScript", "key", [tool("node"), str(typescript / "dist" / f"{stem}.js")], typescript,
                ))
        if "Go" in languages:
            for stem, samples in stems:
                go = ROOT / "src" / "go" / stem
                executable = destination / (f"{stem}.exe" if os.name == "nt" else stem)
                build([tool("go"), "build", "-o", str(executable), "."], go)
                samples.append(Sample("Go", "key", [str(executable)], go))
        java = ROOT / "src" / "java"
        classpath_file = destination / "classpath.txt"
        if "Java" in languages:
            build([tool("mvn"), "--batch-mode", "compile", "dependency:build-classpath",
                   f"-Dmdep.outputFile={classpath_file}"], java)
            classpath = str(java / "target" / "classes") + os.pathsep + classpath_file.read_text().strip()
            for (_, samples), class_name in zip(stems, ("DecisionsExample", "DecisionsMultimodalExample")):
                samples.append(Sample(
                    "Java", "key", [tool("java"), "-cp", classpath, f"com.azure.openai.starter.{class_name}"], java,
                ))
        dotnet = ROOT / "src" / "dotnet"
        if ".NET" in languages:
            for stem, samples in stems:
                output = destination / f"dotnet-{stem}"
                build([tool("dotnet"), "build", f"{stem}.cs", "--nologo", "--output", str(output)], dotnet)
                samples.append(Sample(".NET", "key", [tool("dotnet"), str(output / f"{stem}.dll")], dotnet))
        ruby = ROOT / "src" / "ruby"
        if "Ruby" in languages:
            build([tool("bundle"), "check"], ruby)
            for stem, samples in stems:
                samples.append(Sample("Ruby", "key", [tool("bundle"), "exec", "ruby", f"{stem}.rb"], ruby))
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
                elif cls.scenario == "null_choice":
                    answers[1]["choice"] = None
                elif cls.scenario == "missing_choice":
                    answers[1].pop("choice")
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
                elif cls.scenario == "usage_no_details":
                    response["usage"].pop("input_tokens_details")
                    response["usage"].pop("output_tokens_details")
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

    def assert_request(self, deployment: str = "gpt-6-luna", *, user_message_input: bool = False) -> None:
        self.assertEqual(len(self.requests), 1)
        request = self.requests[0]
        self.assertEqual(request["path"], "/openai/v1/decisions")
        self.assertTrue(request["authorization"] == "Bearer local-contract-test-key"
                        or request["api-key"] == "local-contract-test-key")
        self.assertIsNone(request["content-encoding"])
        body = request["body"]
        self.assertEqual(body["model"], deployment)
        # Only the typed .NET client wraps a text input in a user message; every other client sends the string.
        if user_message_input:
            self.assertEqual(message_text(body["input"]), INPUT)
        else:
            self.assertEqual(body["input"], INPUT)
        self.assertEqual([item["name"] for item in body["questions"]], NAMES)
        self.assertEqual([item["type"] for item in body["questions"]], ["predicate", "choice", "score"])
        self.assertEqual(body["questions"][1]["choices"][0]["value"], "billing")
        self.assertEqual([item["label"] for item in body["questions"][2]["levels"]], ["Low", "Medium", "High"])
        for field in ("reasoning", "temperature", "max_output_tokens", "stream"):
            self.assertNotIn(field, body)

    def assert_photo_request(self) -> str:
        """Check the multimodal request and return the image it carries."""
        self.assertEqual(len(self.requests), 1)
        request = self.requests[0]
        self.assertEqual(request["path"], "/openai/v1/decisions")
        self.assertIsNone(request["content-encoding"])
        body = request["body"]
        self.assertEqual(body["model"], "gpt-6-luna")
        self.assertEqual([question["name"] for question in body["questions"]], PHOTO_NAMES)
        self.assertEqual([item["type"] for item in body["questions"]], ["predicate", "choice", "score"])
        self.assertEqual(body["questions"][1]["choices"][-1]["value"], "other")
        self.assertEqual(len(body["input"]), 1)
        self.assertEqual(body["input"][0]["role"], "user")
        content = body["input"][0]["content"]
        self.assertEqual([part["type"] for part in content], ["input_text", "input_image"])
        return content[1]["image_url"]

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
                    self.assert_request(deployment, user_message_input=sample.language == ".NET")

    def test_python_discovers_dotenv_without_overriding_environment(self) -> None:
        if not any(sample.language == "Python" for sample in self.samples):
            self.skipTest("Python was not selected")
        with tempfile.TemporaryDirectory(prefix="decisions-dotenv-") as temporary:
            directory = Path(temporary)
            sample_directory = directory / "sample"
            sample_directory.mkdir()
            working_directory = directory / "working"
            working_directory.mkdir()
            script = sample_directory / "decisions_example.py"
            script.write_bytes((ROOT / "src" / "python" / "decisions_example.py").read_bytes())
            copied = Sample("Python", "key", [sys.executable, str(script)], working_directory)
            dotenv = (
                f"AZURE_OPENAI_ENDPOINT={self.endpoint}\n"
                "AZURE_OPENAI_API_KEY=local-contract-test-key\n"
            )
            (directory / ".env").write_text(
                dotenv + "AZURE_OPENAI_DEPLOYMENT=parent-luna\n", encoding="utf-8",
            )
            nearest = sample_directory / ".env"
            for use_nearest, deployment, expected in (
                (True, None, "sample-luna"),
                (False, None, "parent-luna"),
                (True, "environment-luna", "environment-luna"),
            ):
                with self.subTest(nearest=use_nearest, environment_deployment=deployment):
                    if use_nearest:
                        nearest.write_text(
                            dotenv + "AZURE_OPENAI_DEPLOYMENT=sample-luna\n", encoding="utf-8",
                        )
                    else:
                        nearest.unlink()
                    self.requests.clear()
                    result = self.run_sample(copied, {
                        "PYTHON_DOTENV_DISABLED": None,
                        "AZURE_OPENAI_ENDPOINT": None,
                        "AZURE_OPENAI_API_KEY": None,
                        "AZURE_OPENAI_DEPLOYMENT": deployment,
                    })
                    self.assertEqual(result.returncode, 0, result.stdout)
                    self.assert_request(expected)

    def test_refusals_are_handled_explicitly(self) -> None:
        type(self).scenario = "refusal"
        for sample in [*self.samples, *self.photo_samples]:
            with self.subTest(language=sample.language, example=sample.command[-1]):
                self.requests.clear()
                result = self.run_sample(sample)
                self.assertEqual(result.returncode, 0, result.stdout)
                self.assertIn("refus", result.stdout.lower())
                self.assertEqual(len(self.requests), 1)

    def test_http_errors_are_reported(self) -> None:
        for sample in [*self.samples, *self.photo_samples]:
            for scenario, message in (
                ("http_error", "Contract test rejection"),
                ("deployment_not_found", "The specified deployment does not exist."),
            ):
                with self.subTest(language=sample.language, example=sample.command[-1], scenario=scenario):
                    type(self).scenario = scenario
                    self.requests.clear()
                    result = self.run_sample(sample)
                    self.assertNotEqual(result.returncode, 0, result.stdout)
                    self.assertIn(message, result.stdout)
                    self.assertEqual(len(self.requests), 1)

    def test_unusable_responses_fail(self) -> None:
        for sample in [*self.samples, *self.photo_samples]:
            for scenario in ("empty", "missing_usage", "unknown"):
                with self.subTest(language=sample.language, example=sample.command[-1], scenario=scenario):
                    type(self).scenario = scenario
                    self.requests.clear()
                    result = self.run_sample(sample)
                    self.assertNotEqual(result.returncode, 0, result.stdout)
                    self.assertEqual(len(self.requests), 1)

    def test_missing_endpoint_fails_before_request(self) -> None:
        for sample in [*self.samples, *self.photo_samples]:
            with self.subTest(language=sample.language, example=sample.command[-1]):
                result = self.run_sample(sample, {"AZURE_OPENAI_ENDPOINT": None})
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn("AZURE_OPENAI_ENDPOINT", result.stdout)
                self.assertEqual(self.requests, [])

    def test_dotnet_rejects_malformed_endpoints_before_any_request(self) -> None:
        for sample in [*self.samples, *self.photo_samples]:
            if sample.language != ".NET":
                continue
            for setting in ("AZURE_OPENAI_ENDPOINT", "Clients__Decisions__Options__Endpoint"):
                for endpoint in ("", "example.invalid", "/openai/v1/"):
                    with self.subTest(example=sample.command[-1], setting=setting, endpoint=endpoint):
                        self.requests.clear()
                        result = self.run_sample(sample, {setting: endpoint})
                        self.assertNotEqual(result.returncode, 0, result.stdout)
                        self.assertIn("must be an absolute URL", result.stdout)
                        self.assertEqual(self.requests, [])

    def test_dotnet_optional_usage_details_and_required_choice(self) -> None:
        for sample in [*self.samples, *self.photo_samples]:
            if sample.language != ".NET":
                continue
            for scenario in ("usage_no_details", "null_choice", "missing_choice"):
                with self.subTest(example=sample.command[-1], scenario=scenario):
                    type(self).scenario = scenario
                    self.requests.clear()
                    result = self.run_sample(sample)
                    if scenario == "usage_no_details":
                        self.assertEqual(result.returncode, 0, result.stdout)
                        self.assertIn("Usage:", result.stdout)
                    else:
                        self.assertNotEqual(result.returncode, 0, result.stdout)
                        self.assertIn("A choice must be a string or a boolean", result.stdout)
                    self.assertEqual(len(self.requests), 1)

    def test_dotnet_client_is_configured_through_dependency_injection(self) -> None:
        for sample in [*self.samples, *self.photo_samples]:
            if sample.language != ".NET":
                continue
            with self.subTest(example=sample.command[-1]):
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
                self.assertEqual(len(self.requests), 1)
                self.assertEqual(self.requests[0]["body"]["model"], "configured-luna")
                self.assertIn("Usage:", result.stdout)

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
        for stem in ("decisions_example", "decisions_multimodal_example", "responses_example_entra"):
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

    def test_developer_cli_receives_the_resource_tenant(self) -> None:
        tenant = "00000000-0000-0000-0000-000000000000"
        # Python, .NET and Ruby always use the Azure Developer CLI. Go's default credential chain
        # is told to use it with the standard AZURE_TOKEN_CREDENTIALS selection.
        for sample in [*self.samples, *self.photo_samples]:
            if sample.language not in ("Python", ".NET", "Go", "Ruby"):
                continue
            sources = [None, "AzureDeveloperCliCredential"] if sample.language == ".NET" else [None]
            for source in sources:
                with self.subTest(language=sample.language, example=sample.command[-1], source=source):
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
                            "AZURE_TOKEN_CREDENTIALS": "AzureDeveloperCliCredential" if sample.language == "Go" else None,
                            "AZURE_TENANT_ID": tenant,
                            "Clients__Decisions__Credential__CredentialSource": source,
                            "PATH": str(directory) + os.pathsep + os.environ.get("PATH", ""),
                            "STARTER_TEST_CLI_ARGUMENTS": str(recorded),
                        })
                        self.assertNotEqual(result.returncode, 0, result.stdout)
                        self.assertTrue(recorded.is_file(), result.stdout)
                        arguments = recorded.read_text(encoding="utf-8")
                        self.assertIn("auth", arguments)
                        self.assertIn("token", arguments)
                        self.assertIn("--tenant-id", arguments)
                        self.assertIn(tenant, arguments)
                        self.assertIn("--scope", arguments)
                        self.assertIn("https://cognitiveservices.azure.com/.default", arguments)
                        self.assertEqual(self.requests, [])

    def test_photo_inputs_default_hosted_and_inline(self) -> None:
        photo_bytes = PHOTO.read_bytes()
        self.assertTrue(photo_bytes.startswith(b"\x89PNG\r\n\x1a\n"))
        for sample in self.photo_samples:
            for source, label in ((None, "default"), (HOSTED_PHOTO_URL, "hosted"), (str(PHOTO), "inline")):
                with self.subTest(language=sample.language, source=label):
                    self.requests.clear()
                    result = self.run_sample(sample, arguments=[] if source is None else [source])
                    self.assertEqual(result.returncode, 0, result.stdout)
                    image = self.assert_photo_request()
                    if source is None:
                        self.assertEqual(image, DEFAULT_PHOTO_URL)
                    elif source == HOSTED_PHOTO_URL:
                        self.assertEqual(image, HOSTED_PHOTO_URL)
                    else:
                        prefix, encoded = image.split(",", 1)
                        self.assertEqual(prefix, "data:image/png;base64")
                        self.assertEqual(base64.b64decode(encoded, validate=True), photo_bytes)
                    for name in PHOTO_NAMES:
                        self.assertIn(name, result.stdout)
                    self.assertIn("probabilities=", result.stdout)
                    self.assertIn("Usage:", result.stdout)

    @unittest.skipUnless(os.getenv("AZURE_OPENAI_DECISIONS_LIVE_TESTS") == "1",
                         "Set AZURE_OPENAI_DECISIONS_LIVE_TESTS=1 for billable Entra-authenticated Azure tests")
    def test_live_entra_text_and_photo_matrix(self) -> None:
        self.assertTrue(os.getenv("AZURE_OPENAI_ENDPOINT", "").startswith("https://"),
                        "Configure the HTTPS endpoint of an existing Azure OpenAI resource")
        self.assertTrue(os.getenv("AZURE_OPENAI_DEPLOYMENT", "").strip(),
                        "Configure the Azure deployment name for GPT-6 Luna")
        scenarios = [(sample, "text", [], NAMES) for sample in self.samples]
        for sample in self.photo_samples:
            scenarios.append((sample, "hosted_photo", [], PHOTO_NAMES))
            scenarios.append((sample, "inline_photo", [str(PHOTO)], PHOTO_NAMES))
        for sample, scenario, arguments, names in scenarios:
            with self.subTest(language=sample.language, scenario=scenario):
                result = self.run_sample(sample, arguments=arguments, live=True)
                self.assertEqual(result.returncode, 0, result.stdout)
                for name in names:
                    self.assertIn(name, result.stdout)
                self.assertIn("Usage:", result.stdout)
                print(f"PASS Decisions live: {sample.language} / Entra / {scenario}", flush=True)


if __name__ == "__main__":
    unittest.main()
