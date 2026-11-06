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
var responsesClient = host.Services.GetRequiredService<ResponsesClient>();
```

`AddResponsesClient` binds `ResponsesClientSettings` from configuration and
registers the singleton. There is no `AddAzureClient` call, manual client-options
binding, credential factory, or automatic translation of `AZURE_OPENAI_*`
variables in the Responses samples.

The examples also require `Options:Endpoint` to be an absolute HTTPS URL (HTTP is
accepted only for a loopback test server). A mistyped `http://` URL then cannot send
an API key in clear text, and a value that is not an absolute URL is rejected instead
of being left for the SDK to ignore.

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

## Decisions: use the typed `DecisionsClient`

OpenAI 2.15.0 adds an experimental typed `DecisionsClient`. The two Decisions examples
(a text example and a multimodal example) use its strongly typed
`CreateDecisionAsync(DecisionCreationOptions)` method; they do not call the raw
`BinaryContent` protocol method or build JSON by hand. The client is registered the
same way as the Responses client:

```csharp
var builder = Host.CreateApplicationBuilder();
builder.AddAzureCredentialResolver();
builder.AddDecisionsClient("Clients:Decisions");
using var host = builder.Build();
var decisionsClient = host.Services.GetRequiredService<DecisionsClient>();
```

The request is built from typed models: a `DecisionsUserMessageItem` holds the
input (a `DecisionsInputTextContentPart`, plus a `DecisionsInputImageContentPart` in
the multimodal example), and a `DecisionsPredicateQuestion`, `DecisionsChoiceQuestion`
and `DecisionsScoreQuestion` hold the three batched questions. The response is a
`DecisionResource`; pattern-match each answer as a `DecisionsPredicateAnswer`,
`DecisionsChoiceAnswer`, `DecisionsScoreAnswer` or `DecisionsRefusalAnswer` so a
refusal is handled explicitly instead of cast away.

A choice is a string or a boolean. `DecisionsChoiceValue` has no `ToString()` or
equality, so read its `StringValue` or `BooleanValue` instead of comparing or
printing the wrapper.

The common starter environment variables remain supported by the Decisions examples
and are translated into the `Clients:Decisions` configuration before the client is
registered. Without an API key they use the Azure Developer CLI credential
(`azd auth login`), for the tenant in `AZURE_TENANT_ID` when it is set:

```powershell
$env:AZURE_OPENAI_ENDPOINT = "https://YOUR-RESOURCE.openai.azure.com/"
$env:AZURE_OPENAI_DEPLOYMENT = "YOUR-LUNA-DEPLOYMENT"
dotnet run decisions_example.cs
dotnet run decisions_multimodal_example.cs
dotnet run decisions_multimodal_example.cs -- ..\..\images\decisions-photo.png
```

Alternatively configure `Clients:Decisions` using the included JSON example or
`Clients__Decisions__...` environment keys. `Options:Endpoint` is the full v1 base
URL, `Model` is the Luna deployment name, and `Credential` selects authentication,
for example `AzureCliCredential` or `ManagedIdentityCredential`.
`Options:NetworkTimeout` configures the SDK pipeline's network timeout. An explicit
`Clients:Decisions` setting always wins over the starter variables.

The multimodal example takes an optional image after `--`: the path to a PNG, JPEG,
WebP or GIF file, encoded inline, or a publicly accessible HTTPS URL. With no
argument it sends a public-domain NASA photo by HTTPS URL. No client-side URL download
occurs. Both examples batch three questions and print named answers, probabilities
and usage. An HTTP error stops the example with the service's error message.
Empty answers, missing usage, unknown answer types and choices without a value
also fail explicitly. The endpoint must be an absolute URL so invalid configuration
cannot silently redirect the SDK to its default OpenAI endpoint.

## Packages and validation

The samples use OpenAI **2.15.0** and Microsoft.Extensions Hosting **10.0.10**.
Azure.Core **1.62.0** supplies the `Azure.Identity` credential resolver/types for
authentication; it is not the Azure OpenAI client library. The shipped
configuration APIs and the Decisions client are experimental (`SCME0002` and
`OPENAI001`), explicitly suppressed here.
Native-AOT publishing is disabled for reflection-based configuration.

From the repository root, to test just .NET with local synthetic HTTP/CLI fixtures:

```powershell
$env:STARTER_TEST_LANGUAGES = ".NET"
python -m unittest discover -s tests -v
```

References:
- [OpenAI `AddResponsesClient`](https://github.com/openai/openai-dotnet/blob/OpenAI_2.15.0/OpenAI.Responses/src/Custom/OpenAIResponsesHostBuilderExtensions.cs)
- [OpenAI `AddDecisionsClient`](https://github.com/openai/openai-dotnet/blob/OpenAI_2.15.0/OpenAI/src/Custom/OpenAIHostBuilderExtensions.cs)
- [OpenAI .NET Decisions usage](https://github.com/openai/openai-dotnet/blob/OpenAI_2.15.0/README.md#how-to-create-decisions)
- [System.ClientModel configuration/DI](https://github.com/Azure/azure-sdk-for-net/blob/System.ClientModel_1.16.0/sdk/core/System.ClientModel/src/docs/ConfigurationAndDependencyInjection.md)
- [Azure credential resolver](https://github.com/Azure/azure-sdk-for-net/blob/Azure.Core_1.62.0/sdk/core/Azure.Core/src/Identity/ConfigurationExtensions.cs)
