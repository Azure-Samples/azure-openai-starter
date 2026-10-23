<!--
---
page_type: sample
languages:
- python
- typescript
- go
- csharp
- java
- ruby
products:
- azure-openai
- azure
urlFragment: azure-openai-starter
name: The Azure OpenAI Starter Kit
description: Deploy GPT-6.1 Sol with azd. Optionally add GPT-6 Luna for Decisions, with six-language samples and regional model discovery.
---
-->
# The Azure OpenAI Starter Kit

Deploy Azure OpenAI with one command. Use **GPT-6.1 Sol** with the Responses API,
or optionally add **GPT-6 Luna** for fast classification, routing, and scoring
with the Decisions API.

## Architecture

![The Azure OpenAI Starter Kit architecture](./images/aoaistarterimage.png)

[SVG source](./images/architecture.svg). Bicep provisions an Azure OpenAI account,
the Responses model deployment, and the deploying user's Cognitive Services User
role assignment. The Decisions deployment is **opt-in**, not an additional
resource provisioned by default. All samples support API keys or passwordless
access; Ruby uses an Azure CLI token for its passwordless example.

## Prerequisites

- [Azure subscription](https://azure.microsoft.com/pricing/purchase-options/azure-account)
- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli), signed in with `az login`
- [Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd),
  signed in with `azd auth login`
- A supported region and sufficient quota for the model and deployment SKU
- The runtime for your sample: Python 3.10+, Node.js 24+, Go 1.26+,
  .NET 10, Java 21 with Maven, or Ruby 3.3+ with Bundler

See [client setup](./CLIENT_README.md) for dependency versions and commands.

## Quick start: Responses

```bash
az login
azd auth login
azd up
```

This deploys GPT-6.1 Sol (`2026-09-29`) on `GlobalStandard`. The default capacity
is 10 thousand tokens per minute, subject to subscription quota. Configure it
with `azd env set AZURE_OPENAI_CAPACITY 10`.

Set the resource endpoint, then run a passwordless example:

```bash
export AZURE_OPENAI_ENDPOINT="$(azd env get-value AZURE_OPENAI_ENDPOINT)"
export AZURE_OPENAI_GPT_DEPLOYMENT_NAME="$(azd env get-value AZURE_OPENAI_GPT_DEPLOYMENT_NAME)"
cd src/python
python -m pip install -r requirements.txt
python responses_example_entra.py
```

PowerShell:

```powershell
$env:AZURE_OPENAI_ENDPOINT = azd env get-value AZURE_OPENAI_ENDPOINT
$env:AZURE_OPENAI_GPT_DEPLOYMENT_NAME = azd env get-value AZURE_OPENAI_GPT_DEPLOYMENT_NAME
Set-Location src\python
python -m pip install -r requirements.txt
python responses_example_entra.py
```

Responses samples cover simple text, conversations, explicit error handling,
and reasoning-token usage. Optional settings:

| Environment variable | Default | Meaning |
|---|---|---|
| `AZURE_OPENAI_GPT_DEPLOYMENT_NAME` | `gpt-6.1-sol` | Your Responses deployment name |
| `AZURE_OPENAI_REASONING_EFFORT` | `medium` | `low`, `medium`, `high`, `xhigh`, or `max` |
| `AZURE_OPENAI_MAX_OUTPUT_TOKENS` | `16384` | Integer from 16 to 128000, including reasoning tokens |

These reasoning settings are **not** sent to the Decisions API.

## Decisions: classify, route, and score

