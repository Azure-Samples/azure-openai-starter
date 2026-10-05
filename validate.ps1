Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "Validating Azure OpenAI GPT-6.1 Sol template..." -ForegroundColor Cyan
Push-Location $PSScriptRoot
try {
    foreach ($command in @("azd", "az")) {
        if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
            throw "Required command not found: $command"
        }
    }
    azd version | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Azure Developer CLI (azd) failed"
    }

    $requiredFiles = @(
        "azure.yaml",
        "infra\main.bicep",
        "infra\resources.bicep",
        "infra\main.parameters.json",
        "src\python\responses_example.py",
        "src\python\responses_example_entra.py",
        "src\typescript\responses_example.ts",
        "src\typescript\responses_example_entra.ts",
        "src\go\responses_example\main.go",
        "src\go\responses_example_entra\main.go",
        "src\dotnet\responses_example.cs",
        "src\dotnet\responses_example_entra.cs",
        "src\java\pom.xml",
        "src\java\src\main\java\com\azure\openai\starter\ResponsesExample.java",
        "src\java\src\main\java\com\azure\openai\starter\ResponsesExampleEntra.java"
    )
    foreach ($file in $requiredFiles) {
        if (-not (Test-Path $file -PathType Leaf)) {
            throw "Required file not found: $file"
        }
    }
    Write-Host "All required infrastructure and source files found" -ForegroundColor Green

    az bicep build --file "infra\main.bicep" --stdout | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Bicep template validation failed"
    }
    Write-Host "Template validation successful (no resources deployed)." -ForegroundColor Green
    Write-Host "For client contract tests: python -m unittest discover -s tests -v" -ForegroundColor Cyan
} finally {
    Pop-Location
}
