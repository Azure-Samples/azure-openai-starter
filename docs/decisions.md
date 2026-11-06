# Classify and score requests with the Azure OpenAI Decisions API

> **Audience:** This page is for coding agents and documentation authors, not for
> developers learning the starter. Developers should start with the
> [README](../README.md) and the [client guide](../CLIENT_README.md).

This article is a documentation-authoring source for the
[Azure OpenAI starter](../README.md). Its language tabs use Microsoft Learn
syntax and include the runnable sample files, so documentation and tested code
cannot drift independently. When publishing into another documentation repository,
copy the referenced sources or update the include paths to that repository's
sample location. GitHub displays the tab headings and source links rather than
the rendered Microsoft Learn tabs.

The Decisions API returns typed answers instead of generated prose. Every language
has two examples: a text example that routes a support ticket, and a multimodal
example that [asks about a photo](#evaluate-a-photo). The text example
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
- `AZURE_OPENAI_DEPLOYMENT` set to your Luna deployment name;
  the samples default to `gpt-6-luna`.
- Passwordless access with an identity assigned Cognitive Services User.
  Leave `AZURE_OPENAI_API_KEY` unset for this default. Python, .NET and Ruby use
  your `azd auth login` session; TypeScript, Go and Java use `DefaultAzureCredential`.
  Set `AZURE_TENANT_ID` to the tenant that owns the resource if your login spans
  several tenants; see the client guide. Setting `AZURE_OPENAI_API_KEY` explicitly
  selects the API-key fallback.
- The [runtime and dependencies for your language](../CLIENT_README.md).

SDK baselines checked **2026-10-23**:

| Language | OpenAI SDK | Decisions implementation |
|---|---|---|
| Python | 3.37.0 | Native SDK |
| JavaScript / TypeScript | 7.43.0 | Native SDK |
| Go | v3.86.0 | Native SDK |
| Java | 4.91.0 | Native SDK |
| Ruby | 0.111.0 | Native SDK |
| C# | OpenAI 2.15.0 (checked 2026-11-05) | Native SDK (experimental typed `DecisionsClient`) |

These are exact starter pins, not claims that earlier SDKs cannot run a basic
text example. The Learn minimums, Python 3.26.0 and JavaScript 7.30.0, cover basic
examples. The GA-type updates introduce source-level union/message changes.
The SDK base URL is `https://{resource}.openai.azure.com/openai/v1/`; the operation
is `/decisions`. The common [.env example](../.env.example) uses the resource root,
to which the programs append the v1 path.

Azure documentation currently describes up to **400 questions** and data URLs
or publicly accessible **HTTPS image URLs**. It excludes **East US 2** from the
Decisions rollout. These examples do not depend on JSON input, images in
question instructions, explicit caching controls, tool history or
GPT-Live. Those types being available in an OpenAI SDK is not certification of
the corresponding Azure service feature.

## Send a text decision request

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

# [C#](#tab/csharp)

From `src/dotnet`, run `dotnet run decisions_example.cs` with the .NET 10 SDK.
The [.NET configuration/DI guide](../src/dotnet/README.md) explains how to configure
the credential source, endpoint and timeout, while retaining the common starter
environment-variable setup.
The example uses the typed `DecisionsClient` and its strongly typed
`CreateDecisionAsync` method from OpenAI 2.15.0. That client is experimental in the
SDK, so the sample suppresses the `OPENAI001` and `SCME0002` diagnostics.

[!code-csharp[Decisions with the native .NET SDK](../src/dotnet/decisions_example.cs)]

---

## Interpret the results

The `answers` array follows the request's question order and echoes each
question's name. Predicates return `probability`; choice and score answers also
return their option/level probabilities and a `confidence` field. A refusal has
`type: "refusal"` and the question name.

The examples print named answers, per-option probabilities and full token usage.
Cached counts of zero are valid; no request depends on caching. Actual probabilities and
scores vary; example outputs are not assertions about model quality. Choose
application thresholds using labeled evaluation data and the costs of false
positives/negatives. A successful local contract test does not validate production
latency, quality, regional availability or billing.

Use a separate deployment name for Responses and Decisions. Do not send
Responses-only parameters such as `reasoning` or `max_output_tokens` to Decisions.

## Evaluate a photo

The multimodal example sends text and an image in one user message. The three
questions evaluate visible damage, classify the main object with an `other`
fallback, and score damage severity. Batch related questions into one request and
reuse the client for later batches instead of reconnecting per question.

# [Python](#tab/python)

From `src/python`, run `python decisions_multimodal_example.py`.

[!code-python[Decisions with an image using the native Python SDK](../src/python/decisions_multimodal_example.py)]

# [JavaScript / TypeScript](#tab/typescript)

From `src/typescript`, run `npm run decisions:multimodal`. To run JavaScript, compile with
`npm run build`, then run `node dist/decisions_multimodal_example.js`.

[!code-typescript[Decisions with an image using the native TypeScript SDK](../src/typescript/decisions_multimodal_example.ts)]

# [Go](#tab/go)

From `src/go/decisions_multimodal_example`, run `go run .`.

[!code-go[Decisions with an image using the native Go SDK](../src/go/decisions_multimodal_example/main.go)]

# [Java](#tab/java)

From `src/java`, run
`mvn compile exec:java -Dexec.mainClass=com.azure.openai.starter.DecisionsMultimodalExample`.

[!code-java[Decisions with an image using the native Java SDK](../src/java/src/main/java/com/azure/openai/starter/DecisionsMultimodalExample.java)]

# [Ruby](#tab/ruby)

From `src/ruby`, run `bundle install`, then
`bundle exec ruby decisions_multimodal_example.rb`.

[!code-ruby[Decisions with an image using the native Ruby SDK](../src/ruby/decisions_multimodal_example.rb)]

# [C#](#tab/csharp)

From `src/dotnet`, run `dotnet run decisions_multimodal_example.cs` with the .NET 10 SDK.
The image goes into a `DecisionsInputImageContentPart` beside the text part.

[!code-csharp[Decisions with an image using the native .NET SDK](../src/dotnet/decisions_multimodal_example.cs)]

---

With no argument, the example sends a public-domain NASA photo by HTTPS URL, which
Azure fetches. Pass your own public HTTPS image URL or the path to an image file
instead; a file is encoded as an inline base64 data URL.

The [client guide](../CLIENT_README.md#real-photo-scenarios) has the exact command
for each runtime. For example, from the repository root:

```bash
python src/python/decisions_multimodal_example.py
python src/python/decisions_multimodal_example.py images/decisions-photo.png
python src/python/decisions_multimodal_example.py https://example.com/your-photo.png
```

The included [real NASA photo](../images/decisions-photo.png) is a public-domain
transport fixture; [attribution](../images/decisions-photo.md) records the source.
It is not a damaged-product benchmark. Supported image formats are PNG, JPEG,
WebP and GIF; the service allows at most 128 images and 32 MB combined per request.
These programs send a single image.

Decisions returns one non-streaming response. The samples use uncompressed JSON,
not compressed request bodies. A non-success HTTP response stops an example with
the service's error message.
Use a fallback choice/probability threshold for ambiguous input rather than
trying to provoke a safety refusal.

## Check availability before provisioning

```bash
python scripts/check-model-support.py --region eastus --model gpt-6-luna --sku DataZoneStandard --format json
```

The script reads Azure's management-plane model catalog. Its output includes
versions and reported SKUs, a documented East US 2 rollout exclusion, and explicit
uncertainty for remaining feature, capacity and quota checks. It does not invoke
a model or enable a feature. Bicep defaults to East US and a DataZoneStandard
Luna deployment, with GlobalStandard configurable when appropriate. Its `location`
parameter allows only the regions that support both the default GPT-6.1 Sol
deployment and the Decisions API. Check the current region/model/SKU table and
quota; East US 2 is not a Decisions target.

## Live validation

With an existing Luna deployment configured in `AZURE_OPENAI_ENDPOINT` and
`AZURE_OPENAI_DEPLOYMENT`, set `AZURE_OPENAI_DECISIONS_LIVE_TESTS=1` and run
`python -m unittest discover -s tests -v`. The opt-in Decisions matrix removes
the API-key fallback and runs text, inline photo and hosted photo requests with
Entra authentication for every selected language. It incurs Azure usage charges.
Without a configured target, it is skipped explicitly; offline tests are not
live service-validation evidence. Advanced JSON/role/tool-history payloads are
left out until independently live-validated.

## References

- [Azure Decisions API documentation](https://learn.microsoft.com/azure/foundry/openai/how-to/decisions)
- [Azure model and region availability](https://learn.microsoft.com/azure/foundry/foundry-models/concepts/models-sold-directly-by-azure-region-availability)
- [OpenAI Decisions guide](https://developers.openai.com/api/docs/guides/decisions)
- [OpenAI SDKs](https://developers.openai.com/api/docs/libraries)
