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

### Decisions uses interim REST

OpenAI .NET 2.14.0 does **not** expose a typed Decisions client.
`decisions_example.cs` therefore uses `HttpClient` to post the documented JSON
contract to `/openai/v1/decisions` and validates the response with `JsonDocument`.
It does not depend on an unreleased SDK class.
The sample includes a TODO to switch to a typed client when one is released.
The file disables the optional native-AOT publish default so the anonymous
request object can use reflection-based JSON serialization.

Set `AZURE_OPENAI_DEPLOYMENT` to the **Azure deployment name** pointing to
GPT-6 Luna. It defaults to `gpt-6-luna` only when unset; an explicitly blank
value is rejected. This is independent of the Sol Responses deployment.
The endpoint must be the **resource root**, without `/openai/v1/`.
The Decisions sample uses `AZURE_OPENAI_API_KEY` when nonempty, otherwise
`DefaultAzureCredential` with the Azure OpenAI scope. For local development,
run `az login` and ensure your identity has Azure OpenAI data-plane access.

```powershell
$env:AZURE_OPENAI_DEPLOYMENT = "gpt-6-luna"
dotnet run decisions_example.cs
dotnet run decisions_example.cs -- --image ..\..\images\decisions-photo.png
dotnet run decisions_example.cs -- --image "https://raw.githubusercontent.com/scikit-image/scikit-image/v0.25.2/skimage/data/astronaut.png"
```

No arguments preserves the duplicate-charge ticket and its three questions.
The only optional arguments are `--image PATH_OR_HTTPS_URL`; they switch to
visible-damage, object-category, and severity questions. Use the bundled NASA
public-domain photo above or your own
readable, nonempty `.png`, `.jpg`, `.jpeg`, `.webp`, or `.gif` photo, at most
**32 MiB (33,554,432 bytes)**. Local bytes are encoded as an inline base64 data
URL with the matching MIME type. Validation runs before authentication or
client creation.

Public HTTPS image URLs pass through unchanged, without an app-side download.
Signed query strings are allowed, but a host is required and credentials,
fragments, and HTTP image URLs (even loopback) are rejected. Only one image is
sent, below the API's 128-image limit. The Azure endpoint requires HTTPS;
HTTP loopback is allowed only with an explicit API key for synthetic tests.
One reusable `HttpClient` sends all three questions in one buffered JSON request.

The example prints each named predicate, choice, score, or refusal, all
choice/score option probabilities, and input/output/total usage. Cached,
cache-write, and reasoning tokens are printed when reported. HTTP errors
include the response body; unknown, duplicate, missing, or malformed answers
and missing usage fail instead of being reported as successful decisions.
