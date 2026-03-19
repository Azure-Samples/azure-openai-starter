#!/bin/bash
# Validation script for Azure OpenAI azd template

echo "🔍 Validating Azure OpenAI azd template..."

# Check if azd is installed
if ! command -v azd &> /dev/null; then
    echo "❌ Azure Developer CLI (azd) is not installed"
    echo "💡 Install it from: https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/install-azd"
    exit 1
fi

# Check if azure.yaml exists
if [ ! -f "azure.yaml" ]; then
    echo "❌ azure.yaml not found"
    exit 1
fi

# Check if infra directory exists
if [ ! -d "infra" ]; then
    echo "❌ infra directory not found"
    exit 1
fi

# Check if main.bicep exists
if [ ! -f "infra/main.bicep" ]; then
    echo "❌ infra/main.bicep not found"
    exit 1
fi

# Check if main.parameters.json exists
if [ ! -f "infra/main.parameters.json" ]; then
    echo "❌ infra/main.parameters.json not found"
    exit 1
fi

echo "✅ All required infra files found"

# Check source examples
source_files=(
    "src/python/responses_example.py"
    "src/python/responses_example_entra.py"
    "src/typescript/responses_example.ts"
    "src/typescript/responses_example_entra.ts"
    "src/go/responses_example/main.go"
    "src/go/responses_example_entra/main.go"
    "src/dotnet/responses_example.cs"
    "src/dotnet/responses_example_entra.cs"
    "src/java/pom.xml"
)

all_sources_found=true
for file in "${source_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ $file not found"
        all_sources_found=false
    fi
done

if [ "$all_sources_found" = true ]; then
    echo "✅ All source examples found"
else
    echo "⚠️  Some source examples are missing"
fi

# Validate Bicep template if Azure CLI is available
if command -v az &> /dev/null; then
    echo "🔧 Validating Bicep template..."
    if az bicep build --file infra/main.bicep &> /dev/null; then
        echo "✅ Bicep template is valid"
    else
        echo "❌ Bicep template validation failed"
        exit 1
    fi
else
    echo "⚠️  Azure CLI not found - skipping Bicep validation"
fi

echo "🎉 Template validation successful!"
echo "🚀 You can now run: azd up"
