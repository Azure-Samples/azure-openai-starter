# .NET configuration and dependency injection samples

Requires the .NET 10 SDK (`dotnet --list-sdks`). These are file-based applications:
their package directives restore dependencies; no project file is required.

All three applications use the .NET Generic Host configuration system and
dependency injection. Configuration can come from an optional `appsettings.json`,
environment variables, or command-line configuration in the Responses examples.
Clients and credential settings are registered once and resolved from DI, rather
than constructing an SDK client with a fixed credential in the sample.

## Quick start with the existing starter variables

From this directory:

```powershell
$env:AZURE_OPENAI_ENDPOINT = "https://YOUR-RESOURCE.openai.azure.com/"
$env:AZURE_OPENAI_GPT_DEPLOYMENT_NAME = "YOUR-SOL-DEPLOYMENT"
$env:AZURE_OPENAI_DEPLOYMENT = "YOUR-LUNA-DEPLOYMENT"
dotnet run responses_example_entra.cs
dotnet run decisions_example.cs
```

The deployment settings refer to **Azure deployment names**, not arbitrary model
selectors. The Responses deployment hosts GPT-6.1 Sol; Decisions requires GPT-6 Luna.
API-key Responses remains available with `responses_example.cs` and
`AZURE_OPENAI_API_KEY`. In Decisions, an explicitly set key is the fallback to
the default Entra flow. No arguments preserves the three-question billing example.

The Entra configuration defaults to a chain of environment, workload identity,
managed identity, Azure CLI, and Azure Developer CLI credentials. For a specific
developer credential, set `AZURE_TOKEN_CREDENTIALS`, for example
`AzureDeveloperCliCredential`. `dev` selects the CLI credentials; `prod` selects
environment/workload/managed identity. `AZURE_TENANT_ID` is forwarded to the
credential settings for multi-tenant developer logins.

## Configure the clients and credentials

Copy [appsettings.example.json](./appsettings.example.json) to `appsettings.json`,
replace the placeholder endpoints/deployment names, then run the same commands.
The example selects an existing Azure Developer CLI login; run `azd auth login`
first. Keep your real configuration and secrets out of source control.

| Configuration section | Purpose |
|---|---|
| `Clients:Responses:Options` | `ResponsesClientOptions`, including endpoint, network timeout, organization/project IDs and supported pipeline settings |
| `Clients:Responses:Credential` | Credential source and its options, such as `TenantId`, `ClientId` and chained `Sources` |
| `Clients:Responses:Model` | Sol deployment name |
| `Clients:Responses:ReasoningEffort` / `MaxOutputTokens` | Existing Responses request settings |
| `Clients:Decisions:Options` | Interim HTTP transport endpoint and network timeout |
| `Clients:Decisions:Credential` | API key or Azure token credential configuration |
| `Clients:Decisions:Model` | Luna deployment name |

The SDK's released configuration/DI interface registers the Responses singleton:

```csharp
builder.AddAzureCredentialResolver();
builder.AddAzureClient<ResponsesClient, ResponsesClientSettings>("Clients:Responses");
using var host = builder.Build();
var client = host.Services.GetRequiredService<ResponsesClient>();
```

The Azure resolver constructs the configured credential. For example, use
`AzureDeveloperCliCredential`, `AzureCliCredential`, `ManagedIdentityCredential`
or `ChainedTokenCredential` with a `Sources` array. Set the Azure OpenAI
`Credential:Scope` to `https://cognitiveservices.azure.com/.default`.

Use standard double-underscore environment keys to override JSON:

```powershell
$env:Clients__Responses__Credential__CredentialSource = "ManagedIdentityCredential"
$env:Clients__Responses__Credential__ClientId = "YOUR-USER-ASSIGNED-IDENTITY-CLIENT-ID"
$env:Clients__Responses__Options__NetworkTimeout = "00:02:00"

# Or select an API key supplied securely, not saved in JSON:
$env:Clients__Responses__Credential__CredentialSource = "ApiKeyCredential"
$env:Clients__Responses__Credential__Key = $env:AZURE_OPENAI_API_KEY
```

The same credential keys work under `Clients__Decisions__Credential__...`.
Configuration sections take precedence over the starter's `AZURE_OPENAI_*`
variables; the latter are used only to populate missing settings. A configured
`Options:Endpoint` is the **full v1 base URL**, unlike the legacy resource-root
`AZURE_OPENAI_ENDPOINT`. Changing credentials does not require editing the sample.
Application code can also register custom credential resolvers and configure
the DI client's settings/options.

These samples pin OpenAI **2.14.0**, Azure.Core **1.62.0**, and Microsoft.Extensions
Hosting/HTTP **10.0.10**. Azure.Core 1.62.0 supplies the Azure identity
configuration resolver and credential types; a separate older Azure.Identity
reference is not needed. The configuration APIs are shipped but marked
experimental (`SCME0002`); the samples explicitly suppress that diagnostic.
File-based native-AOT publishing is disabled for reflection-based configuration.

References:
- [System.ClientModel configuration and DI](https://github.com/Azure/azure-sdk-for-net/blob/System.ClientModel_1.15.0/sdk/core/System.ClientModel/src/docs/ConfigurationAndDependencyInjection.md)
- [Azure credential configuration](https://github.com/Azure/azure-sdk-for-net/blob/Azure.Core_1.62.0/sdk/core/Azure.Core/src/Identity/ConfigurationExtensions.cs)

## Decisions remains an interim REST operation

OpenAI 2.14.0 has no typed Decisions client. The sample keeps its documented
`POST /openai/v1/decisions` JSON contract and `System.Text.Json` response checks.
Its named `HttpClient` comes from `IHttpClientFactory`; endpoint, timeout and
credentials come from configuration/DI. A TODO records the future switch to a
released typed client. It does not call a nonexistent SDK method.

```powershell
dotnet run decisions_example.cs -- --image ..\..\images\decisions-photo.png
dotnet run decisions_example.cs -- --image "https://raw.githubusercontent.com/scikit-image/scikit-image/v0.25.2/skimage/data/astronaut.png"
```

The optional `--image PATH_OR_HTTPS_URL` switches to visible damage, object
category and severity questions. Local PNG, JPEG, WebP and GIF files must be
readable, nonempty, and at most 32 MiB. A public HTTPS URL passes through unchanged,
without an app-side download. Validation precedes credential acquisition.

The Decisions endpoint must use HTTPS; loopback HTTP is permitted only with an
explicit API key for synthetic tests. The sample sends one uncompressed,
non-streaming request and prints named answers, all choice/score probabilities,
and usage. HTTP errors, refusals and malformed responses retain their explicit
handling; configuration/DI does not change the request contract.
