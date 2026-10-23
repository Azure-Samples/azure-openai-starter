"""Exercise all six real Decisions clients against a local HTTP contract."""

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
                })
                answers = [
                    {"type": "predicate", "name": NAMES[0], "probability": 0.95},
                    {"type": "choice", "name": NAMES[1], "choice": "billing", "confidence": 0.9,
                     "probabilities": [{"value": "billing", "probability": 0.9},
                                       {"value": "technical", "probability": 0.05},
                                       {"value": "other", "probability": 0.05}]},
                    {"type": "score", "name": NAMES[2], "score": 1.1, "confidence": 0.55,
                     "probabilities": [{"label": "Low", "value": 0, "probability": 0.1},
                                       {"label": "Medium", "value": 1, "probability": 0.7},
                                       {"label": "High", "value": 2, "probability": 0.2}]},
                ]
                if cls.scenario == "refusal":
                    answers = [{"type": "refusal", "name": name} for name in NAMES]
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

    def run_sample(self, sample: Sample, settings: dict[str, str | None] | None = None) -> subprocess.CompletedProcess:
        environment = os.environ.copy()
        for name in list(environment):
            if name.startswith(("OPENAI_", "AZURE_OPENAI_")):
                environment.pop(name)
        environment.update({
            "AZURE_OPENAI_ENDPOINT": self.endpoint,
            "AZURE_OPENAI_API_KEY": "local-contract-test-key",
            "PYTHON_DOTENV_DISABLED": "1",
            "DOTENV_CONFIG_PATH": os.devnull,
            "PYTHONIOENCODING": "utf-8",
        })
        for name, value in (settings or {}).items():
            if value is None:
                environment.pop(name, None)
            else:
                environment[name] = value
        result = subprocess.run(sample.command, cwd=sample.directory, env=environment,
                                capture_output=True, text=True, encoding="utf-8",
                                errors="replace", timeout=60)
        result.stdout += result.stderr
        result.stdout = result.stdout.replace("local-contract-test-key", "[redacted]")
        return result

    def assert_request(self, deployment: str = "gpt-6-luna") -> None:
        self.assertEqual(len(self.requests), 1)
        request = self.requests[0]
        self.assertEqual(request["path"], "/openai/v1/decisions")
        self.assertTrue(request["authorization"] == "Bearer local-contract-test-key"
                        or request["api-key"] == "local-contract-test-key")
        body = request["body"]
        self.assertEqual(body["model"], deployment)
        self.assertEqual(body["input"], INPUT)
        self.assertEqual([item["name"] for item in body["questions"]], NAMES)
        self.assertEqual([item["type"] for item in body["questions"]], ["predicate", "choice", "score"])
        self.assertEqual(body["questions"][1]["choices"][0]["value"], "billing")
        self.assertEqual([item["label"] for item in body["questions"][2]["levels"]], ["Low", "Medium", "High"])
        for field in ("reasoning", "temperature", "max_output_tokens"):
            self.assertNotIn(field, body)

    def test_defaults_endpoint_normalization_and_deployment_override(self) -> None:
        for sample in self.samples:
            for ending, deployment in (("", "gpt-6-luna"), ("/", "custom-luna"), ("///", "custom-luna")):
                with self.subTest(language=sample.language, endpoint_suffix=ending):
                    self.requests.clear()
                    settings = {"AZURE_OPENAI_ENDPOINT": self.endpoint + ending}
                    if deployment != "gpt-6-luna":
                        settings["AZURE_OPENAI_DECISIONS_DEPLOYMENT_NAME"] = deployment
                    result = self.run_sample(sample, settings)
                    self.assertEqual(result.returncode, 0, result.stdout)
                    for name in NAMES:
                        self.assertIn(name, result.stdout)
                    for kind in ("predicate", "choice", "score"):
                        self.assertIn(kind, result.stdout.lower())
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
            for scenario in ("http_error", "empty", "missing_usage", "unknown"):
                with self.subTest(language=sample.language, scenario=scenario):
                    type(self).scenario = scenario
                    self.requests.clear()
                    result = self.run_sample(sample)
                    self.assertNotEqual(result.returncode, 0, result.stdout)
                    self.assertEqual(len(self.requests), 1)
                    if scenario == "http_error":
                        self.assertIn("Contract test rejection", result.stdout)

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
                    result = self.run_sample(sample, {"AZURE_OPENAI_DECISIONS_DEPLOYMENT_NAME": value})
                    self.assertNotEqual(result.returncode, 0, result.stdout)
                    self.assertIn("AZURE_OPENAI_DECISIONS_DEPLOYMENT_NAME", result.stdout)
                    self.assertEqual(self.requests, [])


if __name__ == "__main__":
    unittest.main()
