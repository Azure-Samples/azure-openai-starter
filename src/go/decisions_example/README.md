# Go Decisions example

Requires Go **1.26 or later**, the minimum required by OpenAI Go `v3.86.0`.
From this directory:

```powershell
$env:AZURE_OPENAI_ENDPOINT = "https://YOUR-RESOURCE.openai.azure.com"
$env:AZURE_OPENAI_DECISIONS_DEPLOYMENT_NAME = "gpt-6-luna"
go run .
```

Set `AZURE_OPENAI_API_KEY` for API-key authentication. Otherwise the sample
uses `DefaultAzureCredential`, including an existing `az login` session or a
managed identity with Azure OpenAI data-plane access. Supply the resource-root
endpoint, not an `/openai/v1/` URL. The native OpenAI Go `Decisions` client uses
the separate Luna deployment, not the Sol Responses deployment or its
reasoning settings.
