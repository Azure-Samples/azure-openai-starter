# Client setup and validation

The starter has Responses samples for Python, TypeScript, Go, .NET and Java,
and Decisions samples for those languages plus Ruby. Every Decisions sample
classifies the same synthetic ticket with predicate, choice, and score questions.
See the [tabbed Decisions article](./docs/decisions.md) for the code and API contract.
On Windows, install PowerShell 7 (`pwsh`) to run the azd preprovision validation
hook. Standalone language samples do not require PowerShell.

## Configuration

Use your resource's root endpoint, for example
`https://YOUR-RESOURCE-NAME.openai.azure.com/`, not a deployment-specific URL.
The examples append `/openai/v1/`. No data-plane `api-version` is needed.
The .NET Responses examples instead use native OpenAI configuration:
`Clients:Responses:Options:Endpoint` is the **full v1 URL**. Their endpoint,
credentials and model are supplied by configuration, not translated from the
common starter variables. See the [.NET guide](./src/dotnet/README.md).

| Environment variable | Applies to | Default / requirement |
|---|---|---|
| `AZURE_OPENAI_ENDPOINT` | All | Required resource root endpoint |
| `AZURE_OPENAI_API_KEY` | All key-auth samples | Required for Responses key examples; optional for Decisions |
| `AZURE_OPENAI_GPT_DEPLOYMENT_NAME` | Responses | `gpt-6.1-sol` |
| `AZURE_OPENAI_REASONING_EFFORT` | Responses | `medium`; also `low`, `high`, `xhigh`, `max` |
| `AZURE_OPENAI_MAX_OUTPUT_TOKENS` | Responses | `16384`; integer 16 through 128000 |
| `AZURE_OPENAI_DEPLOYMENT` | Decisions | Your Azure deployment name; defaults to `gpt-6-luna` |

The Responses and Decisions deployment settings are separate. A Sol deployment cannot serve a Decisions
request. `model` always identifies your Azure deployment, not an arbitrary model
selected by the SDK. An omitted Decisions API key selects passwordless
authentication (Ruby obtains a token from the Azure CLI). For local development,
run `az login` and ensure the calling identity has the **Cognitive Services User**
role on the resource. Role assignments can take time to propagate.

If your development login has access to multiple tenants, set `AZURE_TENANT_ID`
to the tenant that owns the resource. The TypeScript keyless examples pass this
optional setting to `DefaultAzureCredential`, including its developer CLI
credential, rather than relying on your CLI's current tenant.
For Python with an azd login, explicitly set
`AZURE_TOKEN_CREDENTIALS=AzureDeveloperCliCredential` as well as `AZURE_TENANT_ID`.
The Python keyless examples then construct that official credential with the
resource tenant and keep the bearer-token provider's automatic refresh.
With no explicit credential selection, Python still uses `DefaultAzureCredential`.
The Go keyless examples also forward `AZURE_TENANT_ID` to their default
credential chain. Ruby normally uses `az`; set
`AZURE_TOKEN_CREDENTIALS=AzureDeveloperCliCredential` to use an existing `azd`
login instead. Ruby forwards `AZURE_TENANT_ID` to the selected CLI.

Every Decisions sample uses the configuration in [.env.example](./.env.example).
Export those values into your shell; loading a `.env` file is not automatic in
every runtime. For example, on Bash, copy the example to `.env`, replace the
placeholder endpoint, then run `set -a; source .env; set +a`. In PowerShell:

```powershell
$env:AZURE_OPENAI_ENDPOINT = "https://YOUR-RESOURCE-NAME.openai.azure.com/"
$env:AZURE_OPENAI_DEPLOYMENT = "YOUR-LUNA-DEPLOYMENT-NAME"
Remove-Item Env:AZURE_OPENAI_API_KEY -ErrorAction SilentlyContinue
```

When provisioning with azd, obtain these values with `azd env get-value
AZURE_OPENAI_ENDPOINT` and `azd env get-value AZURE_OPENAI_DEPLOYMENT`.
For the explicit API-key fallback, set `AZURE_OPENAI_API_KEY`; otherwise leave it unset.

