# Go Decisions example

Requires Go **1.26 or later**, the minimum required by OpenAI Go `v3.86.0`.
From this directory:

```powershell
$env:AZURE_OPENAI_ENDPOINT = "https://YOUR-RESOURCE.openai.azure.com"
$env:AZURE_OPENAI_DEPLOYMENT = "gpt-6-luna"
go run .
```

This is the text example: it classifies a duplicate-charge support ticket. The
[multimodal example](../decisions_multimodal_example/README.md) asks about a photo.

Set `AZURE_OPENAI_API_KEY` for API-key authentication. Otherwise the sample
uses `DefaultAzureCredential`, including an existing `az login` or `azd auth login`
session or a managed identity with Azure OpenAI data-plane access. Set
`AZURE_TENANT_ID` to the tenant that owns the resource if your login spans several
tenants. Supply the resource-root endpoint, not an `/openai/v1/` URL. The native
OpenAI Go `Decisions` client uses `AZURE_OPENAI_DEPLOYMENT` as the **Azure
deployment name**, which must point to GPT-6 Luna. It defaults to `gpt-6-luna`
when unset. It does not use the Sol Responses deployment or reasoning settings.
All three questions (a predicate, a choice and a score) are batched in one call.

Output includes each named answer's probability or value and confidence, every
choice/score option probability, and the token usage the service reports. A refusal
is printed instead of an answer. The SDK's error string for a failed request leaves
out the service's message, so the sample adds it.
