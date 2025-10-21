---
page_type: sample
languages:
- python
- typescript
products:
- azure-openai
- azure
urlFragment: azure-openai-starter
name: The Azure OpenAI Starter Kit
description: Deploy Azure OpenAI with GPT-5-mini using one CLI command. Includes OpenAI SDK for Python and TypeScript examples using the Responses API.
---

# The Azure OpenAI Starter Kit

**The fastest way to get started with Azure OpenAI.** 

Rapidly deploy an Azure OpenAI instance with a GPT-5-mini model using a single CLI command. Includes OpenAI SDK for Python and TypeScript examples using the  Responses API. 

## Quick Start

```bash
# 1. Login to Azure
azd auth login

# 2. Deploy GPT-5-mini to Azure OpenAI in Sweden Central 
azd up
```
**Don't have azd?** Install it: https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd

That's it! 🚀 You now have **Azure OpenAI** with **GPT-5-mini** model deployed and ready to use!

## Next Steps

### 1. Get Your Connection Details
```bash
# See all your deployment info
azd env get-values

# Key outputs you'll need:
# AZURE_ENV_NAME=YOUR_ENV_NAME
# AZURE_OPENAI_NAME=YOUR_RESOURCE_NAME
# AZURE_OPENAI_ENDPOINT=YOUR_ENDPOINT
# AZURE_OPENAI_GPT_DEPLOYMENT_NAME=YOUR_MODEL
```

### 2. Get Your API Key
```bash
# Copy and paste the 2 azd env values from above, then run:
az cognitiveservices account keys list --name YOUR_RESOURCE_NAME --resource-group rg-YOUR_ENV_NAME
```
**Don't have az?** Install it: https://learn.microsoft.com/en-us/cli/azure/install-azure-cli

### 3. Start Using GPT-5-mini

**📖 See [CLIENT_README.md](CLIENT_README.md) for detailed setup (Python & TypeScript)**

**Quick examples using the new Responses API:**

**Python:**
```python
from openai import OpenAI

client = OpenAI(
    api_key="YOUR_API_KEY", 
    base_url="YOUR_ENDPOINT/openai/v1/"  # Note the /v1/ suffix
)

response = client.responses.create(
    model="YOUR_MODEL",  # This is your deployment name
    input="Explain quantum computing in simple terms",
    max_output_tokens=1000  # Higher for reasoning models
)
print(response.output_text)
```

**TypeScript/Node.js:**
```typescript
import OpenAI from 'openai';

const client = new OpenAI({
    apiKey: "YOUR_API_KEY",
    baseURL: "YOUR_ENDPOINT/openai/v1/"
});

const response = await client.responses.create({
    model: "YOUR_MODEL",
    input: "Explain quantum computing in simple terms",
    maxOutputTokens: 1000  // Higher for reasoning models
});
console.log(response.outputText);
```

**Or run the included examples:**
```bash
# Python - Responses API
cd src/python && python responses_example.py

# TypeScript - Responses API
cd src/typescript && npm start
```

## What This Template Includes

- **Core Infrastructure**: Azure OpenAI resource with GPT-5-mini deployment
- **Optimal Configuration**: Sweden Central region, GlobalStandard SKU, v1 API
- **Client Examples**: Python and TypeScript using the new Responses API
- **Validation Scripts**: PowerShell and Bash scripts for testing
- **Complete Documentation**: Setup guides and troubleshooting tips

## What You Get

✅ **GPT-5-mini (2025-08-07)** - Latest reasoning model, no registration required  
✅ **Sweden Central** deployment - Optimal European region   
✅ **New v1 API** support - Future-proof, no version management needed  
✅ **Automatic deployment** - Model ready to use immediately  
✅ **Multi-language examples** - Python and TypeScript/Node.js clients  
✅ **Unique resource naming** - No conflicts with existing resources  


## Template Structure

```
├── azure.yaml                 # azd configuration
├── infra/
│   ├── main.bicep             # Main deployment template
│   ├── main.parameters.json   # Deployment parameters (Sweden Central)
│   └── resources.bicep        # Azure OpenAI resource definition
├── src/
│   ├── python/
│   │   ├── responses_example.py  # Python Responses API example
│   │   └── requirements.txt      # Python dependencies
│   └── typescript/
│       ├── responses_example.ts  # TypeScript Responses API example
│       ├── package.json          # Node.js dependencies
│       └── tsconfig.json         # TypeScript configuration
├── CLIENT_README.md           # Detailed setup guide (Python & TypeScript)
├── validate.ps1              # PowerShell validation script
└── validate.sh               # Bash validation script
```

## Common Commands

```bash
# Redeploy with changes
azd up

# See what would be deployed
azd provision --preview  

# Debug deployment issues
azd up --debug

# Clean up everything  
azd down
```

## Alternative Regions

Want to deploy to East US 2 instead?
```bash
azd env set AZURE_LOCATION eastus2
azd up
```

## Model Customization

Want a different model? Edit `infra/resources.bicep`:

```bicep
// Current: GPT-5-mini (no registration required)
gptModelName: 'gpt-5-mini'
gptModelVersion: '2025-08-07'

// Alternatives (no registration required):
gptModelName: 'gpt-5-nano'      // Fastest
gptModelName: 'gpt-5-chat'      // Chat-optimized

// Full GPT-5 (requires registration):
gptModelName: 'gpt-5'           // Needs approval
```

## Troubleshooting

**"GPT-5-mini not available"** → Try `azd env set AZURE_LOCATION eastus2`

**"Quota exceeded"** → Check your subscription quota for Azure OpenAI

**"Permission denied"** → Ensure you have Cognitive Services Contributor role

**Need debug info?** → Run `azd up --debug` for detailed logs

## Why This Template?

✅ **Minimal setup** - 2 commands instead of 20+  
✅ **Latest model** - GPT-5-mini with reasoning capabilities  
✅ **Future-proof** - Uses new v1 API, no version management  
✅ **Production-ready** - GlobalStandard SKU, proper resource naming  
✅ **Complete examples** - Python client with error handling  
✅ **Easy cleanup** - Remove everything with `azd down`  

---

**Happy AI building with GPT-5-mini!** 🤖✨

*Powered by [Azure Developer CLI](https://aka.ms/azd) | Deploys GPT-5-mini (2025-08-07)*