Do not use real credentials against a local stub or an untrusted endpoint.
Decisions examples require an HTTPS resource root URL without user information,
query strings, fragments or deployment paths. Plain HTTP is allowed only for
loopback addresses with an explicitly supplied API key, for offline tests using
synthetic credentials. Passwordless authentication always requires HTTPS.

## Python

Requires Python 3.10 or newer. From `src/python`:

```bash
python -m venv .venv
# Activate the environment with your shell's normal activation command.
python -m pip install -r requirements.txt
python responses_example_entra.py
python responses_example.py
python decisions_example.py
```

The requirements pin OpenAI to the checked GA release 3.37.0. Keyless examples
use Azure Identity. A `.env` file is optional; real
environment variables take precedence in the Decisions example.

## TypeScript / JavaScript

Requires Node.js 24 or newer. From `src/typescript`:

```bash
npm ci
npm run build
npm start
npx tsx responses_example_entra.ts
npm run decisions
```

The examples are strict TypeScript. After compilation, run the same samples as
JavaScript, for example `node dist/decisions_example.js`. The committed npm lock records the dependencies resolved for this starter.

## Go

Requires Go 1.26 or newer. Each example is its own module:

```bash
cd src/go/responses_example
go run .
```

Or choose `src/go/responses_example_entra` or `src/go/decisions_example`.
Restore each module with `go mod download`. The Decisions instructions field
uses the SDK's string-or-content union rather than assigning a string directly.

## Java

Requires Java 21 and Maven. From `src/java`:

```bash
mvn --batch-mode compile
mvn exec:java -Dexec.mainClass=com.azure.openai.starter.ResponsesExample
mvn exec:java -Dexec.mainClass=com.azure.openai.starter.ResponsesExampleEntra
mvn exec:java -Dexec.mainClass=com.azure.openai.starter.DecisionsExample
```

Dependencies are declared in `pom.xml`; the examples need no sibling Java helper
classes. The Decisions SDK uses role-specific message and instruction union
types when advanced inputs are needed; the basic example uses text input.

## .NET / C#

Requires the .NET 10 SDK. File-based package directives restore the dependencies;
there is no application project file. From `src/dotnet`:

```bash
dotnet run responses_example.cs
dotnet run responses_example_entra.cs
dotnet run decisions_example.cs
```

Responses uses the OpenAI 2.14.0 SDK. Decisions intentionally uses `HttpClient`
against `/openai/v1/decisions`, with API-key or Microsoft Entra authentication,
because this package has no typed Decisions client. See the [.NET guide](./src/dotnet/README.md).
All .NET examples register their clients through the Generic Host and dependency
injection. OpenAI's `AddResponsesClient` binds Responses options and
credentials; Decisions uses a named `HttpClient` and configurable Azure
credential settings. The Responses examples require native client configuration;
the interim Decisions REST example still supports the starter environment variables.
Use `Clients__Responses__...` or `Clients__Decisions__...` settings, or the
optional [appsettings example](./src/dotnet/appsettings.example.json), to override
client options and credential sources without editing code. No language sample
uses an Azure OpenAI wrapper client/package; Azure identity/core components are
used only for authentication.

## Ruby

Requires Ruby 3.3 or newer and Bundler. From `src/ruby`:

```bash
bundle install
bundle exec ruby decisions_example.rb
```

The native OpenAI gem is pinned to 0.111.0. If `AZURE_OPENAI_API_KEY` is absent,
the sample runs `az account get-access-token` and uses the returned bearer token
for its single request. It never prints the token. This is a developer workflow,
not a managed-identity implementation for a long-running service.

## Region/model discovery

From the repository root:

```bash
python scripts/check-model-support.py --region eastus --model gpt-6-luna --sku DataZoneStandard
python scripts/check-model-support.py --region westus3 --model gpt-6-luna --sku DataZoneStandard --format json
```

These commands inspect Luna, not the separate Sol deployment. For a combined
deployment, verify Sol and its GlobalStandard SKU in the selected region too.

Use `--subscription NAME_OR_ID` to inspect a different subscription without
changing the active CLI subscription. `--all-regions` is opt-in.

