# Azure OpenAI GPT-5-mini Template - azd Template

This workspace contains a minimal Azure Developer CLI (azd) template for deploying GPT-5-mini on Azure OpenAI.

## ✅ Completed Template Features:
- **One-command deployment**: `azd up` deploys GPT-5-mini in Sweden Central
- **GPT-5-mini (2025-08-07)**: Latest reasoning model, no registration required
- **New v1 API support**: Future-proof, no version management needed
- **GlobalStandard SKU**: Optimal performance and availability
- **Responses API Examples**: Python and TypeScript using the new Responses API
- **Complete documentation**: Setup guides and troubleshooting
- **Validation scripts**: PowerShell and Bash for testing

## Template Structure:
```
├── azure.yaml                 # azd configuration
├── infra/
│   ├── main.bicep             # Main deployment (subscription scope)
│   ├── main.parameters.json   # Parameters (Sweden Central default)
│   └── resources.bicep        # Azure OpenAI + GPT-5-mini deployment
├── src/
│   ├── python/
│   │   ├── responses_example.py  # Responses API example
│   │   └── requirements.txt      # Python dependencies
│   └── typescript/
│       ├── responses_example.ts  # Responses API example
│       ├── package.json          # Node.js dependencies  
│       └── tsconfig.json         # TypeScript configuration
├── CLIENT_README.md           # Setup guide for both languages
├── README.md                  # Main documentation
├── validate.ps1/.sh          # Validation scripts
└── .github/copilot-instructions.md # This file
```

## Key Configuration:
- **Region**: Sweden Central (swedencentral) - optimal for European users
- **Model**: GPT-5-mini (2025-08-07) with GlobalStandard SKU
- **API**: New v1 endpoint format for future compatibility
- **Deployment name**: `gpt-5-mini` (descriptive naming)
- **Resource naming**: Auto-generated unique names with resourceToken

## Usage Instructions:
1. **Deploy**: `azd auth login && azd up`
2. **Get details**: `azd env get-values`
3. **Get API key**: `az cognitiveservices account keys list --name RESOURCE_NAME --resource-group rg-ENV_NAME`
4. **Test Python**: `cd src/python && python responses_example.py`
5. **Test TypeScript**: `cd src/typescript && npm start`

## Template Benefits:
- ✅ **Minimal setup** - No complex configuration or containers
- ✅ **Latest AI model** - GPT-5-mini with reasoning capabilities  
- ✅ **Production-ready** - Proper resource naming and configuration
- ✅ **Future-proof** - v1 API eliminates version management
- ✅ **Responses API** - Cleaner interface optimized for reasoning models
- ✅ **Complete examples** - Working Python and TypeScript clients included
- ✅ **Easy cleanup** - `azd down` removes everything

## API Notes:
- **Responses API**: Cleaner interface optimized for reasoning models like GPT-5-mini
- Uses `max_output_tokens=1000` to account for GPT-5-mini's internal reasoning
- Reasoning tokens are visible in usage statistics via `response.usage.output_tokens_details.reasoning_tokens`
- Supports both simple text input and conversation format

The template is production-ready and validated for external customer use!
