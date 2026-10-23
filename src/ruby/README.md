# Ruby Decisions example

Requires Ruby **3.3 or later** and Bundler. The official `openai` gem is pinned
to `0.111.0`.

From this directory:

```powershell
bundle install
$env:AZURE_OPENAI_ENDPOINT = "https://YOUR-RESOURCE.openai.azure.com"
$env:AZURE_OPENAI_DECISIONS_DEPLOYMENT_NAME = "gpt-6-luna"
bundle exec ruby decisions_example.rb
```

Set `AZURE_OPENAI_API_KEY` for API-key authentication. Otherwise install the
Azure CLI and run `az login`; the example obtains an Azure OpenAI access token
with `az account get-access-token` without printing it. The signed-in identity
needs Azure OpenAI data-plane access. The endpoint is the **resource root**,
not an `/openai/v1/` URL. A separate Luna deployment is required; this example
does not use `AZURE_OPENAI_GPT_DEPLOYMENT_NAME` or the Sol Responses settings.

The example prints one line per predicate, choice, score, or refusal and fails
on HTTP errors, empty answers, missing usage, and malformed answers.
