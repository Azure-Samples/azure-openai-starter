# Azure OpenAI GPT-5-mini Client Examples

Complete guide to using your deployed Azure OpenAI GPT-5-mini model with the **Responses API** in **Python** and **TypeScript/Node.js**.

## About the Responses API

The Responses API is the newer, cleaner interface designed specifically for GPT-5-mini and other reasoning models. It provides:

- **Simpler syntax**: Uses `input` parameter instead of `messages`
- **Better for reasoning**: Optimized for GPT-5-mini's internal reasoning capabilities
- **Cleaner output**: Direct access to response text via `output_text`
- **Token visibility**: Clear visibility into reasoning tokens vs output tokens

## Prerequisites

✅ Azure OpenAI GPT-5-mini deployed (run `azd up` first)  
✅ Python 3.8+ or Node.js 18+ installed

## Quick Setup

### 1. Get Your Deployment Information
```bash
# Get all deployment details
azd env get-values

# Note these key values:
# AZURE_ENV_NAME=XXXXXX
# AZURE_OPENAI_ENDPOINT=https://openai-XXXXXX.openai.azure.com/
# AZURE_OPENAI_NAME=openai-XXXXXX  
# AZURE_OPENAI_GPT_DEPLOYMENT_NAME=gpt-5-mini
```

### 2. Get Your API Key
```bash
# Use env values from step 1
az cognitiveservices account keys list --name AZURE_OPENAI_NAME --resource-group rg-AZURE_ENV_NAME
# Copy key1 or key2 from the output
```
**Don't have Azure CLI?** Install it: https://learn.microsoft.com/en-us/cli/azure/install-azure-cli

## Python Client

### 3a. Install Dependencies & Run (Python)
```bash
# Navigate to Python example
cd src/python

# Install dependencies
pip install -r requirements.txt

# Set your credentials (replace with your actual values)
$env:AZURE_OPENAI_ENDPOINT="https://openai-XXXXXX.openai.azure.com/"
$env:AZURE_OPENAI_API_KEY="your-api-key-here"

# Run the example
python responses_example.py
```

## TypeScript/Node.js Client

### 3b. Install Dependencies & Run (TypeScript/Node.js)  
```bash
# Navigate to TypeScript example
cd src/typescript

# Install dependencies
npm run install-deps
# or manually: npm install openai tsx typescript @types/node

# Set your credentials (replace with your actual values)
$env:AZURE_OPENAI_ENDPOINT="https://openai-XXXXXX.openai.azure.com/"
$env:AZURE_OPENAI_API_KEY="your-api-key-here"

# Run the example
npm start
# or: npx tsx responses_example.ts
```

### 6. Test the Connection
   ```bash
   python client_example.py
   ```

## Expected Output

## Example Output

When you run either example, you should see:

```
🔗 Connecting to: https://openai-xxx.openai.azure.com/openai/v1/
🤖 Testing GPT-5-mini model...
------------------------------------------------------------
✅ Success! GPT-5-mini response:
--------------------------------------------------
Hello! I'm GPT-5-mini running on Microsoft Azure in Sweden Central. 

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
✅ **Sweden Central** deployment - Optimal European region  
✅ **Standard OpenAI client** - Works with Python and TypeScript  
✅ **Minimal dependencies** - Just one package install  
✅ **No containers** - Direct API calls, no complex setup  

## Code Examples

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

## Troubleshooting

**❌ "Missing environment variables"**  
→ Run `azd env get-values` to get your endpoint  
→ Get API key: `az cognitiveservices account keys list --name YOUR_RESOURCE_NAME --resource-group rg-YOUR_ENV_NAME`

**❌ "Invalid request" or 401 errors**  
→ Verify your API key is correct  
→ Check endpoint URL includes trailing slash: `https://openai-xxx.openai.azure.com/`

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

🔧 **Customize the examples**: Edit `responses_example.py` or `responses_example.ts` for your use case  
📚 **Learn more**: [Azure OpenAI documentation](https://learn.microsoft.com/azure/ai-services/openai/)  
🚀 **Add more models**: Edit `infra/resources.bicep` to deploy additional models  
⚡ **Scale up**: Increase capacity or try GPT-5 full model  

---

**🎉 You're now running GPT-5-mini on Azure!** Experience the future of AI reasoning.
