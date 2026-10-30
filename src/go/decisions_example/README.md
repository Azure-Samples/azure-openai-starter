# Go Decisions example

Requires Go **1.26 or later**, the minimum required by OpenAI Go `v3.86.0`.
From this directory:

```powershell
$env:AZURE_OPENAI_ENDPOINT = "https://YOUR-RESOURCE.openai.azure.com"
$env:AZURE_OPENAI_DEPLOYMENT = "gpt-6-luna"
go run .
go run . --image ..\..\..\images\decisions-photo.png
go run . --image "https://raw.githubusercontent.com/scikit-image/scikit-image/v0.25.2/skimage/data/astronaut.png"
```

Set `AZURE_OPENAI_API_KEY` for API-key authentication. Otherwise the sample
uses `DefaultAzureCredential`, including an existing `az login` session or a
managed identity with Azure OpenAI data-plane access. Supply the resource-root
endpoint, not an `/openai/v1/` URL. The native OpenAI Go `Decisions` client uses
`AZURE_OPENAI_DEPLOYMENT` as the **Azure deployment name**, which must point to
GPT-6 Luna. It defaults to `gpt-6-luna` only when unset; an explicitly blank value
is rejected. It does not use the Sol Responses deployment or reasoning settings.
The client is created once so its connections can be reused, and all three
questions are batched in one call.

With no arguments, the sample classifies the existing duplicate-charge ticket.
The only optional arguments are `--image PATH_OR_HTTPS_URL`, which instead ask
about visible damage, object category, and severity. Use the bundled NASA
public-domain photo above or your own photo: a
readable, nonempty `.png`, `.jpg`, `.jpeg`, `.webp`, or `.gif` file of at most
**32 MiB (33,554,432 bytes)**. Local bytes are base64-encoded inline with the
matching MIME type. File and argument validation happens before credentials
or a client are created.

A public HTTPS image URL is sent unchanged to the service, never downloaded
by the app. Signed query strings are allowed; a host is required and user info,
fragments, and HTTP image URLs (including loopback) are rejected. The sample
sends one image, below the API's 128-image limit. The Azure endpoint also
requires HTTPS; HTTP loopback is allowed only with an explicit API key for
synthetic contract tests.

Output includes each named answer's probability or value and confidence, every
choice/score option probability, and input/output/total token usage. Cached,
cache-write, and reasoning token counts are printed when reported. Unknown,
duplicate, missing, or malformed answers and missing usage fail explicitly.