The [Azure OpenAI Decisions API](https://learn.microsoft.com/azure/foundry/openai/how-to/decisions)
uses a **GPT-6 Luna deployment**, not GPT-6.1 Sol. Its typed answers include
predicate probabilities, predefined choices, scores, and per-question refusals.
The samples send the same synthetic support ticket and three questions in every
language so that outputs and authentication approaches are easy to compare.

### 1. Check region and model availability

```bash
python scripts/check-model-support.py --region swedencentral --region eastus2
python scripts/check-model-support.py --region swedencentral --format json
```

The script uses read-only `az cognitiveservices model list` calls. It reports
model versions and deployment SKUs when Azure returns them, and distinguishes
catalog visibility from actual endpoint support. It does **not** deploy resources,
read keys, consume model tokens, or prove quota/capacity.

The Decisions documentation checked on **2026-10-23** excludes **East US 2** from
the rollout, even if GPT-6 Luna appears in that region's model catalog. Recheck the
[current rollout documentation](https://learn.microsoft.com/azure/foundry/openai/how-to/decisions)
and [regional model table](https://learn.microsoft.com/azure/foundry/foundry-models/concepts/models-sold-directly-by-azure-region-availability).
Use `--all-regions` only when you intend to query every subscription-visible
location; this can take several minutes.

### 2. Optionally provision a Decisions deployment

Choose a region supported by **both** deployments before provisioning:

```bash
azd env set AZURE_LOCATION swedencentral
azd env set AZURE_OPENAI_DEPLOY_DECISIONS true
azd env set AZURE_OPENAI_DECISIONS_MODEL_VERSION 2026-09-22
azd env set AZURE_OPENAI_DECISIONS_CAPACITY 10
azd up
```

GPT-6 Luna (`2026-09-22`) is listed in the
[public Azure model catalog](https://learn.microsoft.com/azure/foundry/foundry-models/concepts/models-sold-directly-by-azure).
The optional deployment uses `GlobalStandard` and has separate quota and billing.
If you already have a Luna deployment, skip this step and set its name directly.
Disabling the option in a later incremental deployment does not necessarily
delete an existing Azure deployment; manage its lifecycle explicitly.

### 3. Run a sample

```bash
export AZURE_OPENAI_ENDPOINT="$(azd env get-value AZURE_OPENAI_ENDPOINT)"
export AZURE_OPENAI_DECISIONS_DEPLOYMENT_NAME="$(azd env get-value AZURE_OPENAI_DECISIONS_DEPLOYMENT_NAME)"
python src/python/decisions_example.py
```

PowerShell:

```powershell
$env:AZURE_OPENAI_ENDPOINT = azd env get-value AZURE_OPENAI_ENDPOINT
$env:AZURE_OPENAI_DECISIONS_DEPLOYMENT_NAME = azd env get-value AZURE_OPENAI_DECISIONS_DEPLOYMENT_NAME
python src\python\decisions_example.py
```

Leave `AZURE_OPENAI_API_KEY` unset for passwordless access. Set it to use an API
key instead. Do not commit credentials or copy actual keys into documentation.

| Language | Decisions implementation | Run from its sample directory |
|---|---|---|
| [Python](./src/python/decisions_example.py) | Native OpenAI SDK | `python decisions_example.py` |
| [TypeScript / JavaScript](./src/typescript/decisions_example.ts) | Native OpenAI SDK | `npm run decisions` |
| [Go](./src/go/decisions_example/main.go) | Native OpenAI SDK | `go run .` |
| [Java](./src/java/src/main/java/com/azure/openai/starter/DecisionsExample.java) | Native OpenAI SDK | `mvn compile exec:java -Dexec.mainClass=com.azure.openai.starter.DecisionsExample` |
| [Ruby](./src/ruby/decisions_example.rb) | Native OpenAI SDK | `bundle exec ruby decisions_example.rb` |
| [.NET / C#](./src/dotnet/decisions_example.cs) | `HttpClient` REST fallback | `dotnet run decisions_example.cs` |

**Documentation authors:** [docs/decisions.md](./docs/decisions.md) provides
Microsoft Learn-style language tabs that include these runnable sources directly.
It separates current Azure-documented behavior from OpenAI SDK capabilities.
The .NET fallback is intentional: OpenAI 2.14.0 has no native typed Decisions client.

## SDK baseline

These published OpenAI versions include the expanded Decisions GA types, except
.NET, which uses REST for Decisions. Versions were checked on **2026-10-23**.

| SDK | Version used as the sample baseline |
|---|---|
| [Python](https://pypi.org/project/openai/3.37.0/) | `>=3.37.0,<4` |
| [JavaScript / TypeScript](https://www.npmjs.com/package/openai/v/7.43.0) | `^7.43.0` |
| [Go](https://pkg.go.dev/github.com/openai/openai-go/v3@v3.86.0) | `v3.86.0` |
| [Java](https://central.sonatype.com/artifact/com.openai/openai-java/4.91.0) | `4.91.0` |
| [Ruby](https://rubygems.org/gems/openai/versions/0.111.0) | `0.111.0` |
| [.NET](https://www.nuget.org/packages/OpenAI/2.14.0) | `2.14.0` for Responses; REST for Decisions |

The non-.NET release notes call out type changes to message inputs and structured
instruction parts. Updating an existing application can require source changes.
Model availability, service-feature availability, and SDK type availability are
different checks; installing a newer SDK does not enable an Azure feature.

## Validation

```bash
# Infrastructure compilation and required-file checks; no resources are deployed.
bash validate.sh

# Or PowerShell:
pwsh -File validate.ps1

# Model-catalog unit tests only; no SDKs or cloud access required.
python -m unittest discover -s tests -p test_model_support.py -v

# After restoring all six languages' dependencies:
python -m unittest discover -s tests -v
```

The contract suite runs real SDK clients and the .NET REST client against a local
HTTP server, checks payloads and deployment overrides, and exercises refusals,
HTTP failures, and malformed responses. It does not prove Azure rollout or quota.
Live Responses tests are separately opt-in with `AZURE_OPENAI_LIVE_TESTS=1` and
require a real deployment; they can incur charges.

## Cleanup

```bash
azd down
```

Review the resources selected for deletion. This removes this environment's
resource group, including its model deployments; it does not remove unrelated
deployments in a separately managed resource.
