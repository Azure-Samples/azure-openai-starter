# Validation script for Azure OpenAI azd template
# PowerShell version

Write-Host "🔍 Validating Azure OpenAI azd template..." -ForegroundColor Cyan

# Check if azd is installed
try {
    azd version | Out-Null
    Write-Host "✅ Azure Developer CLI (azd) is installed" -ForegroundColor Green
} catch {
    Write-Host "❌ Azure Developer CLI (azd) is not installed" -ForegroundColor Red
    Write-Host "💡 Install it from: https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/install-azd" -ForegroundColor Yellow
    exit 1
}

# Check if azure.yaml exists
if (-not (Test-Path "azure.yaml")) {
    Write-Host "❌ azure.yaml not found" -ForegroundColor Red
    exit 1
}

# Check if infra directory exists
if (-not (Test-Path "infra" -PathType Container)) {
    Write-Host "❌ infra directory not found" -ForegroundColor Red
    exit 1
}

# Check if main.bicep exists
if (-not (Test-Path "infra/main.bicep")) {
    Write-Host "❌ infra/main.bicep not found" -ForegroundColor Red
    exit 1
}

# Check if main.parameters.json exists
if (-not (Test-Path "infra/main.parameters.json")) {
    Write-Host "❌ infra/main.parameters.json not found" -ForegroundColor Red
    exit 1
}

Write-Host "✅ All required files found" -ForegroundColor Green

# Validate Bicep template if Azure CLI is available
try {
    az version | Out-Null
    Write-Host "🔧 Validating Bicep template..." -ForegroundColor Cyan
    
    $buildResult = az bicep build --file infra/main.bicep 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Bicep template is valid" -ForegroundColor Green
    } else {
        Write-Host "❌ Bicep template validation failed" -ForegroundColor Red
        Write-Host $buildResult -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "⚠️  Azure CLI not found - skipping Bicep validation" -ForegroundColor Yellow
}

Write-Host "🎉 Template validation successful!" -ForegroundColor Green
Write-Host "🚀 You can now run: azd up" -ForegroundColor Cyan
