#!/bin/bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
echo "Validating Azure OpenAI GPT-6.1 Sol template..."
for tool in azd az; do
    if ! command -v "$tool" > /dev/null; then
        echo "Required command not found: $tool" >&2
        exit 1
    fi
done
azd version > /dev/null

required_files=(
    "azure.yaml"
    "infra/main.bicep"
    "infra/resources.bicep"
    "infra/main.parameters.json"
    "src/python/responses_example.py"
    "src/python/responses_example_entra.py"
    "src/typescript/responses_example.ts"
    "src/typescript/responses_example_entra.ts"
    "src/go/responses_example/main.go"
    "src/go/responses_example_entra/main.go"
    "src/dotnet/responses_example.cs"
    "src/dotnet/responses_example_entra.cs"
    "src/java/pom.xml"
    "src/java/src/main/java/com/azure/openai/starter/ResponsesExample.java"
    "src/java/src/main/java/com/azure/openai/starter/ResponsesExampleEntra.java"
)

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "Required file not found: $file" >&2
        exit 1
    fi
done
echo "All required infrastructure and source files found"

if ! az bicep build --file infra/main.bicep --stdout > /dev/null; then
    echo "Bicep template validation failed" >&2
    exit 1
fi

echo "Template validation successful (no resources deployed)."
echo "For client contract tests: python -m unittest discover -s tests -v"