For an offline inspection, save the JSON returned by
`az cognitiveservices model list --location REGION --output json` and run:

```bash
python scripts/check-model-support.py --region eastus --catalog-file catalog.json
```

Keep subscription-specific catalog snapshots out of source control. A catalog
entry is not proof of quota, available capacity, a deployed model, or support
for every Decisions feature. The script labels those limits explicitly.

## Real-photo scenarios

All six Decisions programs accept `--image PATH_OR_HTTPS_URL` after the usual
command. Local PNG, JPEG, WebP or GIF files become inline base64 data URLs.
HTTPS URLs are passed to Azure, which must be able to fetch the image without
your browser session. The sample never downloads an arbitrary URL itself.

| Language | Inline photo command from the language's sample directory |
|---|---|
| Python | `python decisions_example.py --image ../../images/decisions-photo.png` |
| TypeScript | `npm run decisions -- --image ../../images/decisions-photo.png` |
| Go (`src/go/decisions_example`) | `go run . --image ../../../images/decisions-photo.png` |
| Java | `mvn compile exec:java -Dexec.mainClass=com.azure.openai.starter.DecisionsExample -Dexec.args="--image ../../images/decisions-photo.png"` |
| .NET | `dotnet run decisions_example.cs -- --image ../../images/decisions-photo.png` |
| Ruby | `bundle exec ruby decisions_example.rb --image ../../images/decisions-photo.png` |

To demonstrate hosted input, replace the path with:

```text
https://raw.githubusercontent.com/scikit-image/scikit-image/v0.25.2/skimage/data/astronaut.png
```

This is a real public-domain NASA photograph, not a synthetic test pattern.
See [attribution](./images/decisions-photo.md). Choose a domain-relevant photo to
evaluate model quality; the sample photo need not depict damage.

## Tests

Restore the dependencies above before running the complete suite:

```bash
python -m unittest discover -s tests -v
```

This requires Python, Node/npm, Go, .NET, Java/Maven, Ruby/Bundler, and Azure CLI
with Bicep for the infrastructure check. Offline contract tests need no Azure
credentials and incur no model charges. They override inherited model/key settings.
The shell-validator tests use fake CLIs, and availability tests use catalog fixtures.

To test only the installed language toolchains, set `STARTER_TEST_LANGUAGES` to
a comma-separated selection of `Python`, `TypeScript`, `Go`, `.NET`, `Java`, and
`Ruby`. For example, `STARTER_TEST_LANGUAGES=Python,TypeScript python -m unittest
discover -s tests -v` on Bash. Unset the variable for the complete matrix.
Unknown language names are errors rather than silently skipped tests.

To run only discovery tests, no SDK or Azure CLI is needed:

```bash
python -m unittest discover -s tests -p test_model_support.py -v
```

Tests for live Responses requests are disabled unless
`AZURE_OPENAI_LIVE_TESTS=1`. Enabling Responses live tests requires real key and
Entra access and incurs charges. To run Decisions with Entra only, set
`AZURE_OPENAI_DECISIONS_LIVE_TESTS=1`, configure the common endpoint/deployment
settings, and run the suite. It removes the key fallback and exercises text,
inline photo and hosted photo inputs for every selected language. Do not enable
live flags in a public CI job with credentials.

A local contract test passing is not a live-region certification.

## Troubleshooting

| Symptom | Check |
|---|---|
| Decisions returns 404 / deployment not found | Use the Luna deployment name and a region in the current rollout; East US 2 is excluded in the documentation checked 2026-10-23 |
| 401 or 403 | Check endpoint, credential tenant and resource role assignment; do not print tokens or keys |
| A newer SDK type compiles but Azure rejects the request | SDK types and Azure feature rollout are separate; confirm the feature in Azure documentation |
| A package mirror cannot find the documented version | Compare the official registry and your approved package feed; do not silently downgrade the samples |
| Responses has no visible output | Check incomplete/error status and increase the output-token budget if reasoning consumed it |
| A region lists a model but provisioning fails | Check deployment SKU, subscription quota and current capacity; catalog visibility alone is insufficient |
