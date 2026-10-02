# Azure OpenAI Starter - Client Examples

Use the **GPT-6.1 Sol (`gpt-6.1-sol`, version `2026-09-29`)** deployment with the **Responses v1 API** in Python, TypeScript, Go, .NET or Java.

## Prerequisites

Deploy the [Bicep template](./infra/main.bicep) with `azd up`, then choose a language:

| Language | Requirement | Dependencies |
|---|---|---|
| Python | Python 3.10+ | [requirements.txt](./src/python/requirements.txt) |
| TypeScript | Node.js 24+ and npm | [package.json](./src/typescript/package.json) |
| Go | Go 1.25.1+ | [API-key module](./src/go/responses_example/go.mod), [Entra module](./src/go/responses_example_entra/go.mod) |
| .NET | .NET 10 SDK | [SDK configuration](./src/dotnet/global.json), package directives in each sample |
| Java | JDK 21+ and Maven | [pom.xml](./src/java/pom.xml) |

For the cross-language test suite, install **all five** toolchains. The Python interpreter running the suite must have the Python sample dependencies installed. Builds restore normal SDK/package dependencies but the test runner does not install missing toolchains.

## Configure Authentication

Set the endpoint and deployment name from the same azd environment that you provisioned.

### Bash / zsh

```bash
export AZURE_OPENAI_ENDPOINT="$(azd env get-value AZURE_OPENAI_ENDPOINT)"
export AZURE_OPENAI_GPT_DEPLOYMENT_NAME="$(azd env get-value AZURE_OPENAI_GPT_DEPLOYMENT_NAME)"
export AZURE_TENANT_ID="$(az account show --query tenantId --output tsv)"
```

### PowerShell

```powershell
$env:AZURE_OPENAI_ENDPOINT = azd env get-value AZURE_OPENAI_ENDPOINT
$env:AZURE_OPENAI_GPT_DEPLOYMENT_NAME = azd env get-value AZURE_OPENAI_GPT_DEPLOYMENT_NAME
$env:AZURE_TENANT_ID = az account show --query tenantId --output tsv
```

### Microsoft Entra ID (Recommended)

Run `az login` with the intended account and subscription. The examples use `DefaultAzureCredential` and the `https://cognitiveservices.azure.com/.default` scope. You do not need an API key.

The template grants the deploying user **Cognitive Services User** on the new account. Additional users, service principals or managed identities need their own data-plane role assignment. Allow time for RBAC changes to propagate.

For production, replace the development credential chain with the appropriate specific credential, such as `ManagedIdentityCredential`. See the credential guidance linked in each Entra source file.

### API Key (Development)

After setting the endpoint and deployment name, retrieve a single key without printing it:

```bash
export AZURE_OPENAI_API_KEY="$(az cognitiveservices account keys list \
  --name "$(azd env get-value AZURE_OPENAI_NAME)" \
  --resource-group "$(azd env get-value AZURE_RESOURCE_GROUP)" \
  --query key1 --output tsv)"
```

```powershell
$env:AZURE_OPENAI_API_KEY = az cognitiveservices account keys list `
  --name (azd env get-value AZURE_OPENAI_NAME) `
  --resource-group (azd env get-value AZURE_RESOURCE_GROUP) `
  --query key1 --output tsv
