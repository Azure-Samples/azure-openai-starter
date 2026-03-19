# Azure OpenAI Starter - Client Examples

Complete guide to using your deployed Azure OpenAI **GPT-5-mini** model with the **Responses API** in **Python**, **TypeScript/Node.js**, **Go**, **.NET** and **Java**.

## About the Responses API

The Responses API is the newer, cleaner interface designed specifically for GPT-5-mini and other reasoning models. It provides:

- **Simpler syntax**: Uses `input` parameter instead of `messages`
- **Better for reasoning**: Optimized for GPT-5-mini's internal reasoning capabilities
- **Cleaner output**: Direct access to response text via `output_text`
- **Token visibility**: Clear visibility into reasoning tokens vs output tokens

## Prerequisites

✅ Azure OpenAI GPT-5-mini deployed (run `azd up` first)  
✅ Python 3.8+ or Node.js 18+ or Go 1.21+ or .NET 10+ or Java 21+ installed  
✅ Azure CLI installed and logged in (`az login`)

## 🔐 Recommended: Keyless Authentication (Production Ready)

**This is the secure, production-ready approach. No API keys to manage!**

<details>
<summary><strong>Click to expand Keyless setup and code examples</strong></summary>

### Setup Steps

```bash
# 1. Get your Azure OpenAI endpoint
azd env get-values | Select-String 'AZURE_OPENAI_ENDPOINT'

# 2. Set environment variable
$env:AZURE_OPENAI_ENDPOINT="https://openai-XXXXXX.openai.azure.com/"

# Note: The "Cognitive Services User" role is automatically assigned to your
# account during "azd up", so no manual role assignment is needed.
```

### Python Setup & Code

```bash
# Install dependencies
cd src/python
pip install -r requirements.txt

# Run with EntraID
python responses_example_entra.py
```

**Python Code Example:**
```python
from openai import OpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
import os

# Use DefaultAzureCredential for EntraID authentication
token_provider = get_bearer_token_provider(
    DefaultAzureCredential(),
    "https://cognitiveservices.azure.com/.default"
)

# Initialize OpenAI client with Azure endpoint and EntraID
client = OpenAI(
    base_url=f"{os.getenv('AZURE_OPENAI_ENDPOINT')}openai/v1/",
    api_key=token_provider
)

# Use the Responses API
response = client.responses.create(
    model="gpt-5-mini",
    input="Explain quantum computing in simple terms",
    max_output_tokens=1000
)
print(response.output_text)
```

### TypeScript Setup & Code

```bash
# Install dependencies
cd src/typescript
npm install

# Run with EntraID
tsx responses_example_entra.ts
```

**TypeScript Code Example:**
```typescript
import OpenAI from "openai";
import { DefaultAzureCredential, getBearerTokenProvider } from "@azure/identity";

// Use Azure Identity for authentication
const credential = new DefaultAzureCredential();
const scope = "https://cognitiveservices.azure.com/.default";
const tokenProvider = getBearerTokenProvider(credential, scope);

// Initialize OpenAI client with Azure endpoint and EntraID
const client = new OpenAI({
    baseURL: `${process.env.AZURE_OPENAI_ENDPOINT}openai/v1/`,
    apiKey:  await tokenProvider()
});

// Use the Responses API
const response = await client.responses.create({
    model: "gpt-5-mini",
    input: "Explain quantum computing in simple terms",
    max_output_tokens: 1000
});
console.log(response.output_text);
```

### Go Setup & Code

```bash
# Run with EntraID
cd src/go/responses_example_entra
go run .
```

### .NET Setup & Code

```bash
# Run with EntraID (requires .NET 10+)
cd src/dotnet
dotnet run responses_example_entra.cs
```

### Java Setup & Code

```bash
# Run with EntraID (requires Java 21+ and Maven)
cd src/java
mvn clean compile exec:java -Dexec.mainClass="com.azure.openai.starter.ResponsesExampleEntra"
```

**Why EntraID?**
- ✅ No API keys to manage or rotate
- ✅ Uses your Azure CLI login or Managed Identity
- ✅ Better security with Azure RBAC
- ✅ Automatic token refresh
- ✅ Works with service principals and managed identities
- ✅ Enterprise-grade security compliance

</details>

---

## Alternative: API Key Authentication (Quick Start)

**For quick testing and development only. Not recommended for production.**

<details>
<summary><strong>Click to expand API key setup and code examples</strong></summary>

### Setup Steps

