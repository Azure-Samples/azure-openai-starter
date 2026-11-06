# Ruby Decisions examples

Requires Ruby **3.3 or later** and Bundler. The official `openai` gem is pinned
to `0.111.0`.

From this directory:

```powershell
bundle install
$env:AZURE_OPENAI_ENDPOINT = "https://YOUR-RESOURCE.openai.azure.com"
$env:AZURE_OPENAI_DEPLOYMENT = "gpt-6-luna"
bundle exec ruby decisions_example.rb
bundle exec ruby decisions_multimodal_example.rb
bundle exec ruby decisions_multimodal_example.rb ..\..\images\decisions-photo.png
bundle exec ruby decisions_multimodal_example.rb "https://example.com/your-photo.png"
```

Set `AZURE_OPENAI_API_KEY` for API-key authentication. Otherwise install the
Azure Developer CLI and run `azd auth login`; the examples obtain an Azure OpenAI
access token with `azd auth token` without printing it. The signed-in identity
needs Azure OpenAI data-plane access. There is no official Ruby Azure Identity
credential class; the examples deliberately use the Azure Developer CLI instead.
Set `AZURE_TENANT_ID` to the resource's tenant when your login spans tenants; the
examples pass it to `azd auth token` without changing your saved CLI context.
The endpoint is the **resource root**, not an `/openai/v1/` URL.
`AZURE_OPENAI_DEPLOYMENT` is the **Azure deployment name**, which must point to
GPT-6 Luna. It defaults to `gpt-6-luna` when unset. These examples do not use
`AZURE_OPENAI_GPT_DEPLOYMENT_NAME` or the Sol Responses settings.

`decisions_example.rb` is the text example: it classifies a duplicate-charge
support ticket. `decisions_multimodal_example.rb` asks about a photo (visible
damage, object category and severity). With no argument it sends a public-domain
NASA photo by HTTPS URL, which Azure fetches. Pass your own public HTTPS image URL or
the path to a PNG, JPEG, WebP or GIF file instead; a local file is encoded inline as a
base64 data URL. One image is sent, below the API's 128-image limit, and the example
never downloads it. One client batches all three questions in one call.

Output includes every named predicate, choice, score, or refusal, all
choice/score option probabilities, and the usage the service reports. The gem's error
message for a failed request leaves out the service's message, so the examples
print the response body.

On Windows, the first invocation can take longer while Ruby loads the SDK.
Do not interpret process startup time as the latency of the Decisions request.
