"""Regression tests for both shell validators, without cloud access."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "azure.yaml",
    "infra/main.bicep",
    "infra/resources.bicep",
    "infra/main.parameters.json",
    "src/python/responses_example.py",
    "src/python/responses_example_entra.py",
    "src/typescript/responses_example.ts",
    "src/typescript/responses_example_entra.ts",
    "src/go/responses_example/main.go",
    "src/go/responses_example_entra/main.go",
    "src/dotnet/responses_example.cs",
    "src/dotnet/responses_example_entra.cs",
    "src/java/pom.xml",
    "src/java/src/main/java/com/azure/openai/starter/ResponsesExample.java",
    "src/java/src/main/java/com/azure/openai/starter/ResponsesExampleEntra.java",
]


class ValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runners: list[tuple[str, list[str]]] = []
        pwsh = shutil.which("pwsh")
        if pwsh:
            cls.runners.append(("validate.ps1", [pwsh, "-NoProfile", "-File"]))
        if os.name == "nt":
            git = shutil.which("git")
            bash = Path(git).parent.parent / "bin" / "bash.exe" if git else None
            if bash and bash.is_file():
                cls.runners.append(("validate.sh", [str(bash)]))
        else:
            bash_command = shutil.which("bash")
            if bash_command:
                cls.runners.append(("validate.sh", [bash_command]))
        if not cls.runners:
            raise unittest.SkipTest("Neither PowerShell nor Bash is available")

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="openai-validator-tests-")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.project = self.directory / "project"
        self.bin = self.directory / "bin"
        self.bin.mkdir()
        for relative in REQUIRED:
            path = self.project / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
        for script, _ in self.runners:
            shutil.copyfile(ROOT / script, self.project / script)
        for name in ("az", "azd"):
            variable = f"MOCK_{name.upper()}_EXIT"
            shim = self.bin / name
            shim.write_text(f'#!/bin/sh\nexit "${{{variable}:-0}}"\n', encoding="utf-8")
            shim.chmod(0o755)
            (self.bin / f"{name}.cmd").write_text(
                f'@echo off\nif defined {variable} exit /b %{variable}%\nexit /b 0\n',
                encoding="utf-8",
            )

    def run_validator(self, script: str, command: list[str],
                      settings: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["PATH"] = str(self.bin) + os.pathsep + environment.get("PATH", "")
        environment.pop("MOCK_AZ_EXIT", None)
        environment.pop("MOCK_AZD_EXIT", None)
        environment.update(settings or {})
        return subprocess.run([*command, str(self.project / script)], cwd=self.directory,
                              env=environment, text=True, encoding="utf-8", errors="replace",
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)

    def test_success_from_another_directory(self) -> None:
        for script, command in self.runners:
            with self.subTest(script=script):
                result = self.run_validator(script, command)
                self.assertEqual(result.returncode, 0, result.stdout)
                self.assertIn("Template validation successful", result.stdout)

    def test_every_required_file_is_checked(self) -> None:
        for relative in REQUIRED:
            path = self.project / relative
            path.unlink()
            try:
                for script, command in self.runners:
                    with self.subTest(script=script, missing=relative):
                        result = self.run_validator(script, command)
                        self.assertNotEqual(result.returncode, 0, result.stdout)
                        self.assertIn("Required file not found", result.stdout)
                        self.assertNotIn("Template validation successful", result.stdout)
            finally:
                path.touch()

    def test_cli_failures_propagate(self) -> None:
        for script, command in self.runners:
            for variable in ("MOCK_AZ_EXIT", "MOCK_AZD_EXIT"):
                with self.subTest(script=script, failing_tool=variable):
                    result = self.run_validator(script, command, {variable: "9"})
                    self.assertNotEqual(result.returncode, 0, result.stdout)
                    self.assertNotIn("Template validation successful", result.stdout)


if __name__ == "__main__":
    unittest.main()
