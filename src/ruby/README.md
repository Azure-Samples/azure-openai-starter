# Ruby Decisions example

Requires Ruby **3.3 or later** and Bundler. The official `openai` gem is pinned
to `0.111.0`.

From this directory:

```powershell
bundle install
$env:AZURE_OPENAI_ENDPOINT = "https://YOUR-RESOURCE.openai.azure.com"
$env:AZURE_OPENAI_DEPLOYMENT = "gpt-6-luna"
bundle exec ruby decisions_example.rb
bundle exec ruby decisions_example.rb --image ..\..\images\decisions-photo.png
bundle exec ruby decisions_example.rb --image "https://raw.githubusercontent.com/scikit-image/scikit-image/v0.25.2/skimage/data/astronaut.png"
```

Set `AZURE_OPENAI_API_KEY` for API-key authentication. Otherwise install the
Azure CLI and run `az login`; the example obtains an Azure OpenAI access token
with `az account get-access-token` without printing it. The signed-in identity
needs Azure OpenAI data-plane access. There is no official Ruby Azure Identity
credential class; the sample deliberately uses the Azure CLI instead.
The endpoint is the **resource root**, not an `/openai/v1/` URL.
`AZURE_OPENAI_DEPLOYMENT` is the **Azure deployment name**, which must point to
GPT-6 Luna. It defaults to `gpt-6-luna` only when unset; an explicitly blank value
is rejected. This example does not use `AZURE_OPENAI_GPT_DEPLOYMENT_NAME` or the
Sol Responses settings.

With no arguments, the sample classifies the original duplicate-charge ticket.
The only optional arguments are `--image PATH_OR_HTTPS_URL`, which instead ask
about visible damage, object category, and severity. Use the bundled NASA
public-domain photo above or your own readable,
nonempty `.png`, `.jpg`, `.jpeg`, `.webp`, or `.gif` photo of at most
**32 MiB (33,554,432 bytes)**. Local bytes are encoded inline as a base64 data
URL with the matching MIME type. Validation happens before token acquisition
or client creation.

A public HTTPS image URL is passed unchanged to the service; the sample never
downloads it. Signed query strings are allowed; a host is required and user
info, fragments, and HTTP image URLs (including loopback) are rejected. One
image is sent, below the API's 128-image limit. The Azure endpoint also requires
HTTPS; HTTP loopback is allowed only with an explicit API key for synthetic
contract tests. One client reuses its connections and batches all three
questions in one call.

Output includes every named predicate, choice, score, or refusal, all
choice/score option probabilities, and input/output/total usage. Cached,
cache-write, and reasoning token counts are printed when reported. HTTP errors
and unknown, duplicate, missing, or malformed answers and missing usage fail
explicitly.