```bash
# 1. Get all deployment details
azd env get-values

# 2. Get your API key (use values from step 1)
az cognitiveservices account keys list --name AZURE_OPENAI_NAME --resource-group rg-AZURE_ENV_NAME

# 3. Set environment variables
$env:AZURE_OPENAI_ENDPOINT="https://openai-XXXXXX.openai.azure.com/"
$env:AZURE_OPENAI_API_KEY="your-api-key-here"
```

**Don't have Azure CLI?** Install it: https://learn.microsoft.com/cli/azure/install-azure-cli

### Python Setup & Code

```bash
# Install dependencies
cd src/python
pip install -r requirements.txt

# Run with API key
python responses_example.py
```

**Python Code Example:**
```python
from openai import OpenAI
import os

client = OpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    base_url=f"{os.getenv('AZURE_OPENAI_ENDPOINT')}openai/v1/"
)

response = client.responses.create(
    model="gpt-5-mini",
    input="Explain quantum computing in simple terms",
    max_output_tokens=1000
)
print(response.output_text)
```

### TypeScript Setup & Code

```bash
# Install dependencies
cd src/typescript
npm install

# Run with API key
npm start
```

**TypeScript Code Example:**
```typescript
import OpenAI from 'openai';

const client = new OpenAI({
    apiKey: process.env.AZURE_OPENAI_API_KEY,
    baseURL: `${process.env.AZURE_OPENAI_ENDPOINT}openai/v1/`
});

const response = await client.responses.create({
    model: "gpt-5-mini",
    input: "Explain quantum computing in simple terms",
    max_output_tokens: 1000
});
console.log(response.output_text);
```

### Go Setup & Code

```bash
# Run with API key
cd src/go/responses_example
go run .
```

### .NET Setup & Code

```bash
# Run with API key (requires .NET 10+)
cd src/dotnet
dotnet run responses_example.cs
```

### Java Setup & Code

```bash
# Run with API key (requires Java 21+ and Maven)
cd src/java
mvn clean compile exec:java -Dexec.mainClass="com.azure.openai.starter.ResponsesExample"
```

</details>

---

## Example Output

When you run either example, you should see:

```
🔗 Connecting to: https://openai-xxx.openai.azure.com/openai/v1/
🤖 Testing GPT-5-mini model...
------------------------------------------------------------
✅ Success! GPT-5-mini response:
--------------------------------------------------
Hello! I'm GPT-5-mini running on Microsoft Azure. 

Something interesting about Sweden: Sweden has a unique concept called "allemansrätten" (the Right to Roam), which gives everyone the legal right to access and enjoy nature freely - you can walk, camp, pick berries, and mushrooms almost anywhere in the country, as long as you don't disturb wildlife or private property. This reflects Sweden's deep cultural connection to nature and trust-based society.
--------------------------------------------------
📊 Model: gpt-5-mini-2025-08-07
📊 Tokens used: 284
📊 Input tokens: 45
📊 Output tokens: 239
📊 Reasoning tokens: 156

🧠 Testing with a more complex prompt that requires visible output...
------------------------------------------------------------
✅ Complex response test:
------------------------------
Sweden is distinctive for its blend of social-democratic institutions and strong culture of innovation that has produced globally influential companies. Its unique combination of vast, accessible nature and progressive environmental policies fosters sustainability and a high quality of life.
------------------------------
📊 Complex test tokens: 396
📊 Complex reasoning tokens: 256

🎉 GPT-5-mini is working perfectly!
```

## Key Features

✅ **GPT-5-mini (2025-08-07)** - Latest reasoning model from OpenAI  
✅ **New v1 API** - No api-version needed, future-proof  
✅ **Flexible region** deployment - Choose your optimal region  
✅ **Standard OpenAI client** - Works with Python, TypeScript, Go, .NET and Java  
✅ **Minimal dependencies** - Just one package install  
✅ **No containers** - Direct API calls, no complex setup  

## Code Examples

<details>
<summary><strong>Click to expand additional code examples</strong></summary>

### 🔐 EntraID Authentication (Recommended)

**Python - EntraID with Responses API:**
```python
from openai import OpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
import os

# Use DefaultAzureCredential for EntraID authentication
token_provider = get_bearer_token_provider(
    DefaultAzureCredential(),
    "https://cognitiveservices.azure.com/.default"
)

# Initialize OpenAI client with Azure endpoint and EntraID authentication
client = OpenAI(
    base_url=f"{os.getenv('AZURE_OPENAI_ENDPOINT')}openai/v1/",
    api_key=token_provider
)

# Use the Responses API normally
response = client.responses.create(
    model="gpt-5-mini",
    input="Explain quantum computing in simple terms",
    max_output_tokens=1000
)
print(response.output_text)
```