```

Never put keys in source control. Python and TypeScript also support a local `.env` file; explicitly set process environment variables take precedence. Go, .NET and Java read process environment variables directly.

## Install and Run

Start each set of commands from the repository root, using either the Entra or API-key command.

### Python

Use a virtual environment if desired, then install dependencies into the interpreter that will run the sample:

```bash
python -m pip install -r src/python/requirements.txt
cd src/python
python responses_example_entra.py
# Or:
python responses_example.py
```

Sources: [Entra](./src/python/responses_example_entra.py), [API key](./src/python/responses_example.py), [shared settings and response checks](./src/python/sample_options.py).

### TypeScript

```bash
cd src/typescript
npm ci
npm run build
npm run start:entra
# Or:
npm start
```

Sources: [Entra](./src/typescript/responses_example_entra.ts), [API key](./src/typescript/responses_example.ts), [shared settings and response checks](./src/typescript/sample_options.ts).

### Go

Each authentication example is an independent module:

```bash
cd src/go/responses_example_entra
go run .
```

Or, from the repository root:

```bash
cd src/go/responses_example
go run .
```

Sources: [Entra](./src/go/responses_example_entra/main.go), [API key](./src/go/responses_example/main.go).

### .NET

These are .NET 10 file-based applications; no project scaffolding is needed.

```bash
cd src/dotnet
dotnet run responses_example_entra.cs
# Or:
dotnet run responses_example.cs
```

Sources: [Entra](./src/dotnet/responses_example_entra.cs), [API key](./src/dotnet/responses_example.cs), [SDK prerequisites](./src/dotnet/README.md).

The SDK's extensible `ResponseReasoningEffortLevel` accepts the verified `xhigh` and `max` string values even when a named static constant is not available.

### Java

```bash
cd src/java
mvn compile exec:java "-Dexec.mainClass=com.azure.openai.starter.ResponsesExampleEntra"
# Or:
mvn compile exec:java "-Dexec.mainClass=com.azure.openai.starter.ResponsesExample"
```

Sources: [Entra](./src/java/src/main/java/com/azure/openai/starter/ResponsesExampleEntra.java), [API key](./src/java/src/main/java/com/azure/openai/starter/ResponsesExample.java), [shared settings and response checks](./src/java/src/main/java/com/azure/openai/starter/SampleOptions.java).

The samples use a deployment-name string rather than an SDK constant tied to a different model. Java extracts the output text rather than printing the SDK's internal response-object representation.

## Select a Reasoning Mode

All ten examples accept the same settings:

| Setting | Default | Valid values |
|---|---|---|
| `AZURE_OPENAI_GPT_DEPLOYMENT_NAME` | `gpt-6.1-sol` | Your nonempty Azure deployment name |
| `AZURE_OPENAI_REASONING_EFFORT` | `medium` | `low`, `medium`, `high`, `xhigh`, `max` |
| `AZURE_OPENAI_MAX_OUTPUT_TOKENS` | `16384` | Integer from `16` through `128000` |

For example:

```bash
export AZURE_OPENAI_REASONING_EFFORT=high
export AZURE_OPENAI_MAX_OUTPUT_TOKENS=32768
```

```powershell
$env:AZURE_OPENAI_REASONING_EFFORT = "high"
$env:AZURE_OPENAI_MAX_OUTPUT_TOKENS = "32768"
```

GPT-6.1 Sol does **not** support the `none` or `minimal` reasoning levels. Invalid settings fail locally before authentication or HTTP requests.

The token budget includes both internal reasoning and visible output. A larger limit is a ceiling, not a promise of completion or a fixed token charge. The model may need more reasoning tokens for harder prompts, particularly at `xhigh` or `max`.

The v1 client URL is always `<account-endpoint>/openai/v1/`; the examples normalize trailing slashes. No `api-version` query parameter is required.

## Request Formats and Output

Each program sends:

1. **Simple text:** explain quantum computing in at most 150 words.
2. **Conversation:** a system message specifying an Azure cloud architect, followed by a request for a scalable architecture in at most 150 words.

The .NET SDK serializes the first request as a single user message; the other SDKs use the string input form. Both are supported by the Responses API.

Output looks like the following; actual answers and token counts vary:

```text
Deployment: gpt-6.1-sol; reasoning effort: medium
Example 1: Simple text input
Response: <model-generated answer>
Status: completed
Reasoning tokens: <count>
Output tokens: <count, including reasoning>
```

The process exits unsuccessfully on an API error, an incomplete response, empty output text or missing usage. A token-limit cutoff must not be mistaken for a successful model test.

## Run the Test Matrix

From the repository root:

```bash
python -m unittest discover -s tests -v
```

The [test suite](./tests/test_samples.py) builds all five languages and runs the actual clients against a local mock Responses endpoint. It checks request paths, authentication headers, model/deployment names, all reasoning levels, token limits, both input formats and failure behavior. Invalid configuration is checked for both authentication entry points.

To verify Azure behavior, use a dedicated deployment, sign in with Azure CLI, and set the endpoint, deployment and API-key variables above:

```powershell
$env:AZURE_OPENAI_LIVE_TESTS = "1"
python -m unittest discover -s tests -k live_matrix -v
```

```bash
AZURE_OPENAI_LIVE_TESTS=1 python -m unittest discover -s tests -k live_matrix -v
```

This makes **100 billable Responses API calls** across all five languages, API-key and Entra authentication, five reasoning efforts and both request formats. The Entra runs explicitly use `AzureCliCredential` through the normal `DefaultAzureCredential` chain and receive no API key. Live tests are skipped unless explicitly enabled; a skip is not a successful live test.

The runner executes up to five sample processes concurrently. Increase `AZURE_OPENAI_CAPACITY` in the selected azd environment and reprovision if your quota permits and the test deployment needs more throughput. The suite does not deploy, modify or delete cloud resources.

To test the default client settings separately, use `-k live_default_configuration` instead of `-k live_matrix`.
This runs all ten clients sequentially with the default `medium` reasoning level and 16,384-token budget, making 20 additional billable calls. Running the entire suite with live tests enabled runs both live checks.

Coverage is limited to the starter's non-streaming Responses API examples. Streaming, tool calling, Chat Completions, Batch and production managed-identity hosting are not implemented or certified by this matrix.

## Troubleshooting

| Symptom | Check |
|---|---|
| Missing or invalid environment variable | Set it in the shell that starts the program. An explicitly empty value is invalid, not a request for a default. |
| Deployment/model not found | Confirm `AZURE_OPENAI_GPT_DEPLOYMENT_NAME` matches the deployment output, not an old GPT-5-mini deployment name. Changing client configuration does not deploy a model. |
| `Could not obtain the account information` immediately after creation | The data-plane account information may still be propagating, especially when reusing a recently deleted account name. Confirm provisioning succeeded and retry after propagation; use a new environment name for isolated tests. |
| 401 or 403 with Entra | Check `az account show`, tenant selection, data-plane RBAC and propagation time. An Azure management role alone does not grant model-inference access. |
| Credential chain cannot get a token | Run `az login`. Check the identity guidance linked in the relevant Entra example. |
| API-key authentication fails | Retrieve `key1` with `--query key1 --output tsv`; make sure local authentication is enabled on that account. |
| `Response did not complete` | Inspect the status/details. For a token-limit cutoff, raise `AZURE_OPENAI_MAX_OUTPUT_TOKENS` or reduce prompt complexity/reasoning effort. Other failures need their underlying cause resolved. |
| 429 / rate limit | Reduce concurrency, wait for the quota window, or increase deployment capacity within your subscription quota. |
| Model unavailable or quota exceeded during deployment | Select a region offered by the template with model access and free GlobalStandard quota. Consult the [model catalog](https://ai.azure.com/catalog/models/gpt-6.1-sol). |
| Network access denied | Use a permitted network or the resource's private connectivity path. Do not disable network controls to bypass the error. |

For additional features, see the [Azure Responses API guide](https://learn.microsoft.com/azure/ai-foundry/openai/how-to/responses) and [GPT-6.1 Sol model reference](https://developers.openai.com/api/docs/models/gpt-6.1-sol).
