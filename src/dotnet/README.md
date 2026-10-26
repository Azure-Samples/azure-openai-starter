# .NET OpenAI configuration and dependency injection

Requires the .NET 10 SDK. These are file-based applications: package directives
restore dependencies; no project file is required.

## Responses: use the OpenAI registration extension

Both Responses examples register the native OpenAI client directly:

```csharp
var builder = Host.CreateApplicationBuilder(args);
builder.AddAzureCredentialResolver();
builder.AddResponsesClient("Clients:Responses");
using var host = builder.Build();
var client = host.Services.GetRequiredService<ResponsesClient>();
```

`AddResponsesClient` binds `ResponsesClientSettings` from configuration and
registers the singleton. There is no `AddAzureClient` call, manual client-options
binding, credential factory, or automatic translation of `AZURE_OPENAI_*`
variables in the Responses samples.

The Azure credential resolver is **authentication only**. It enables configured
Entra credential sources; it does not create an Azure OpenAI wrapper client.
Both entry points register it because either can select Entra through configuration.
It is not used when `CredentialSource` is `ApiKeyCredential`; an API-key-only
application can omit that registration and its Azure authentication dependency.
No `Azure.AI.OpenAI` package or `AzureOpenAIClient` is used in this starter.

### Configure and run

From this directory, copy [appsettings.example.json](./appsettings.example.json)
to `appsettings.json`, replace the full v1 endpoints and Azure deployment names,
and run:

```powershell
dotnet run responses_example_entra.cs
dotnet run responses_example.cs
```

The configuration, not the filename, selects authentication. The example JSON
uses an existing `azd auth login` session. To configure without a JSON file:

```powershell
$env:Clients__Responses__Options__Endpoint = "https://YOUR-RESOURCE.openai.azure.com/openai/v1/"
$env:Clients__Responses__Model = "YOUR-SOL-DEPLOYMENT"
$env:Clients__Responses__Credential__CredentialSource = "AzureDeveloperCliCredential"
$env:Clients__Responses__Credential__Scope = "https://cognitiveservices.azure.com/.default"
# If your login spans tenants, set Clients__Responses__Credential__TenantId too.
dotnet run responses_example_entra.cs
```

For the explicit API-key alternative:

```powershell
$env:Clients__Responses__Credential__CredentialSource = "ApiKeyCredential"
$env:Clients__Responses__Credential__Key = $env:AZURE_OPENAI_API_KEY
dotnet run responses_example.cs
```

Use `AzureCliCredential`, `ManagedIdentityCredential`, or a configured
`ChainedTokenCredential` with `Sources` when appropriate. Pass credential options
such as `TenantId` and `ClientId` in the `Credential` section. These are standard
SDK configuration values, not sample-specific authentication switches.

| Setting | Purpose |
|---|---|
| `Clients:Responses:Options` | `ResponsesClientOptions`: full endpoint, network timeout, supported pipeline settings and organization/project IDs |
| `Clients:Responses:Credential` | Credential source, its options, and the Azure token scope |
| `Clients:Responses:Model` | Required Azure deployment name for GPT-6.1 Sol |
| `Clients:Responses:ReasoningEffort` | `medium` by default; also `low`, `high`, `xhigh`, `max` |
| `Clients:Responses:MaxOutputTokens` | `16384` by default; integer 16 through 128000 |

The Generic Host loads optional `appsettings.json`, environment variables and
command-line configuration. Standard double-underscore environment keys override
JSON. The required endpoint/model checks and request-parameter validation do not
bind or mutate client settings; the SDK extension handles that.

Keep real configuration and keys out of source control. The example configuration
is tracked; real `appsettings*.json` files are ignored.

## Decisions: interim REST

OpenAI 2.14.0 has no typed Decisions client. The Decisions example remains an
interim `HttpClient` REST call to `/openai/v1/decisions`, not an Azure OpenAI
wrapper. It uses DI for the named HTTP transport and configured Entra credentials.
A TODO records the future switch to a released typed OpenAI client.

The common starter environment variables remain supported by this REST example:

```powershell
$env:AZURE_OPENAI_ENDPOINT = "https://YOUR-RESOURCE.openai.azure.com/"
$env:AZURE_OPENAI_DEPLOYMENT = "YOUR-LUNA-DEPLOYMENT"
dotnet run decisions_example.cs
dotnet run decisions_example.cs -- --image ..\..\images\decisions-photo.png
```

Alternatively configure `Clients:Decisions` using the included JSON example or
`Clients__Decisions__...` environment keys. `Options:Endpoint` is the full v1 base
URL, `Model` is the Luna deployment name, and `Credential` selects authentication.
`Options:NetworkTimeout` configures the HTTP timeout.

The optional `--image PATH_OR_HTTPS_URL` accepts a real PNG, JPEG, WebP or GIF
photo of at most 32 MiB, encoded inline, or a publicly accessible HTTPS URL.
Validation precedes credentials; no client-side URL download occurs. The sample
batches three questions, prints named answers/probabilities/usage, and retains
explicit HTTP-error, refusal and malformed-response handling.

## Packages and validation

The samples use OpenAI **2.14.0** and Microsoft.Extensions Hosting/HTTP **10.0.10**.
Azure.Core **1.62.0** supplies the `Azure.Identity` credential resolver/types for
authentication; it is not the Azure OpenAI client library. The shipped
configuration APIs are experimental (`SCME0002`), explicitly suppressed here.
Native-AOT publishing is disabled for reflection-based configuration.

From the repository root, to test just .NET with local synthetic HTTP/CLI fixtures:

```powershell
$env:STARTER_TEST_LANGUAGES = ".NET"
python -m unittest discover -s tests -v
```

References:
- [OpenAI `AddResponsesClient`](https://github.com/openai/openai-dotnet/blob/OpenAI_2.14.0/OpenAI.Responses/src/Custom/OpenAIResponsesHostBuilderExtensions.cs)
- [System.ClientModel configuration/DI](https://github.com/Azure/azure-sdk-for-net/blob/System.ClientModel_1.15.0/sdk/core/System.ClientModel/src/docs/ConfigurationAndDependencyInjection.md)
- [Azure credential resolver](https://github.com/Azure/azure-sdk-for-net/blob/Azure.Core_1.62.0/sdk/core/Azure.Core/src/Identity/ConfigurationExtensions.cs)