**TypeScript - EntraID with Responses API:**
```typescript
import OpenAI from "openai";
import { DefaultAzureCredential, getBearerTokenProvider } from "@azure/identity";

// Use Azure Identity for authentication
const credential = new DefaultAzureCredential();
const scope = "https://cognitiveservices.azure.com/.default";
const tokenProvider = getBearerTokenProvider(credential, scope);

// Use standard OpenAI client with Azure endpoint and token provider
const client = new OpenAI({
    baseURL: `${process.env.AZURE_OPENAI_ENDPOINT}openai/v1/`,
    apiKey: tokenProvider as any
});

// Use the Responses API normally
const response = await client.responses.create({
    model: "gpt-5-mini",
    input: "Explain quantum computing in simple terms",
    max_output_tokens: 1000
});
console.log(response.output_text);
```

---

### API Key Authentication (Quick Start)

<details>
<summary>Click to expand API key code examples</summary>

### Python - Basic Responses API
```python
from openai import OpenAI
import os

client = OpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    base_url=f"{os.getenv('AZURE_OPENAI_ENDPOINT')}/openai/v1/"
)

response = client.responses.create(
    model="gpt-5-mini",
    input="Explain quantum computing in simple terms",
    max_output_tokens=1000
)
print(response.output_text)
```

### TypeScript - Basic Responses API
```typescript
import OpenAI from 'openai';

const client = new OpenAI({
    apiKey: process.env.AZURE_OPENAI_API_KEY,
    baseURL: `${process.env.AZURE_OPENAI_ENDPOINT}/openai/v1/`
});

const response = await client.responses.create({
    model: "gpt-5-mini",
    input: "Explain quantum computing in simple terms",
    maxOutputTokens: 1000
});
console.log(response.outputText);
```

### Python - Conversation Format
```python
# The Responses API also supports conversation format
response = client.responses.create(
    model="gpt-5-mini",
    input=[
        {"role": "system", "content": "You are an Azure cloud architect."},
        {"role": "user", "content": "Design a scalable web application architecture."}
    ],
    max_output_tokens=1000
)
print(response.output_text)
```

### TypeScript - Conversation Format
```typescript
const response = await client.responses.create({
    model: "gpt-5-mini",
    input: [
        { role: "system", content: "You are an Azure cloud architect." },
        { role: "user", content: "Design a scalable web application architecture." }
    ],
    maxOutputTokens: 1000
});
console.log(response.outputText);
```

### Python - Accessing Reasoning Tokens
```python
# GPT-5-mini uses internal reasoning - you can see how many reasoning tokens were used
response = client.responses.create(
    model="gpt-5-mini",
    input="Explain quantum computing in simple terms",
    max_output_tokens=1000
)
print(response.output_text)
print(f"Reasoning tokens: {response.usage.output_tokens_details.reasoning_tokens}")
```

### TypeScript - Accessing Reasoning Tokens
```typescript
// GPT-5-mini uses internal reasoning - you can see how many reasoning tokens were used
const response = await client.responses.create({
    model: "gpt-5-mini",
    input: "Explain quantum computing in simple terms",
    maxOutputTokens: 1000
});
console.log(response.outputText);
console.log(`Reasoning tokens: ${response.usage?.outputTokensDetails?.reasoningTokens}`);
```

### Python - Accessing Reasoning Tokens
```python
# GPT-5-mini uses internal reasoning - you can see the token usage
response = client.responses.create(
    model="gpt-5-mini",
    input="Solve this step by step: 15 + 27 - 8 = ?",
    max_output_tokens=500
)

# Access reasoning and output tokens
print(f"Response: {response.output_text}")
print(f"Reasoning tokens: {response.usage.reasoning_tokens}")
print(f"Output tokens: {response.usage.output_tokens}")
print(f"Total tokens: {response.usage.total_tokens}")
```

### TypeScript - Accessing Reasoning Tokens
```typescript
// GPT-5-mini uses internal reasoning - you can see the token usage
const response = await client.responses.create({
    model: "gpt-5-mini",
    input: "Solve this step by step: 15 + 27 - 8 = ?",
    max_output_tokens: 500
});

// Access reasoning and output tokens
console.log(`Response: ${response.output_text}`);
console.log(`Reasoning tokens: ${response.usage?.reasoning_tokens}`);
console.log(`Output tokens: ${response.usage?.output_tokens}`);
console.log(`Total tokens: ${response.usage?.total_tokens}`);
```

