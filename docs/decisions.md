# Classify and score requests with the Azure OpenAI Decisions API

This article is a documentation-authoring source for the
[Azure OpenAI starter](../README.md). Its language tabs use Microsoft Learn
syntax and include the runnable sample files, so documentation and tested code
cannot drift independently. When publishing into another documentation repository,
copy the referenced sources or update the include paths to that repository's
sample location. GitHub displays the tab headings and source links rather than
the rendered Microsoft Learn tabs.

The Decisions API returns typed answers instead of generated prose. This example
evaluates a synthetic billing ticket with three independent questions:

| Question | Type | Result |
|---|---|---|
| Is a refund requested? | `predicate` | Probability that the condition is true |
| Which team should receive the ticket? | `choice` | One predefined option and its confidence |
| How severe is the issue? | `score` | A probability-weighted score and confidence |

Each question can instead return a refusal. Handle it explicitly, without
treating it as a negative predicate answer or as an HTTP transport failure.

## Prerequisites and scope

- An Azure OpenAI resource and a deployed **GPT-6 Luna** model in a supported
  region. The `model` parameter is your deployment name.
- `AZURE_OPENAI_ENDPOINT` set to the resource root, for example
  `https://YOUR-RESOURCE-NAME.openai.azure.com/`.
- `AZURE_OPENAI_DECISIONS_DEPLOYMENT_NAME` set to your Luna deployment name;
  the samples default to `gpt-6-luna`.
- Either an API key in `AZURE_OPENAI_API_KEY`, or passwordless access with an
  identity assigned Cognitive Services User. Ruby's passwordless sample uses
  your `az login` session; the other languages use Azure Identity.
- The [runtime and dependencies for your language](../CLIENT_README.md).

SDK baselines checked **2026-10-23**:

| Language | OpenAI SDK | Decisions implementation |
|---|---|---|
| Python | 3.37.0 or later within major version 3 | Native SDK |
| JavaScript / TypeScript | 7.43.0 or later within major version 7 | Native SDK |
| Go | v3.86.0 | Native SDK |
| Java | 4.91.0 | Native SDK |
| Ruby | 0.111.0 | Native SDK |
| C# | OpenAI 2.14.0 for Responses | REST using `HttpClient`; no typed Decisions client in this version |

These are starter baselines, not claims that earlier SDKs cannot run a basic
text example. The GA-type updates introduce source-level union/message changes.

Azure documentation currently describes up to **400 questions** and data URLs
or publicly accessible **HTTPS image URLs**. It excludes **East US 2** from the
Decisions rollout. This basic text sample does not depend on JSON input,
multimodal question instructions, explicit caching controls, tool history or
GPT-Live. Those types being available in an OpenAI SDK is not certification of
the corresponding Azure service feature.

## Send a decision request

# [Python](#tab/python)

From `src/python`, run `python decisions_example.py`.

[!code-python[Decisions with the native Python SDK](../src/python/decisions_example.py)]

# [JavaScript / TypeScript](#tab/typescript)

From `src/typescript`, run `npm run decisions`. To run JavaScript, compile with
`npm run build`, then run `node dist/decisions_example.js`.

[!code-typescript[Decisions with the native TypeScript SDK](../src/typescript/decisions_example.ts)]

# [Go](#tab/go)

From `src/go/decisions_example`, run `go run .`.

[!code-go[Decisions with the native Go SDK](../src/go/decisions_example/main.go)]

# [Java](#tab/java)

From `src/java`, run
`mvn compile exec:java -Dexec.mainClass=com.azure.openai.starter.DecisionsExample`.

[!code-java[Decisions with the native Java SDK](../src/java/src/main/java/com/azure/openai/starter/DecisionsExample.java)]

# [Ruby](#tab/ruby)

From `src/ruby`, run `bundle install`, then
`bundle exec ruby decisions_example.rb`.

[!code-ruby[Decisions with the native Ruby SDK](../src/ruby/decisions_example.rb)]

# [C# / REST](#tab/csharp)

From `src/dotnet`, run `dotnet run decisions_example.cs` with the .NET 10 SDK.
The HTTP call is intentional; do not replace it with an unreleased SDK class.

[!code-csharp[Decisions with HttpClient](../src/dotnet/decisions_example.cs)]

---

## Interpret the results

The `answers` array follows the request's question order and echoes each
question's name. Predicates return `probability`; choice and score answers also
return their option/level probabilities and a `confidence` field. A refusal has
`type: "refusal"` and the question name.

The examples print named answers and input-token usage. Actual probabilities and
scores vary; example outputs are not assertions about model quality. Choose
application thresholds using labeled evaluation data and the costs of false
positives/negatives. A successful local contract test does not validate production
latency, quality, regional availability or billing.

Use a separate deployment name for Responses and Decisions. Do not send
Responses-only parameters such as `reasoning` or `max_output_tokens` to Decisions.

## Check availability before provisioning

```bash
python scripts/check-model-support.py --region swedencentral --model gpt-6-luna --format json
```

The script reads Azure's management-plane model catalog. Its output includes
versions and reported SKUs, a documented East US 2 rollout exclusion, and explicit
uncertainty for remaining feature, capacity and quota checks. It does not invoke
a model or enable a feature.

## References

- [Azure Decisions API documentation](https://learn.microsoft.com/azure/foundry/openai/how-to/decisions)
- [Azure model and region availability](https://learn.microsoft.com/azure/foundry/foundry-models/concepts/models-sold-directly-by-azure-region-availability)
- [OpenAI Decisions guide](https://developers.openai.com/api/docs/guides/decisions)
- [OpenAI SDKs](https://developers.openai.com/api/docs/libraries)
