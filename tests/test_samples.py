"""Build and exercise the real SDK clients. Live tests require explicit opt-in."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


ROOT = Path(__file__).resolve().parents[1]
EFFORTS = ("low", "medium", "high", "xhigh", "max")
MODEL = "gpt-6.1-sol"
LOCAL_TOKEN = "local-contract-test-token"


@dataclass(frozen=True)
class Sample:
    language: str
    auth: str
    command: list[str]
    directory: Path


@dataclass
class StubState:
    scenario: str = "completed"
    requests: list[dict] = field(default_factory=list)


def handler_for(state: StubState) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            pass

        def do_POST(self) -> None:
            request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            state.requests.append({
                "path": self.path,
                "authorization": self.headers.get("Authorization"),
                "api-key": self.headers.get("api-key"),
                "body": request,
            })
            status = "incomplete" if state.scenario == "incomplete" else "completed"
            text = "" if state.scenario == "empty" else "Local contract test response."
            response = {
                "id": "resp_contract_test",
                "object": "response",
                "created_at": 1790960400,
                "model": request["model"],
                "status": status,
                "error": None,
                "incomplete_details": {"reason": "max_output_tokens"} if status == "incomplete" else None,
                "instructions": None,
                "max_output_tokens": request["max_output_tokens"],
                "parallel_tool_calls": True,
                "tool_choice": "auto",
                "tools": [],
                "temperature": 1.0,
                "top_p": 1.0,
                "reasoning": request["reasoning"],
                "text": {"format": {"type": "text"}},
                "truncation": "disabled",
                "metadata": {},
                "output": [{
                    "id": "msg_contract_test",
                    "type": "message",
                    "role": "assistant",
                    "status": "completed",
                    "content": [{"type": "output_text", "text": text, "annotations": [], "logprobs": []}],
                }],
                "usage": {
                    "input_tokens": 20,
                    "input_tokens_details": {"cached_tokens": 0},
                    "output_tokens": 12,
                    "output_tokens_details": {"reasoning_tokens": 4},
                    "total_tokens": 32,
                },
            }
            if state.scenario == "missing_usage":
                response["usage"] = None
            code = 200
            if self.path != "/openai/v1/responses":
                code = 404
                response = {"error": {"message": "Unexpected request path", "type": "invalid_request_error", "code": "not_found"}}
            elif state.scenario == "http_error":
                code = 400
                response = {"error": {"message": "Contract test rejection", "type": "invalid_request_error", "code": "invalid_request"}}
            payload = json.dumps(response).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    return Handler


def tool(name: str) -> str:
    executable = shutil.which(name)
    if executable is None:
        raise RuntimeError(f"Required tool is missing: {name}. See CLIENT_README.md.")
    return executable


def build(command: list[str], directory: Path) -> None:
    result = subprocess.run(command, cwd=directory, text=True, encoding="utf-8", errors="replace",
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
    if result.returncode:
        raise RuntimeError(f"Build failed ({directory}): {' '.join(command)}\n{result.stdout}")


def build_samples(destination: Path) -> list[Sample]:
    python = ROOT / "src" / "python"
    build([sys.executable, "-c",
           "from importlib.metadata import version; import azure.identity, dotenv; "
           "assert int(version('openai').split('.')[0]) >= 3, 'Install src/python/requirements.txt'"], python)
    typescript = ROOT / "src" / "typescript"
    build([tool("npm"), "run", "build"], typescript)
    java = ROOT / "src" / "java"
    classpath_file = destination / "java-classpath.txt"
    build([tool("mvn"), "--batch-mode", "compile", "dependency:build-classpath",
           f"-Dmdep.outputFile={classpath_file}"], java)
    classpath = str(java / "target" / "classes") + os.pathsep + classpath_file.read_text().strip()
    samples = []
    for auth, suffix, java_suffix in (("key", "", ""), ("entra", "_entra", "Entra")):
        stem = f"responses_example{suffix}"
        samples.append(Sample("Python", auth, [sys.executable, str(python / f"{stem}.py")], python))
        samples.append(Sample("TypeScript", auth, [tool("node"), str(typescript / "dist" / f"{stem}.js")], typescript))
        go = ROOT / "src" / "go" / stem
        executable = destination / (f"go-{auth}.exe" if os.name == "nt" else f"go-{auth}")
        build([tool("go"), "build", "-o", str(executable), "."], go)
        samples.append(Sample("Go", auth, [str(executable)], go))
        dotnet = ROOT / "src" / "dotnet"
        output = destination / f"dotnet-{auth}"
        build([tool("dotnet"), "build", f"{stem}.cs", "--nologo", "--output", str(output)], dotnet)
        samples.append(Sample(".NET", auth, [tool("dotnet"), str(output / f"{stem}.dll")], dotnet))
        samples.append(Sample("Java", auth, [tool("java"), "-cp", classpath,
                                             f"com.azure.openai.starter.ResponsesExample{java_suffix}"], java))
    return samples


def copy_standalone_sample(sample: Sample, destination: Path, java_dependencies: str) -> Sample:
    directory = destination / f"standalone-{sample.language.lower()}-{sample.auth}"
    directory.mkdir()
    suffix = "_entra" if sample.auth == "entra" else ""
    stem = f"responses_example{suffix}"
    if sample.language == "Python":
        source = directory / f"{stem}.py"
        shutil.copyfile(ROOT / "src" / "python" / source.name, source)
        return Sample(sample.language, sample.auth, [sys.executable, str(source)], directory)
    if sample.language == "TypeScript":
        source = directory / f"{stem}.ts"
        shutil.copyfile(ROOT / "src" / "typescript" / source.name, source)
        dependencies = ROOT / "src" / "typescript" / "node_modules"
        build([tool("node"), str(dependencies / "typescript" / "bin" / "tsc"), str(source),
               "--target", "ES2022", "--module", "commonjs", "--strict",
               "--esModuleInterop", "--skipLibCheck", "--moduleResolution", "node",
               "--baseUrl", str(dependencies), "--typeRoots", str(dependencies / "@types"),
               "--types", "node", "--outDir", str(directory / "dist")], directory)
        return Sample(sample.language, sample.auth,
                      [tool("node"), str(directory / "dist" / f"{stem}.js")], directory)
    if sample.language == "Java":
        name = "ResponsesExampleEntra" if sample.auth == "entra" else "ResponsesExample"
        source = directory / f"{name}.java"
        shutil.copyfile(ROOT / "src" / "java" / "src" / "main" / "java" / "com" / "azure"
                        / "openai" / "starter" / source.name, source)
        classes = directory / "classes"
        build([tool("javac"), "--release", "21", "-cp", java_dependencies,
               "-sourcepath", str(directory), "-d", str(classes), str(source)], directory)
        return Sample(sample.language, sample.auth,
                      [tool("java"), "-cp", str(classes) + os.pathsep + java_dependencies,
                       f"com.azure.openai.starter.{name}"], directory)
    raise ValueError(f"Standalone source test is not defined for {sample.language}")


class SampleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(prefix="openai-starter-tests-")
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.samples = build_samples(Path(cls.temporary.name))
        cls.local_cli = Path(cls.temporary.name) / "local-cli"
        cls.local_cli.mkdir()
        token = json.dumps({"accessToken": LOCAL_TOKEN, "expiresOn": "2099-01-01 00:00:00.000000",
                            "expires_on": 4070908800, "tokenType": "Bearer"})
        (cls.local_cli / "az.cmd").write_text(f"@echo off\necho {token}\n", encoding="utf-8")
        cli = cls.local_cli / "az"
        cli.write_text(f"#!/bin/sh\nprintf '%s\\n' '{token}'\n", encoding="utf-8")
        cli.chmod(0o755)
        cls.state = StubState()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(cls.state))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.addClassCleanup(cls.server.server_close)
        cls.addClassCleanup(cls.thread.join)
        cls.addClassCleanup(cls.server.shutdown)
        cls.endpoint = f"http://127.0.0.1:{cls.server.server_port}"

    def setUp(self) -> None:
        self.state.scenario = "completed"
        self.state.requests.clear()

    def run_sample(self, sample: Sample, settings: dict[str, str | None] | None = None,
                   *, live: bool = False) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        for name in list(environment):
            if name.startswith("OPENAI_") or (not live and name.startswith("AZURE_OPENAI_")):
                environment.pop(name)
        environment.update({"PYTHON_DOTENV_DISABLED": "1", "DOTENV_CONFIG_PATH": os.devnull,
                            "PYTHONIOENCODING": "utf-8", "AZURE_TOKEN_CREDENTIALS": "AzureCliCredential"})
        if not live:
            environment.update({"AZURE_OPENAI_ENDPOINT": self.endpoint,
                                "AZURE_OPENAI_API_KEY": "local-contract-test-key"})
        if sample.auth == "entra":
            environment.pop("AZURE_OPENAI_API_KEY", None)
        for name, value in (settings or {}).items():
            if value is None:
                environment.pop(name, None)
            else:
                environment[name] = value
        result = subprocess.run(sample.command, cwd=sample.directory, env=environment, text=True,
                                encoding="utf-8", errors="replace", stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=300 if live else 60)
        key = environment.get("AZURE_OPENAI_API_KEY")
        if key:
            result.stdout = result.stdout.replace(key, "[redacted]")
        return result

    def assert_success(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(result.returncode, 0, result.stdout[-6000:])
        self.assertEqual(len(re.findall(r"Status: completed\b", result.stdout, re.IGNORECASE)), 2, result.stdout)
        self.assertEqual(len(re.findall(r"Response: \S", result.stdout)), 2, result.stdout)
        reasoning = re.findall(r"Reasoning tokens: (\d+)", result.stdout)
        output = re.findall(r"Output tokens: (\d+)", result.stdout)
        self.assertEqual(len(reasoning), 2, result.stdout)
        self.assertEqual(len(output), 2, result.stdout)
        for reasoning_count, output_count in zip(reasoning, output):
            self.assertGreater(int(output_count), 0)
            self.assertLessEqual(int(reasoning_count), int(output_count))

    def assert_requests(self, effort: str = "medium", model: str = MODEL, tokens: int = 16384,
                        auth: str = "key") -> None:
        self.assertEqual(len(self.state.requests), 2)
        for request in self.state.requests:
            self.assertEqual(request["path"], "/openai/v1/responses")
            if auth == "entra":
                self.assertEqual(request["authorization"], f"Bearer {LOCAL_TOKEN}")
                self.assertIsNone(request["api-key"])
            else:
                self.assertTrue(request["authorization"] == "Bearer local-contract-test-key"
                                or request["api-key"] == "local-contract-test-key")
            body = request["body"]
            self.assertEqual(body["model"], model)
            self.assertEqual(body["reasoning"]["effort"], effort)
            self.assertEqual(body["max_output_tokens"], tokens)
            self.assertNotIn("temperature", body)
        first = self.state.requests[0]["body"]["input"]
        if isinstance(first, str):
            self.assertIn("quantum computing", first)
        else:
            # .NET serializes its simple-text helper as a single user message.
            self.assertEqual(len(first), 1)
            self.assertEqual(first[0]["role"], "user")
            self.assertIn("quantum computing", json.dumps(first))
        conversation = self.state.requests[1]["body"]["input"]
        self.assertEqual([message["role"] for message in conversation], ["system", "user"])
        self.assertIn("Azure cloud architect", json.dumps(conversation))
        self.assertIn("scalable web application", json.dumps(conversation))

    def test_defaults_and_endpoint_normalization(self) -> None:
        for sample in self.samples:
            if sample.auth != "key":
                continue
            for ending in ("", "/", "///"):
                with self.subTest(language=sample.language, endpoint_suffix=ending):
                    self.state.requests.clear()
                    self.assert_success(self.run_sample(sample, {"AZURE_OPENAI_ENDPOINT": self.endpoint + ending}))
                    self.assert_requests()

    def test_all_reasoning_efforts(self) -> None:
        for sample in self.samples:
            if sample.auth != "key":
                continue
            for effort in EFFORTS:
                with self.subTest(language=sample.language, effort=effort):
                    self.state.requests.clear()
                    self.assert_success(self.run_sample(sample, {"AZURE_OPENAI_REASONING_EFFORT": effort}))
                    self.assert_requests(effort)

    def test_deployment_and_token_overrides(self) -> None:
        for sample in self.samples:
            if sample.auth != "key":
                continue
            for tokens in (16, 4096, 128000):
                with self.subTest(language=sample.language, tokens=tokens):
                    self.state.requests.clear()
                    self.assert_success(self.run_sample(sample, {
                        "AZURE_OPENAI_GPT_DEPLOYMENT_NAME": "custom-sol-deployment",
                        "AZURE_OPENAI_MAX_OUTPUT_TOKENS": str(tokens),
                    }))
                    self.assert_requests(model="custom-sol-deployment", tokens=tokens)

    def test_copied_examples_run_without_sibling_files(self) -> None:
        destination = Path(self.temporary.name)
        java_dependencies = (destination / "java-classpath.txt").read_text().strip()
        settings = {
            "PYTHONPATH": None,
            "NODE_PATH": str(ROOT / "src" / "typescript" / "node_modules"),
            "PATH": str(self.local_cli) + os.pathsep + os.environ.get("PATH", ""),
        }
        for sample in self.samples:
            if sample.language not in ("Python", "TypeScript", "Java"):
                continue
            with self.subTest(language=sample.language, auth=sample.auth):
                copied = copy_standalone_sample(sample, destination, java_dependencies)
                self.state.requests.clear()
                self.assert_success(self.run_sample(copied, settings))
                self.assert_requests(auth=sample.auth)
                for effort in EFFORTS:
                    self.state.requests.clear()
                    self.assert_success(self.run_sample(copied, {
                        **settings,
                        "AZURE_OPENAI_GPT_DEPLOYMENT_NAME": "copied-sol-deployment",
                        "AZURE_OPENAI_REASONING_EFFORT": effort,
                        "AZURE_OPENAI_MAX_OUTPUT_TOKENS": "4096",
                    }))
                    self.assert_requests(effort, "copied-sol-deployment", 4096, sample.auth)

    def test_invalid_configuration_fails_before_request(self) -> None:
        invalid = [
            ("AZURE_OPENAI_REASONING_EFFORT", value) for value in ("none", "minimal", "invalid", "")
        ] + [
            ("AZURE_OPENAI_MAX_OUTPUT_TOKENS", value)
            for value in ("0", "-1", "1", "15", "1.5", "128001", "invalid", "", "999999999999999999999")
        ]
        for sample in self.samples:
            for name, value in invalid:
                with self.subTest(language=sample.language, auth=sample.auth, setting=name, value=value):
                    self.state.requests.clear()
                    result = self.run_sample(sample, {name: value})
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(name, result.stdout)
                    self.assertEqual(self.state.requests, [])

    def test_required_environment(self) -> None:
        for sample in self.samples:
            required = ["AZURE_OPENAI_ENDPOINT"]
            if sample.auth == "key":
                required.append("AZURE_OPENAI_API_KEY")
            for name in required:
                with self.subTest(language=sample.language, auth=sample.auth, setting=name):
                    self.state.requests.clear()
                    result = self.run_sample(sample, {name: None})
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(name, result.stdout)
                    self.assertEqual(self.state.requests, [])

    def test_unsuccessful_responses_are_not_reported_as_success(self) -> None:
        for sample in self.samples:
            if sample.auth != "key":
                continue
            for scenario, message in (
                ("incomplete", "Response did not complete"),
                ("empty", "Response completed without output text"),
                ("missing_usage", "Response completed without token usage"),
                ("http_error", "Contract test rejection"),
            ):
                with self.subTest(language=sample.language, scenario=scenario):
                    self.state.scenario = scenario
                    self.state.requests.clear()
                    result = self.run_sample(sample)
                    self.assertNotEqual(result.returncode, 0, result.stdout)
                    self.assertIn(message, result.stdout)
                    self.assertNotRegex(result.stdout, r"Status: [Cc]ompleted")
                    self.assertEqual(len(self.state.requests), 1)

    @unittest.skipUnless(os.getenv("AZURE_OPENAI_LIVE_TESTS") == "1", "Set AZURE_OPENAI_LIVE_TESTS=1 to enable billable Azure tests")
    def test_live_matrix(self) -> None:
        self.assertTrue(os.getenv("AZURE_OPENAI_ENDPOINT", "").startswith("https://"),
                        "Live tests require the HTTPS endpoint of a real Azure deployment")
        self.assertTrue(os.getenv("AZURE_OPENAI_API_KEY"), "Live tests require an API key for the key-authentication cases")
        with ThreadPoolExecutor(max_workers=5) as executor:
            jobs = {
                executor.submit(self.run_sample, sample, {"AZURE_OPENAI_REASONING_EFFORT": effort}, live=True):
                (sample, effort)
                for sample in self.samples for effort in EFFORTS
            }
            for job in as_completed(jobs):
                sample, effort = jobs[job]
                with self.subTest(language=sample.language, auth=sample.auth, effort=effort):
                    result = job.result()
                    self.assert_success(result)
                    self.assertIn(f"reasoning effort: {effort}", result.stdout)
                    print(f"PASS live: {sample.language} / {sample.auth} / {effort} / text + conversation", flush=True)

    @unittest.skipUnless(os.getenv("AZURE_OPENAI_LIVE_TESTS") == "1", "Set AZURE_OPENAI_LIVE_TESTS=1 to enable billable Azure tests")
    def test_live_default_configuration(self) -> None:
        self.assertTrue(os.getenv("AZURE_OPENAI_ENDPOINT", "").startswith("https://"))
        self.assertTrue(os.getenv("AZURE_OPENAI_API_KEY"))
        for sample in self.samples:
            with self.subTest(language=sample.language, auth=sample.auth):
                result = self.run_sample(sample, {
                    "AZURE_OPENAI_REASONING_EFFORT": None,
                    "AZURE_OPENAI_MAX_OUTPUT_TOKENS": None,
                }, live=True)
                self.assert_success(result)
                self.assertIn("reasoning effort: medium", result.stdout)
                print(f"PASS live defaults: {sample.language} / {sample.auth} / text + conversation", flush=True)


if __name__ == "__main__":
    unittest.main()