### Python - Multi-Turn Conversation
```python
# Build a conversation with Responses API
messages = [
    {"role": "system", "content": "You are a helpful coding assistant."},
    {"role": "user", "content": "Write a Python function to calculate factorial"}
]

response = client.responses.create(
    model="gpt-5-mini",
    input=messages,
    max_output_tokens=400
)

# Add assistant's response to conversation
messages.append({"role": "assistant", "content": response.output_text})

# Continue the conversation
messages.append({"role": "user", "content": "Now optimize it with memoization"})

response2 = client.responses.create(
    model="gpt-5-mini",
    input=messages,
    max_output_tokens=400
)
print(response2.output_text)
```

### TypeScript - Multi-Turn Conversation
```typescript
// Build a conversation with Responses API
const messages: Array<{role: string, content: string}> = [
    { role: "system", content: "You are a helpful coding assistant." },
    { role: "user", content: "Write a TypeScript function to calculate factorial" }
];

const response = await client.responses.create({
    model: "gpt-5-mini",
    input: messages,
    max_output_tokens: 400
});

// Add assistant's response to conversation
messages.push({ role: "assistant", content: response.output_text ?? "" });

// Continue the conversation
messages.push({ role: "user", content: "Now optimize it with memoization" });

const response2 = await client.responses.create({
    model: "gpt-5-mini",
    input: messages,
    max_output_tokens: 400
});
console.log(response2.output_text);
```

</details>

---

## Troubleshooting

### EntraID Authentication Issues

**❌ "401 PermissionDenied" with EntraID**  
→ Assign the "Cognitive Services OpenAI User" role (see setup instructions above)  
→ Verify you're logged in: `az account show`  
→ Try logging in again: `az login`

**❌ "DefaultAzureCredential failed to retrieve a token"**  
→ Ensure Azure CLI is installed and you're logged in: `az login`  
→ Check you have access to the subscription: `az account list`

### API Key Authentication Issues

**❌ "Missing environment variables"**  
→ Run `azd env get-values` to get your endpoint  
→ Get API key: `az cognitiveservices account keys list --name YOUR_RESOURCE_NAME --resource-group rg-YOUR_ENV_NAME`

**❌ "Invalid request" or 401 errors with API key**  
→ Verify your API key is correct  
→ Check endpoint URL includes trailing slash: `https://openai-xxx.openai.azure.com/`

### General Issues

**❌ "Model not found"**  
→ Ensure deployment completed: `azd env get-values` should show `AZURE_OPENAI_GPT_DEPLOYMENT_NAME=gpt-5-mini`  
→ Check deployment status in Azure portal

**❌ "Rate limit exceeded"**  
→ Default capacity is 10K tokens per minute  
→ Wait and retry, or increase capacity in Azure portal

## Why the New v1 API?

This template uses Azure OpenAI's **new v1 API endpoint** which:

✅ Uses standard `OpenAI()` client instead of `AzureOpenAI()`  
✅ No `api_version` parameter needed - future-proof  
✅ Same client code works for both OpenAI and Azure OpenAI  
✅ Automatic compatibility with latest OpenAI features  
✅ Simplified authentication and configuration  

## About the Responses API

This template uses the **Responses API**, which provides a cleaner interface optimized for GPT-5-mini reasoning models:

**Key Benefits:**
- ✅ Simpler interface - direct `input` parameter instead of message formatting
- ✅ Direct access to reasoning tokens via `response.usage.output_tokens_details.reasoning_tokens`
- ✅ Supports both simple text and conversation format
- ✅ Designed for reasoning models like GPT-5-mini
- ✅ Cleaner response structure with `output_text` property

**Important:** Use `max_output_tokens=1000` (not 50-200) to account for GPT-5-mini's internal reasoning process. The model uses reasoning tokens internally before generating the final output.

## Next Steps

🔧 **Customize the examples**: Edit the example files in `src/` for your use case  
📚 **Learn more**: [Azure OpenAI documentation](https://learn.microsoft.com/azure/ai-services/openai/)  
🚀 **Add more models**: Edit `infra/resources.bicep` to deploy additional models  
⚡ **Scale up**: Increase capacity or try GPT-5 full model  

---

**🎉 You're now running GPT-5-mini on Azure!** Experience the future of AI reasoning.
