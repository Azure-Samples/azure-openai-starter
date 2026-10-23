# .NET Code Prerequisites

This sample code requires .NET 10 or later.

1. Check whether you've installed .NET 10 or not.

    ```bash
    dotnet --list-sdks
    ```

1. If you don't see 10.0.100 or higher, install [.NET 10 SDK](https://dotnet.microsoft.com/download/dotnet/10.0).

## Run the examples

These are .NET 10 file-based applications; no project file is required.

```powershell
$env:AZURE_OPENAI_ENDPOINT = "https://YOUR-RESOURCE.openai.azure.com"
dotnet run responses_example.cs
dotnet run responses_example_entra.cs
dotnet run decisions_example.cs
```

The Responses samples use OpenAI .NET **2.14.0**, the Sol deployment configured
by `AZURE_OPENAI_GPT_DEPLOYMENT_NAME`, and the existing reasoning settings.
The API-key Responses sample requires `AZURE_OPENAI_API_KEY`; the Entra sample
uses `DefaultAzureCredential`.

### Decisions uses REST

OpenAI .NET 2.14.0 does **not** expose a typed Decisions client.
`decisions_example.cs` therefore uses `HttpClient` to post the documented JSON
contract to `/openai/v1/decisions` and validates the response with `JsonDocument`.
It does not depend on an unreleased SDK class.
The file disables the optional native-AOT publish default so the anonymous
request object can use reflection-based JSON serialization.

Set `AZURE_OPENAI_DECISIONS_DEPLOYMENT_NAME` to your separate Luna deployment;
the default is `gpt-6-luna`. This is independent of the Sol Responses deployment.
The endpoint must be the **resource root**, without `/openai/v1/`.
The Decisions sample uses `AZURE_OPENAI_API_KEY` when nonempty, otherwise
`DefaultAzureCredential` with the Azure OpenAI scope. For local development,
run `az login` and ensure your identity has Azure OpenAI data-plane access.

The example prints one line per predicate, choice, score, or refusal. HTTP errors
include the response body, and malformed responses, empty answers, or missing
usage fail instead of being reported as successful decisions.
